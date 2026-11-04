"""Population-level rate monitoring. Descriptive signals, never causal conclusions."""
from __future__ import annotations

import hashlib
import json
import re
from fractions import Fraction
from datetime import datetime, timedelta, timezone
from typing import Literal
from pydantic import Field, StrictBool, StrictInt, model_validator
from .core import Strict, TOKEN, instant

COLUMNS = ('id', 'metric_id', 'cohort_id', 'bucket_start', 'bucket_end', 'numerator',
           'denominator', 'missing', 'definition_version', 'population_complete', 'finalized')


class Window(Strict):
    start: datetime
    end: datetime

    @model_validator(mode='after')
    def check(self):
        self.start, self.end = instant(self.start), instant(self.end)
        if any(d.time().isoformat() != '00:00:00' for d in (self.start, self.end)):
            raise ValueError('aggregate windows require UTC midnight boundaries')
        if not 1 <= (self.end - self.start).days <= 90:
            raise ValueError('window length must be 1 to 90 days')
        return self


class Windows(Strict):
    baseline: Window
    current: Window

    @model_validator(mode='after')
    def check(self):
        if self.baseline.end > self.current.start:
            raise ValueError('baseline must end before or at current start')
        return self


class Rolling(Strict):
    current_days: int = Field(default=7, ge=1, le=90)
    baseline_days: int = Field(default=28, ge=1, le=90)
    lag_days: int = Field(default=1, ge=0, le=30)


class Metric(Strict):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    definition_version: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    role: Literal['outcome', 'guardrail']
    worse: Literal['higher', 'lower'] = 'higher'
    threshold: float = Field(ge=0, le=1)
    min_change: float = Field(default=0.05, gt=0, le=1)
    min_denominator: int = Field(default=30, ge=1, le=1000000000)
    min_coverage: float = Field(default=0.95, gt=0, le=1)
    consecutive_days: int = Field(default=3, ge=2, le=30)


class AggregateSource(Strict):
    name: str = Field(default='workflow_metrics', pattern=r'^[a-z][a-z0-9_-]{0,39}$')
    kind: Literal['postgres_aggregate'] = 'postgres_aggregate'
    schema_name: str = 'reporting'
    view: str = 'daily_operation_metrics'
    dsn_env: str = 'OPS_DATABASE_DSN'
    fields: dict[str, str] = Field(default_factory=lambda: {c: c for c in COLUMNS})

    @model_validator(mode='after')
    def check(self):
        if set(self.fields) != set(COLUMNS) or len(set(self.fields.values())) != len(COLUMNS):
            raise ValueError('all aggregate columns require distinct mappings')
        for value in [self.schema_name, self.view, self.dsn_env, *self.fields.values()]:
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
                raise ValueError('invalid aggregate identifier')
        return self


class MonitorConfig(Strict):
    source: AggregateSource = Field(default_factory=AggregateSource)
    metrics: list[Metric] = Field(min_length=1, max_length=20)
    cohorts: list[str] = Field(min_length=1, max_length=20)
    windows: Windows | None = None
    rolling: Rolling | None = None
    max_rows: int = Field(default=5000, ge=1, le=10000)
    timeout_seconds: int = Field(default=15, ge=1, le=60)
    max_output_bytes: int = Field(default=1000000, ge=2000, le=5000000)

    @model_validator(mode='after')
    def check(self):
        if (self.windows is None) == (self.rolling is None):
            raise ValueError('select explicit windows or rolling windows, not both')
        if len({m.id for m in self.metrics}) != len(self.metrics):
            raise ValueError('duplicate metrics')
        if len(set(self.cohorts)) != len(self.cohorts) or any(not re.fullmatch(TOKEN, c) for c in self.cohorts):
            raise ValueError('cohorts must be unique opaque identifiers')
        days = ((self.windows.baseline.end - self.windows.baseline.start).days +
                (self.windows.current.end - self.windows.current.start).days) if self.windows else self.rolling.baseline_days + self.rolling.current_days
        if days * len(self.metrics) * len(self.cohorts) > self.max_rows:
            raise ValueError('expected daily cells exceed retrieval budget; narrow configured cohorts or windows')
        return self

    def resolve(self, as_of=None):
        if self.windows:
            if as_of is not None:
                raise ValueError('as-of is only valid for rolling configuration')
            if self.windows.current.end > datetime.now(timezone.utc):
                raise ValueError('monitor windows must be closed, not future-dated')
            return self.windows
        anchor = instant(as_of) if as_of is not None else datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if anchor.time().isoformat() != '00:00:00':
            raise ValueError('as-of must be UTC midnight')
        end = anchor - timedelta(days=self.rolling.lag_days)
        if end > datetime.now(timezone.utc):
            raise ValueError('monitor windows must be closed, not future-dated')
        start = end - timedelta(days=self.rolling.current_days)
        return Windows(baseline=Window(start=start - timedelta(days=self.rolling.baseline_days), end=start), current=Window(start=start, end=end))


class AggregateRow(Strict):
    id: str = Field(pattern=r'^[A-Za-z0-9_.:/+=-]{1,512}$')
    metric_id: str
    cohort_id: str
    bucket_start: datetime
    bucket_end: datetime
    numerator: StrictInt = Field(ge=0, le=1000000000000)
    denominator: StrictInt = Field(ge=0, le=1000000000000)
    missing: StrictInt = Field(ge=0, le=1000000000000)
    definition_version: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    population_complete: StrictBool
    finalized: StrictBool

    @model_validator(mode='after')
    def check(self):
        self.bucket_start, self.bucket_end = instant(self.bucket_start), instant(self.bucket_end)
        if self.bucket_start.time().isoformat() != '00:00:00' or self.bucket_end - self.bucket_start != timedelta(days=1):
            raise ValueError('rows must cover one UTC day')
        if self.numerator > self.denominator:
            raise ValueError('numerator exceeds observed denominator')
        return self


def days(window):
    return [window.start + timedelta(days=i) for i in range((window.end - window.start).days)]


def monitor(config, fetch, as_of=None):
    windows = config.resolve(as_of)
    limitations, accepted, source_ok = [], [], True
    expected = {(m.id, c, d) for m in config.metrics for c in config.cohorts for w in (windows.baseline, windows.current) for d in days(w)}
    try:
        rows, truncated = fetch(config, windows)
        if not isinstance(rows, list) or not isinstance(truncated, bool):
            raise ValueError('invalid aggregate response')
        if truncated or len(rows) > config.max_rows:
            source_ok = False
            limitations.append('Source retrieval truncated; comparisons withheld.')
        seen_ids, seen_cells = set(), set()
        for index, raw in enumerate(rows[:config.max_rows]):
            try:
                value = {key: raw[column] for key, column in config.source.fields.items()}
                if isinstance(value['id'], int) and not isinstance(value['id'], bool):
                    value['id'] = str(value['id'])
                row = AggregateRow.model_validate(value)
                cell = (row.metric_id, row.cohort_id, row.bucket_start)
                if cell not in expected or cell in seen_cells or row.id in seen_ids:
                    raise ValueError('unexpected or duplicated cell/ID')
                seen_cells.add(cell)
                seen_ids.add(row.id)
                accepted.append(row)
            except (ValueError, KeyError, TypeError):
                source_ok = False
                limitations.append(f'Row {index} invalid, duplicated or outside configured scope; comparisons withheld.')
    except Exception as exc:
        source_ok = False
        limitations.append(f'Aggregate source unavailable ({type(exc).__name__}); no source error payload retained.')
    cells = {(r.metric_id, r.cohort_id, r.bucket_start): r for r in accepted}
    results = []
    for metric in config.metrics:
        for cohort in config.cohorts:
            totals = {}
            issues = [] if source_ok else ['source_unreliable']
            for label, window in [('baseline', windows.baseline), ('current', windows.current)]:
                selected = [cells[(metric.id, cohort, d)] for d in days(window) if (metric.id, cohort, d) in cells]
                n, denominator, missing = (sum(getattr(r, key) for r in selected) for key in ('numerator', 'denominator', 'missing'))
                eligible = denominator + missing
                coverage = denominator / eligible if eligible else None
                expected_days = len(days(window))
                if len(selected) != expected_days:
                    issues.append(f'{label}_missing_daily_buckets')
                if any(not r.population_complete or not r.finalized or r.definition_version != metric.definition_version for r in selected):
                    issues.append(f'{label}_incomplete_unfinalized_or_definition_mismatch')
                if denominator < metric.min_denominator:
                    issues.append(f'{label}_small_denominator')
                if coverage is None or coverage < metric.min_coverage:
                    issues.append(f'{label}_low_coverage')
                totals[label] = {'numerator': n, 'denominator': denominator, 'missing': missing,
                    'eligible': eligible, 'coverage': coverage, 'rate': n / denominator if denominator else None,
                    'expected_buckets': expected_days, 'received_buckets': len(selected),
                    'refs': [f'{config.source.name}:{r.id}' for r in selected]}
            result = {'metric_id': metric.id, 'cohort_id': cohort, 'role': metric.role, 'definition_version': metric.definition_version,
                      'windows': totals, 'status': 'insufficient_evidence' if issues else 'no_signal',
                      'priority': 'review_data' if issues else 'none', 'reasons': issues,
                      'change_percentage_points': None, 'threshold_breach': None, 'consecutive_breach_days': None,
                      'rca_handoff': None}
            if not issues:
                current = Fraction(totals['current']['numerator'], totals['current']['denominator'])
                baseline = Fraction(totals['baseline']['numerator'], totals['baseline']['denominator'])
                change = current - baseline
                sign = 1 if metric.worse == 'higher' else -1
                breach = sign * (current - Fraction(str(metric.threshold))) > 0
                deteriorated = sign * change >= Fraction(str(metric.min_change))
                consecutive = longest = 0
                for d in days(windows.current):
                    r = cells[(metric.id, cohort, d)]
                    eligible = r.denominator + r.missing
                    daily_ok = r.denominator >= metric.min_denominator and eligible and r.denominator / eligible >= metric.min_coverage
                    hit = daily_ok and sign * (Fraction(r.numerator, r.denominator) - Fraction(str(metric.threshold))) > 0
                    consecutive = consecutive + 1 if hit else 0
                    longest = max(longest, consecutive)
                persistent = longest >= metric.consecutive_days
                reasons = [name for name, flag in [('threshold_breach', breach), ('window_deterioration', deteriorated), ('consecutive_daily_breaches', persistent)] if flag]
                result.update(status='attention' if reasons else 'no_signal', priority='high' if breach and deteriorated else 'medium' if reasons else 'none',
                              reasons=reasons, change_percentage_points=float(100 * change), threshold_breach=breach, consecutive_breach_days=longest)
                if reasons:
                    result['rca_handoff'] = {'skill': 'operations-root-cause', 'action': 'Human review first; resolve affected case IDs from the approved workflow source, then invoke RCA with an authorized bounded window.',
                                            'question': f'Investigate {metric.id} for cohort {cohort}; distinguish routing, capacity, policy and data-quality explanations.',
                                            'case_ids': [], 'automatic_invocation': False}
            results.append(result)
    order = {'high': 0, 'medium': 1, 'review_data': 2, 'none': 3}
    results.sort(key=lambda r: (order[r['priority']], r['metric_id'], r['cohort_id']))
    report = {'schema_version': 1, 'review_status': 'HUMAN_REVIEW_REQUIRED', 'source': config.source.name,
              'comparison_windows': windows.model_dump(mode='json'), 'metric_contracts': [m.model_dump() for m in config.metrics],
              'coverage': {'accepted_rows': len(accepted), 'expected_rows': len(expected), 'source_reliable': source_ok},
              'results': results, 'evidence': [{'ref': f'{config.source.name}:{r.id}', **r.model_dump(mode='json')} for r in accepted],
              'limitations': limitations + ['Counts and completeness flags are source assertions; census correctness is not independently verified.',
                'Rates use summed numerators / summed observed denominators, not averages of daily percentages.',
                'Window differences and consecutive breaches are descriptive signals, not statistical trends, significance tests or causes.',
                'Cohorts may overlap; do not sum cohort counts. Seasonality and case-mix differences need human review.'],
              'notifications_sent': False, 'schedules_created': False}
    encoded = json.dumps(report, sort_keys=True).encode()
    report['sha256'] = hashlib.sha256(encoded).hexdigest()
    if len((json.dumps(report, indent=2) + '\n').encode()) > config.max_output_bytes:
        raise ValueError('monitor output budget exceeded; narrow configuration')
    return report

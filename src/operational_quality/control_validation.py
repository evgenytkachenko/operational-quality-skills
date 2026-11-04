"""Human-reviewed evaluation of an approved preventive-control pilot. No actions."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from fractions import Fraction
from typing import Literal
from pydantic import Field, model_validator
from .core import Strict, instant, redact
from .inquiry import Assessment
from .monitor import MonitorConfig, Window, monitor
from .provenance import EvidenceLink, bind_claims, required_link_failures

DOMAINS = {'case_mix', 'seasonality', 'concurrent_changes', 'measurement', 'spillover'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class Link(Strict):
    source_id: str = Field(pattern=r'^[A-Za-z0-9_.:/+=-]{1,512}$')
    part: Literal['text'] = 'text'
    quote: str = Field(min_length=1, max_length=4000)


class Artifact(Strict):
    ref: str = Field(pattern=r'^[A-Za-z0-9_.:/+=-]{1,512}$')
    kind: Literal['approval', 'implementation', 'context']
    text: str = Field(min_length=1, max_length=8000)


class Evidence(Strict):
    artifacts: list[Artifact] = Field(max_length=30)

    @model_validator(mode='after')
    def check(self):
        if len({a.ref for a in self.artifacts}) != len(self.artifacts):
            raise ValueError('duplicate supporting artifact refs')
        return self


class Approval(Strict):
    control_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    decision: Literal['approved_pilot', 'not_approved', 'revoked']
    approver_role: str = Field(min_length=1, max_length=120)
    approved_at: datetime
    pilot_cohorts: list[str] = Field(min_length=1, max_length=10)
    window: Window
    criteria_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    links: list[Link] = Field(min_length=1, max_length=5)


class Confounder(Strict):
    domain: Literal['case_mix', 'seasonality', 'concurrent_changes', 'measurement', 'spillover']
    status: Literal['assessed_not_material', 'material', 'unresolved']
    explanation: str = Field(min_length=1, max_length=1000)
    links: list[Link] = Field(default_factory=list, max_length=5)


class ControlPlan(Strict):
    control_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    rca_reference: str = Field(pattern=r'^[A-Za-z0-9_.:/+=-]{1,512}$')
    rca_review_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    control_index: int = Field(ge=0, le=9)
    proposal: str = Field(min_length=1, max_length=1000)
    registered_at: datetime
    monitoring: MonitorConfig
    pilot_cohorts: list[str] = Field(min_length=1, max_length=10)
    comparators: dict[str, str] = Field(default_factory=dict)
    outcome_metric: str
    guardrail_metrics: list[str] = Field(min_length=1, max_length=10)
    fidelity_metric: str
    approval: Approval | None = None
    implemented_at: datetime | None = None
    implementation_claim: str = Field(min_length=1, max_length=1000)
    implementation_links: list[Link] = Field(default_factory=list, max_length=5)
    confounders: list[Confounder] = Field(min_length=5, max_length=5)

    @model_validator(mode='after')
    def check(self):
        if self.monitoring.windows is None:
            raise ValueError('control validation requires fixed approved windows, not rolling scope')
        metrics = {m.id: m for m in self.monitoring.metrics}
        roles = [self.outcome_metric, self.fidelity_metric, *self.guardrail_metrics]
        if len(set(roles)) != len(roles) or set(roles) != set(metrics):
            raise ValueError('configure exactly one outcome, one distinct fidelity metric and distinct guardrails')
        if metrics[self.outcome_metric].role != 'outcome' or any(metrics[k].role != 'guardrail' for k in [self.fidelity_metric, *self.guardrail_metrics]):
            raise ValueError('metric roles must match outcome and guardrails')
        if metrics[self.fidelity_metric].worse != 'lower':
            raise ValueError('implementation fidelity must be a higher-is-better proportion')
        if len(set(self.pilot_cohorts)) != len(self.pilot_cohorts):
            raise ValueError('duplicate pilot cohorts')
        if self.comparators and (set(self.comparators) != set(self.pilot_cohorts) or len(set(self.comparators.values())) != len(self.comparators)):
            raise ValueError('each pilot segment requires its own explicitly matched comparator')
        if set(self.pilot_cohorts) & set(self.comparators.values()):
            raise ValueError('pilot and comparator cohort IDs must differ')
        if set(self.monitoring.cohorts) != set(self.pilot_cohorts) | set(self.comparators.values()):
            raise ValueError('aggregate cohorts must equal pilot and comparator scope')
        if {c.domain for c in self.confounders} != DOMAINS:
            raise ValueError('review each confounding domain exactly once')
        self.registered_at = instant(self.registered_at)
        if self.implemented_at is not None:
            self.implemented_at = instant(self.implemented_at)
        if self.approval:
            self.approval.approved_at = instant(self.approval.approved_at)
        return self

    def criteria(self):
        return {'control_id': self.control_id, 'rca_review_sha256': self.rca_review_sha256,
            'control_index': self.control_index, 'proposal': self.proposal,
            'windows': self.monitoring.windows.model_dump(mode='json'),
            'metrics': [m.model_dump() for m in self.monitoring.metrics],
            'source': self.monitoring.source.model_dump(exclude={'dsn_env'}),
            'pilot_cohorts': self.pilot_cohorts, 'comparators': self.comparators,
            'outcome_metric': self.outcome_metric, 'guardrail_metrics': self.guardrail_metrics,
            'fidelity_metric': self.fidelity_metric, 'registered_at': self.registered_at.isoformat()}


def validate_context(plan, rca_review, evidence):
    """Validate structural scope and quote presence; source authenticity remains unverified."""
    problems, notes = [], []
    criteria_hash = digest(plan.criteria())
    try:
        assessment = Assessment.model_validate(rca_review['assessment'])
        if digest(rca_review) != plan.rca_review_sha256 or assessment.controls[plan.control_index].proposal != plan.proposal:
            problems.append('RCA report hash or selected control does not match the plan.')
    except (ValueError, KeyError, IndexError, TypeError):
        problems.append('RCA review does not contain a valid selected control.')
    sources = {}
    kinds = {}
    for artifact in evidence.artifacts:
        clean = redact(artifact.text)
        if clean != artifact.text:
            notes.append(f'{artifact.ref}: sensitive patterns redacted before evidence use.')
        sources[artifact.ref] = {'text': clean}
        kinds[artifact.ref] = artifact.kind
    approval = plan.approval
    pilot = plan.monitoring.windows.current
    if plan.registered_at > pilot.start:
        problems.append('Evaluation criteria were recorded after pilot start.')
    if approval is None:
        problems.append('No recorded pilot approval supplied.')
    elif (approval.decision != 'approved_pilot' or approval.control_id != plan.control_id or
          set(approval.pilot_cohorts) != set(plan.pilot_cohorts) or len(approval.pilot_cohorts) != len(plan.pilot_cohorts) or
          approval.window != pilot or approval.criteria_sha256 != criteria_hash or
          not plan.registered_at <= approval.approved_at <= pilot.start):
        problems.append('Pilot approval does not match control, criteria, scope or pre-pilot timing.')
    if approval and plan.implemented_at is not None and plan.implemented_at < approval.approved_at:
        problems.append('Recorded implementation predates the supplied pilot approval.')
    if plan.implemented_at is None or not plan.monitoring.windows.baseline.end <= plan.implemented_at <= pilot.start:
        problems.append('Implementation timing is unknown, contaminates baseline or starts within the pilot.')
    claims = {'implementation': plan.implementation_claim}
    links = {'implementation': plan.implementation_links}
    expected_kinds = {'implementation': 'implementation'}
    if approval:
        claims['approval'] = f'Approval for {plan.control_id} and criteria {criteria_hash}'
        links['approval'] = approval.links
        expected_kinds['approval'] = 'approval'
        if not any(criteria_hash in link.quote and plan.control_id in link.quote for link in approval.links):
            problems.append('Approval citation must explicitly bind the control ID and criteria hash.')
    for confounder in plan.confounders:
        if confounder.links or confounder.status == 'assessed_not_material':
            claims[confounder.domain] = confounder.explanation
            links[confounder.domain] = confounder.links
            expected_kinds[confounder.domain] = 'context'
    ledger = bind_claims(claims, {key: [EvidenceLink(**link.model_dump()) for link in items] for key, items in links.items()}, sources)
    if required_link_failures(ledger, tuple(claims)):
        problems.append('One or more required evidence links have missing/invalid sources, parts or quotes.')
    for key, items in links.items():
        if any(kinds.get(link.source_id) != expected_kinds[key] for link in items):
            problems.append(f'{key}: wrong supporting artifact kind.')
    # Do not persist unsanitized plan text or echoed sensitive quotes on a rejected run.
    texts = [plan.proposal, plan.implementation_claim, *[c.explanation for c in plan.confounders], *[l.quote for items in links.values() for l in items]]
    if approval:
        texts.append(approval.approver_role)
    if any(redact(text) != text for text in texts):
        problems.append('Plan text/citations contain sensitive patterns; provide a sanitized record.')
    return problems, notes, ledger, sources


def evaluate_control(plan, rca_review, evidence, fetch):
    plan.monitoring.resolve()  # Enforce closed windows before any retrieval.
    problems, notes, ledger, sources = validate_context(plan, rca_review, evidence)
    result = {'schema_version': 1, 'control_id': plan.control_id, 'rca_reference': plan.rca_reference,
        'rca_review_sha256': plan.rca_review_sha256, 'criteria_sha256': digest(plan.criteria()),
        'recommendation': 'insufficient_evidence', 'review_status': 'HUMAN_REVIEW_REQUIRED',
        'causal_attribution': 'NOT_ESTABLISHED', 'source_authenticity': 'UNVERIFIED',
        'reasons': problems, 'segments': [], 'limitations': notes,
        'actions_executed': False, 'rollout_authorized': False, 'notifications_sent': False, 'schedules_created': False}
    aggregates = None
    if not problems:
        result['criteria'] = plan.criteria()
        result['approval'] = plan.approval.model_dump(mode='json')
        result['provenance'] = {k: v.model_dump() for k, v in ledger.items()}
        result['supporting_evidence'] = sources
        result['confounder_review'] = [c.model_dump() for c in plan.confounders]
        aggregates = monitor(plan.monitoring, fetch)
        result['aggregate_sha256'] = aggregates['sha256']
        metrics = {m.id: m for m in plan.monitoring.metrics}
        findings = {(r['metric_id'], r['cohort_id']): r for r in aggregates['results']}
        confounded = any(c.status != 'assessed_not_material' for c in plan.confounders)
        def usable(row, current_only=False):
            if not current_only:
                return row['status'] != 'insufficient_evidence'
            return not any(reason == 'source_unreliable' or reason.startswith('current_') for reason in row['reasons'])
        def rate(row, window):
            v = row['windows'][window]
            return Fraction(v['numerator'], v['denominator'])
        for cohort in plan.pilot_cohorts:
            outcome = findings[(plan.outcome_metric, cohort)]
            fidelity = findings[(plan.fidelity_metric, cohort)]
            guardrails = [findings[(g, cohort)] for g in plan.guardrail_metrics]
            criteria = metrics[plan.outcome_metric]
            sign = 1 if criteria.worse == 'higher' else -1
            segment = {'cohort_id': cohort, 'recommendation': 'insufficient_evidence', 'reasons': [],
                       'outcome': outcome, 'guardrails': guardrails,
                       'pilot_fidelity': fidelity['windows']['current'], 'fidelity_issues': [r for r in fidelity['reasons'] if r.startswith('current_') or r == 'source_unreliable'],
                       'improvement_percentage_points': None, 'comparison_adjusted_change_percentage_points': None}
            # Reliable current guardrail breaches warrant safety review even with missing outcome data.
            breaches = [g['metric_id'] for g in guardrails if usable(g, True) and
                        (1 if metrics[g['metric_id']].worse == 'higher' else -1) *
                        (rate(g, 'current') - Fraction(str(metrics[g['metric_id']].threshold))) > 0]
            data_ok = usable(outcome) and usable(fidelity, True) and all(usable(g) for g in guardrails)
            baseline_exposure = [r for r in aggregates['evidence'] if r['metric_id'] == plan.fidelity_metric and r['cohort_id'] == cohort
                and instant(r['bucket_start']) < plan.monitoring.windows.baseline.end]
            baseline_contamination = any(r['numerator'] > 0 or r['missing'] > 0 or not r['population_complete'] or not r['finalized']
                or r['definition_version'] != metrics[plan.fidelity_metric].definition_version for r in baseline_exposure)
            segment['baseline_exposure_check'] = {'available_refs': [r['ref'] for r in baseline_exposure],
                'status': 'exposed_or_ambiguous' if baseline_contamination else 'no_exposure_in_available_records' if baseline_exposure else 'no_baseline_fidelity_records'}
            comparison_ok = True
            comparison = findings.get((plan.outcome_metric, plan.comparators.get(cohort, '')))
            if plan.comparators:
                comparison_fidelity = findings[(plan.fidelity_metric, plan.comparators[cohort])]
                comparison_ok = (comparison is not None and usable(comparison) and usable(comparison_fidelity) and
                    all(comparison_fidelity['windows'][window]['numerator'] == 0 and comparison_fidelity['windows'][window]['missing'] == 0
                        for window in ('baseline', 'current')))
                segment['comparison_outcome'] = comparison
                segment['comparison_exposure'] = comparison_fidelity
                segment['comparison_exposure_suitable'] = comparison_ok
            if breaches:
                segment.update(recommendation='stop', reasons=['Reliable pilot guardrail threshold breach: ' + ', '.join(breaches) + '. Recommend human review to suspend the pilot; attribution is unknown.'])
            elif not data_ok or not comparison_ok:
                segment['reasons'].append('Outcome, guardrail, fidelity or comparison evidence is insufficient.')
            elif baseline_contamination:
                segment['reasons'].append('Available baseline control-exposure evidence is positive or ambiguous; the untreated-baseline assumption is unsupported.')
            elif confounded:
                segment['reasons'].append('Material or unresolved confounding prevents a keep/change effectiveness conclusion.')
            else:
                improvement = sign * (rate(outcome, 'baseline') - rate(outcome, 'current'))
                segment['improvement_percentage_points'] = float(100 * improvement)
                adjusted = improvement
                if comparison:
                    adjusted -= sign * (rate(comparison, 'baseline') - rate(comparison, 'current'))
                    segment['comparison_adjusted_change_percentage_points'] = float(100 * adjusted)
                fidelity_ok = rate(fidelity, 'current') >= Fraction(str(metrics[plan.fidelity_metric].threshold))
                target_met = sign * (rate(outcome, 'current') - Fraction(str(criteria.threshold))) <= 0
                guardrail_deterioration = any((1 if metrics[g['metric_id']].worse == 'higher' else -1) *
                    (rate(g, 'current') - rate(g, 'baseline')) >= Fraction(str(metrics[g['metric_id']].min_change)) for g in guardrails)
                if not fidelity_ok:
                    segment.update(recommendation='change', reasons=['Implementation fidelity is below the approved criterion; improve or revise the pilot before judging effectiveness.'])
                elif guardrail_deterioration:
                    segment.update(recommendation='change', reasons=['A guardrail deteriorated by the configured amount even though its stop threshold was not crossed.'])
                elif improvement >= Fraction(str(criteria.min_change)) and adjusted >= Fraction(str(criteria.min_change)) and target_met:
                    segment.update(recommendation='keep', reasons=['Observed outcome improvement and target, pilot fidelity and guardrail criteria met in this segment; retain for human review within approved scope only.'])
                else:
                    segment.update(recommendation='change', reasons=['Outcome target or worthwhile improvement criterion was not met; reassess design or measurement, without claiming ineffectiveness is proven.'])
            result['segments'].append(segment)
        decisions = [s['recommendation'] for s in result['segments']]
        result['recommendation'] = ('stop' if 'stop' in decisions else 'insufficient_evidence' if 'insufficient_evidence' in decisions else 'change' if 'change' in decisions else 'keep')
        result['reasons'] = [f"{s['cohort_id']}: {s['recommendation']}" for s in result['segments']]
    result['limitations'] += ['Quote presence and plan hashes do not prove authentic approval, implementation or semantic support.',
        'Observed before/after and comparison-adjusted differences do not establish causation; residual confounding remains possible.',
        'Keep/change/stop are recommendations for human review only; they authorize no rollout, source change, schedule or notification.',
        'No pooled segment result is computed; distinct cohort IDs do not prove populations are disjoint.']
    if aggregates:
        result['limitations'] += aggregates['limitations']
    result['sha256'] = digest(result)
    return result, aggregates

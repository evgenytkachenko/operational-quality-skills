"""Fixed read operations over established SDKs; no arbitrary queries or tools."""
import os
from contextlib import contextmanager


def datadog_pages(source, config, read_page):
    cursor, seen, rows, notes = None, set(), [], []
    query = '(' + ' OR '.join(f'{source.case_field}:"{c}"' for c in config.case_ids) + ')'
    for _ in range(config.max_pages):
        limit = min(config.page_size, config.max_rows - len(rows))
        start = config.start if source.kind == 'datadog_logs' else str(int(config.start.timestamp() * 1000))
        end = config.end if source.kind == 'datadog_logs' else str(int(config.end.timestamp() * 1000))
        kwargs = dict(filter_query=query, filter_from=start, filter_to=end, page_limit=limit)
        if cursor:
            kwargs['page_cursor'] = cursor
        response = read_page(**kwargs)
        if not isinstance(response, dict) or not isinstance(response.get('data'), list):
            raise ValueError('unexpected Datadog response')
        batch = response['data']
        rows.extend(batch[:limit])
        if len(batch) > limit:
            notes.append('server exceeded requested page size; discarded excess')
        cursor = response.get('meta', {}).get('page', {}).get('after')
        if not cursor:
            return rows, notes
        if not isinstance(cursor, str) or cursor in seen:
            notes.append('invalid or repeated cursor; truncated')
            return rows, notes
        seen.add(cursor)
        if len(rows) >= config.max_rows:
            break
    notes.append('pagination budget reached with remaining cursor; truncated')
    return rows, notes


@contextmanager
def datadog_reader(source, config):
    from datadog_api_client import ApiClient, Configuration
    from datadog_api_client.v2.api.logs_api import LogsApi
    from datadog_api_client.v2.api.spans_api import SpansApi
    from datadog_api_client.v2.api.events_api import EventsApi
    settings = Configuration(request_timeout=config.timeout_seconds)
    settings.server_variables['site'] = source.site
    settings.enable_retry = False
    with ApiClient(settings) as client:
        readers = {'datadog_logs': LogsApi(client).list_logs_get,
                   'datadog_spans': SpansApi(client).list_spans_get,
                   'datadog_events': EventsApi(client).list_events}
        method = readers[source.kind]
        def read(**kwargs):
            return method(**kwargs).to_dict()
        yield read


def postgres_rows(source, config, connect=None):
    import psycopg
    from psycopg import sql
    from psycopg.rows import dict_row
    connect = connect or psycopg.connect
    # DSN lives outside the config/report. A dedicated SELECT-only role is also required.
    with connect(os.environ[source.dsn_env], connect_timeout=config.timeout_seconds, row_factory=dict_row) as conn:
        conn.read_only = True
        with conn.transaction():
            conn.execute("SELECT set_config('statement_timeout', %s, true)", (str(config.timeout_seconds * 1000),))
            columns = sql.SQL(', ').join(sql.Identifier(v) for v in source.fields.values())
            query = sql.SQL('SELECT {} FROM {}.{} WHERE {} = ANY(%s) AND {} >= %s AND {} < %s ORDER BY {}, {} LIMIT %s').format(
                columns, sql.Identifier(source.schema_name), sql.Identifier(source.view),
                sql.Identifier(source.fields['case_id']), sql.Identifier(source.fields['timestamp']),
                sql.Identifier(source.fields['timestamp']), sql.Identifier(source.fields['timestamp']), sql.Identifier(source.fields['id']))
            rows = conn.execute(query, (config.case_ids, config.start, config.end, config.max_rows + 1)).fetchall()
    notes = ['row cap reached; truncated'] if len(rows) > config.max_rows else []
    return rows[:config.max_rows], notes


def fetch_live(source, config):
    if source.kind == 'postgres':
        return postgres_rows(source, config)
    with datadog_reader(source, config) as read:
        return datadog_pages(source, config, read)

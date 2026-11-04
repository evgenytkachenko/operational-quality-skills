"""One fixed bounded aggregate SELECT using the existing official psycopg client."""
import os


def fetch_aggregates(config, windows, connect=None):
    import psycopg
    from psycopg import sql
    from psycopg.rows import dict_row
    source = config.source
    connect = connect or psycopg.connect
    with connect(os.environ[source.dsn_env], connect_timeout=config.timeout_seconds, row_factory=dict_row) as conn:
        conn.read_only = True
        with conn.transaction():
            conn.execute("SELECT set_config('statement_timeout', %s, true)", (str(config.timeout_seconds * 1000),))
            columns = sql.SQL(', ').join(sql.Identifier(v) for v in source.fields.values())
            col = lambda name: sql.Identifier(source.fields[name])
            query = sql.SQL('SELECT {} FROM {}.{} WHERE {} = ANY(%s) AND {} = ANY(%s) '
                'AND (({} >= %s AND {} < %s) OR ({} >= %s AND {} < %s)) '
                'ORDER BY {}, {}, {}, {} LIMIT %s').format(columns, sql.Identifier(source.schema_name), sql.Identifier(source.view),
                col('metric_id'), col('cohort_id'), col('bucket_start'), col('bucket_start'), col('bucket_start'), col('bucket_start'),
                col('metric_id'), col('cohort_id'), col('bucket_start'), col('id'))
            params = ([m.id for m in config.metrics], config.cohorts, windows.baseline.start, windows.baseline.end,
                      windows.current.start, windows.current.end, config.max_rows + 1)
            rows = conn.execute(query, params).fetchall()
    return rows[:config.max_rows], len(rows) > config.max_rows

"""Bounded manifest lookup using the existing workflow PostgreSQL connection profile."""
import os


def fetch_manifests(config, connect=None):
    import psycopg
    from psycopg import sql
    from psycopg.rows import dict_row
    workflow = next(s for s in config.collection.sources if s.name == config.workflow_source)
    source = config.manifest_source
    connect = connect or psycopg.connect
    with connect(os.environ[workflow.dsn_env], connect_timeout=config.collection.timeout_seconds, row_factory=dict_row) as conn:
        conn.read_only = True
        with conn.transaction():
            conn.execute("SELECT set_config('statement_timeout', %s, true)", (str(config.collection.timeout_seconds*1000),))
            query = sql.SQL('SELECT {} FROM {}.{} WHERE {} = ANY(%s) ORDER BY {}, {} LIMIT %s').format(
                sql.SQL(', ').join(sql.Identifier(v) for v in source.fields.values()),
                sql.Identifier(source.schema_name), sql.Identifier(source.view), sql.Identifier(source.fields['case_id']),
                sql.Identifier(source.fields['case_id']), sql.Identifier(source.fields['id']))
            rows = conn.execute(query, (config.collection.case_ids, len(config.collection.case_ids)+1)).fetchall()
    return rows[:len(config.collection.case_ids)], len(rows)>len(config.collection.case_ids)

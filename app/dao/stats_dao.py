from app.db.connection import get_conn


class StatsDao:
    def table_count(self, table_name: str, schema: str = "dbo") -> int:
        # Safety: allow only letters, numbers, underscore
        safe_table = "".join(ch for ch in table_name if ch.isalnum() or ch == "_")
        safe_schema = "".join(ch for ch in schema if ch.isalnum() or ch == "_")

        sql = f"SELECT COUNT(*) FROM {safe_schema}.{safe_table};"
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            return int(cur.fetchone()[0])

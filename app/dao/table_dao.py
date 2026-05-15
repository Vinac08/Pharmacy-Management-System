from app.db.connection import get_conn


class TableDao:
    """
    Generic DAO to display any table quickly:
    SELECT TOP N * FROM dbo.<table>
    """
    def fetch_all(self, table_name: str, limit: int = 200, schema: str = "dbo"):
        limit = int(limit)
        if limit <= 0:
            limit = 200

        # Safety: allow only letters, numbers, underscore
        safe_table = "".join(ch for ch in table_name if ch.isalnum() or ch == "_")
        safe_schema = "".join(ch for ch in schema if ch.isalnum() or ch == "_")

        sql = f"SELECT TOP {limit} * FROM {safe_schema}.{safe_table};"

        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            cols = [c[0] for c in cur.description]
            rows = cur.fetchall()
            return cols, rows

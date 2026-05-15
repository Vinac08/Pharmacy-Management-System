from app.db.connection import get_conn


class MetaDao:
    def get_columns(self, table_name: str, schema: str = "dbo") -> list[dict]:
        sql = """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION;
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (schema, table_name))
            rows = cur.fetchall()
            return [
                {"name": r[0], "type": r[1], "nullable": (str(r[2]).upper() == "YES")}
                for r in rows
            ]

    def get_primary_key(self, table_name: str, schema: str = "dbo") -> str | None:
        sql = """
        SELECT c.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE c
            ON tc.CONSTRAINT_NAME = c.CONSTRAINT_NAME
        WHERE tc.TABLE_SCHEMA = ? AND tc.TABLE_NAME = ? AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY';
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (schema, table_name))
            row = cur.fetchone()
            return row[0] if row else None

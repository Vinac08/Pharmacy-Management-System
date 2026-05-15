from app.db.connection import get_conn
from app.dao.meta_dao import MetaDao


class GenericCrudDao:
    def __init__(self, table_name: str, schema: str = "dbo"):
        self.table = table_name
        self.schema = schema
        self.meta = MetaDao()
        self.pk = self.meta.get_primary_key(table_name, schema)

    def find_all(self, limit: int = 200) -> tuple[list[str], list[tuple]]:
        sql = f"SELECT TOP {int(limit)} * FROM {self.schema}.{self.table};"
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            cols = [c[0] for c in cur.description]
            rows = cur.fetchall()
            return cols, rows

    def insert(self, values: dict) -> None:
        """
        values: {column_name: value} only for columns you want to insert.
        """
        if not values:
            return

        cols = ", ".join(values.keys())
        qmarks = ", ".join(["?"] * len(values))
        sql = f"INSERT INTO {self.schema}.{self.table} ({cols}) VALUES ({qmarks});"

        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, tuple(values.values()))

    def delete_by_pk(self, pk_value) -> None:
        if not self.pk:
            raise ValueError(f"No primary key found for {self.schema}.{self.table}")

        sql = f"DELETE FROM {self.schema}.{self.table} WHERE {self.pk} = ?;"
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (pk_value,))

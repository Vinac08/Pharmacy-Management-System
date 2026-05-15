# app/dao/sales_dao.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

import pyodbc

from app.db.connection import get_conn


@dataclass(frozen=True)
class CustomerItem:
    customer_id: int
    label: str


@dataclass(frozen=True)
class TransactionItem:
    transaction_id: int
    label: str


@dataclass(frozen=True)
class SaleRow:
    sale_id: int
    customer_id: int
    transaction_id: int
    sale_date: str
    total_amount: Decimal


class SalesDao:
    # ---------- helpers ----------
    def _has_table(self, conn, table: str, schema: str = "dbo") -> bool:
        sql = """
        SELECT 1
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?;
        """
        cur = conn.cursor()
        cur.execute(sql, (schema, table))
        return cur.fetchone() is not None

    def _has_column(self, conn, table: str, column: str, schema: str = "dbo") -> bool:
        sql = """
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?;
        """
        cur = conn.cursor()
        cur.execute(sql, (schema, table, column))
        return cur.fetchone() is not None

    # ---------- dropdown ----------
    def list_customers(self) -> List[CustomerItem]:
        with get_conn() as conn:
            cur = conn.cursor()

            if self._has_table(conn, "Customers") and self._has_column(conn, "Customers", "name"):
                rows = cur.execute("SELECT customer_id, name FROM dbo.Customers ORDER BY customer_id DESC;").fetchall()
                return [CustomerItem(int(r[0]), str(r[1])) for r in rows]

            if (self._has_table(conn, "Customers")
                and self._has_column(conn, "Customers", "first_name")
                and self._has_column(conn, "Customers", "last_name")):
                rows = cur.execute(
                    """
                    SELECT customer_id, CONCAT(first_name, ' ', last_name)
                    FROM dbo.Customers
                    ORDER BY customer_id DESC;
                    """
                ).fetchall()
                return [CustomerItem(int(r[0]), str(r[1])) for r in rows]

            if (self._has_table(conn, "Customers") and self._has_table(conn, "Person")
                and self._has_column(conn, "Customers", "person_id")
                and self._has_column(conn, "Person", "first_name")
                and self._has_column(conn, "Person", "last_name")):
                rows = cur.execute(
                    """
                    SELECT c.customer_id, CONCAT(p.first_name, ' ', p.last_name)
                    FROM dbo.Customers c
                    JOIN dbo.Person p ON p.person_id = c.person_id
                    ORDER BY c.customer_id DESC;
                    """
                ).fetchall()
                return [CustomerItem(int(r[0]), str(r[1])) for r in rows]

            rows = cur.execute("SELECT customer_id FROM dbo.Customers ORDER BY customer_id DESC;").fetchall()
            return [CustomerItem(int(r[0]), f"Customer #{int(r[0])}") for r in rows]

    def list_transactions(self, limit: int = 500) -> List[TransactionItem]:
        """
        Dropdown for existing transactions.
        Format: Transaction #ID | MedID | Qty | Price
        """
        sql = f"""
        SELECT TOP ({int(limit)})
            transaction_id, medicine_id, quantity_sold, CAST(price_per_unit AS decimal(10,2)) AS price_per_unit
        FROM dbo.Transactions
        ORDER BY transaction_id DESC;
        """
        with get_conn() as conn:
            rows = conn.cursor().execute(sql).fetchall()
            items: List[TransactionItem] = []
            for r in rows:
                tid = int(r[0])
                med_id = int(r[1])
                qty = int(r[2])
                price = Decimal(str(r[3]))
                label = f"Tx #{tid} | Med #{med_id} | Qty {qty} | {price:.2f}"
                items.append(TransactionItem(tid, label))
            return items

    # ---------- read/search ----------
    def find_all(self, limit: int = 500) -> List[SaleRow]:
        sql = f"""
        SELECT TOP ({int(limit)})
            sale_id, customer_id, transaction_id,
            CONVERT(varchar(10), sale_date, 120) AS sale_date,
            CAST(total_amount AS decimal(10,2)) AS total_amount
        FROM dbo.Sales
        ORDER BY sale_id DESC;
        """
        with get_conn() as conn:
            rows = conn.cursor().execute(sql).fetchall()
            return [
                SaleRow(int(r[0]), int(r[1]), int(r[2]), str(r[3]), Decimal(str(r[4])))
                for r in rows
            ]

    def search(
        self,
        customer_id: Optional[int] = None,
        transaction_id: Optional[int] = None,
    ) -> List[SaleRow]:
        where = []
        params = []

        if customer_id is not None:
            where.append("customer_id = ?")
            params.append(int(customer_id))
        if transaction_id is not None:
            where.append("transaction_id = ?")
            params.append(int(transaction_id))

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        sql = f"""
        SELECT
            sale_id, customer_id, transaction_id,
            CONVERT(varchar(10), sale_date, 120) AS sale_date,
            CAST(total_amount AS decimal(10,2)) AS total_amount
        FROM dbo.Sales
        {where_sql}
        ORDER BY sale_id DESC;
        """

        with get_conn() as conn:
            rows = conn.cursor().execute(sql, params).fetchall()
            return [
                SaleRow(int(r[0]), int(r[1]), int(r[2]), str(r[3]), Decimal(str(r[4])))
                for r in rows
            ]

    # ---------- create: link existing transaction ----------
    def create_sale(self, customer_id: int, transaction_id: int) -> int:
        if int(customer_id) <= 0:
            raise ValueError("customer_id must be > 0.")
        if int(transaction_id) <= 0:
            raise ValueError("transaction_id must be > 0.")

        with get_conn() as conn:
            conn.autocommit = False
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO dbo.Sales (customer_id, transaction_id)
                    OUTPUT INSERTED.sale_id
                    VALUES (?, ?);
                    """,
                    (int(customer_id), int(transaction_id)),
                )
                sale_id = int(cur.fetchone()[0])
                conn.commit()
                return sale_id
            except pyodbc.IntegrityError as e:
                conn.rollback()
                msg = str(e)
                if "UQ_Sales_transaction_id" in msg:
                    raise RuntimeError("This transaction is already linked to another Sale.") from e
                raise
            except Exception:
                conn.rollback()
                raise

    # ---------- update ----------
    def update_sale_customer(self, sale_id: int, customer_id: int) -> None:
        if int(sale_id) <= 0:
            raise ValueError("sale_id must be > 0.")
        if int(customer_id) <= 0:
            raise ValueError("customer_id must be > 0.")

        with get_conn() as conn:
            conn.autocommit = False
            cur = conn.cursor()
            try:
                cur.execute(
                    "UPDATE dbo.Sales SET customer_id = ? WHERE sale_id = ?;",
                    (int(customer_id), int(sale_id)),
                )
                if cur.rowcount == 0:
                    raise RuntimeError("Sale not found.")
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def update_sale_transaction(self, sale_id: int, transaction_id: int) -> None:
        if int(sale_id) <= 0:
            raise ValueError("sale_id must be > 0.")
        if int(transaction_id) <= 0:
            raise ValueError("transaction_id must be > 0.")

        with get_conn() as conn:
            conn.autocommit = False
            cur = conn.cursor()
            try:
                cur.execute(
                    "UPDATE dbo.Sales SET transaction_id = ? WHERE sale_id = ?;",
                    (int(transaction_id), int(sale_id)),
                )
                if cur.rowcount == 0:
                    raise RuntimeError("Sale not found.")
                conn.commit()
            except pyodbc.IntegrityError as e:
                conn.rollback()
                msg = str(e)
                if "UQ_Sales_transaction_id" in msg:
                    raise RuntimeError("This transaction_id is already linked to another Sale.") from e
                raise
            except Exception:
                conn.rollback()
                raise

    # ---------- delete ----------
    def delete_sale(self, sale_id: int) -> None:
        if int(sale_id) <= 0:
            raise ValueError("sale_id must be > 0.")

        with get_conn() as conn:
            conn.autocommit = False
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM dbo.Sales WHERE sale_id = ?;", (int(sale_id),))
                if cur.rowcount == 0:
                    raise RuntimeError("Sale not found.")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
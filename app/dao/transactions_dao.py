# app/dao/transactions_dao.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

import pyodbc

from app.db.connection import get_conn


@dataclass(frozen=True)
class MedicineItem:
    medicine_id: int
    label: str


@dataclass(frozen=True)
class TransactionRow:
    transaction_id: int
    medicine_id: int
    quantity_sold: int
    price_per_unit: Decimal


class TransactionsDao:
    # ---------- dropdown ----------
    def list_medicines(self) -> List[MedicineItem]:
        sql = "SELECT medicine_id, name FROM dbo.Medicines ORDER BY medicine_id DESC;"
        with get_conn() as conn:
            rows = conn.cursor().execute(sql).fetchall()
            return [MedicineItem(int(r[0]), f"{str(r[1])} (#{int(r[0])})") for r in rows]

    # ✅ NEW: read price from Medicines table
    def get_medicine_price(self, medicine_id: int) -> Decimal:
        if int(medicine_id) <= 0:
            raise ValueError("medicine_id must be > 0.")

        sql = "SELECT CAST(price AS decimal(10,2)) FROM dbo.Medicines WHERE medicine_id = ?;"
        with get_conn() as conn:
            row = conn.cursor().execute(sql, (int(medicine_id),)).fetchone()
            if not row or row[0] is None:
                raise RuntimeError("Medicine price not found.")
            return Decimal(str(row[0]))

    # ---------- read/search ----------
    def find_all(self, limit: int = 500) -> List[TransactionRow]:
        sql = f"""
        SELECT TOP ({int(limit)})
            transaction_id, medicine_id, quantity_sold, price_per_unit
        FROM dbo.Transactions
        ORDER BY transaction_id DESC;
        """
        with get_conn() as conn:
            rows = conn.cursor().execute(sql).fetchall()
            return [
                TransactionRow(int(r[0]), int(r[1]), int(r[2]), Decimal(str(r[3])))
                for r in rows
            ]

    def search(
        self,
        transaction_id: Optional[int] = None,
        medicine_id: Optional[int] = None,
    ) -> List[TransactionRow]:
        where = []
        params: list = []

        if transaction_id is not None:
            where.append("transaction_id = ?")
            params.append(int(transaction_id))
        if medicine_id is not None:
            where.append("medicine_id = ?")
            params.append(int(medicine_id))

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        sql = f"""
        SELECT transaction_id, medicine_id, quantity_sold, price_per_unit
        FROM dbo.Transactions
        {where_sql}
        ORDER BY transaction_id DESC;
        """

        with get_conn() as conn:
            rows = conn.cursor().execute(sql, params).fetchall()
            return [
                TransactionRow(int(r[0]), int(r[1]), int(r[2]), Decimal(str(r[3])))
                for r in rows
            ]

    # ---------- create/update/delete ----------
    def insert(self, medicine_id: int, quantity_sold: int, price_per_unit: Decimal) -> int:
        if int(medicine_id) <= 0:
            raise ValueError("medicine_id must be > 0.")
        if int(quantity_sold) <= 0:
            raise ValueError("quantity_sold must be > 0.")
        p = Decimal(str(price_per_unit))
        if p <= 0:
            raise ValueError("price_per_unit must be > 0.")

        with get_conn() as conn:
            conn.autocommit = False
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO dbo.Transactions (medicine_id, quantity_sold, price_per_unit)
                    OUTPUT INSERTED.transaction_id
                    VALUES (?, ?, ?);
                    """,
                    (int(medicine_id), int(quantity_sold), p),
                )
                tid = cur.fetchone()[0]
                conn.commit()
                return int(tid)
            except Exception:
                conn.rollback()
                raise

    def update(self, transaction_id: int, medicine_id: int, quantity_sold: int, price_per_unit: Decimal) -> None:
        if int(transaction_id) <= 0:
            raise ValueError("transaction_id must be > 0.")
        if int(medicine_id) <= 0:
            raise ValueError("medicine_id must be > 0.")
        if int(quantity_sold) <= 0:
            raise ValueError("quantity_sold must be > 0.")
        p = Decimal(str(price_per_unit))
        if p <= 0:
            raise ValueError("price_per_unit must be > 0.")

        with get_conn() as conn:
            conn.autocommit = False
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    UPDATE dbo.Transactions
                    SET medicine_id = ?, quantity_sold = ?, price_per_unit = ?
                    WHERE transaction_id = ?;
                    """,
                    (int(medicine_id), int(quantity_sold), p, int(transaction_id)),
                )
                if cur.rowcount == 0:
                    raise RuntimeError("Transaction not found.")
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def delete(self, transaction_id: int) -> None:
        if int(transaction_id) <= 0:
            raise ValueError("transaction_id must be > 0.")

        with get_conn() as conn:
            conn.autocommit = False
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM dbo.Transactions WHERE transaction_id = ?;", (int(transaction_id),))
                if cur.rowcount == 0:
                    raise RuntimeError("Transaction not found.")
                conn.commit()
            except pyodbc.IntegrityError as e:
                conn.rollback()
                raise RuntimeError("Cannot delete: this transaction is referenced by another table (FK constraint).") from e
            except Exception:
                conn.rollback()
                raise
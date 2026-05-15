# app/dao/prescriptions_dao.py
from __future__ import annotations

from typing import List, Tuple, Optional
from datetime import date

from app.db.connection import get_conn


class PrescriptionsDao:
    TABLE = "dbo.Prescriptions"

    # -------------------------
    # Dropdown: customers
    # -------------------------
    def list_customers_for_dropdown(self, limit: int = 500) -> List[Tuple[int, str]]:
        sql = f"""
        SELECT TOP ({limit})
            c.customer_id,
            CONCAT(CAST(c.customer_id AS VARCHAR(20)), ' - ', p.first_name, ' ', p.last_name) AS label
        FROM dbo.Customers c
        JOIN dbo.Person p ON p.person_id = c.person_id
        ORDER BY c.customer_id DESC;
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
        return [(int(r[0]), str(r[1])) for r in rows]

    # -------------------------
    # Reads
    # -------------------------
    def fetch_all(self, limit: int = 200) -> list[tuple]:
        # Join to show customer name in table
        sql = f"""
        SELECT TOP ({limit})
            pr.prescription_id,
            pr.customer_id,
            CONCAT(p.first_name, ' ', p.last_name) AS customer_name,
            pr.doctor_name,
            pr.date_issued,
            pr.valid_till,
            pr.details
        FROM {self.TABLE} pr
        JOIN dbo.Customers c ON c.customer_id = pr.customer_id
        JOIN dbo.Person p ON p.person_id = c.person_id
        ORDER BY pr.prescription_id DESC;
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            return cur.fetchall()

    def fetch_one(self, prescription_id: int) -> Optional[tuple]:
        sql = f"""
        SELECT
            prescription_id,
            customer_id,
            doctor_name,
            date_issued,
            valid_till,
            details
        FROM {self.TABLE}
        WHERE prescription_id = ?;
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (prescription_id,))
            return cur.fetchone()

    # -------------------------
    # Writes
    # -------------------------
    def insert(
        self,
        customer_id: int,
        doctor_name: str,
        date_issued: date,
        valid_till: Optional[date],
        details: Optional[str],
    ) -> int:
        doctor_name = (doctor_name or "").strip()
        if not doctor_name:
            raise ValueError("doctor_name is required.")

        details = (details or "").strip() or None

        sql = f"""
        INSERT INTO {self.TABLE} (customer_id, doctor_name, date_issued, details, valid_till)
        OUTPUT INSERTED.prescription_id
        VALUES (?, ?, ?, ?, ?);
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (customer_id, doctor_name, date_issued, details, valid_till))
            new_id = cur.fetchone()[0]
            conn.commit()
            return int(new_id)

    def update(
        self,
        prescription_id: int,
        customer_id: int,
        doctor_name: str,
        date_issued: date,
        valid_till: Optional[date],
        details: Optional[str],
    ) -> None:
        doctor_name = (doctor_name or "").strip()
        if not doctor_name:
            raise ValueError("doctor_name is required.")

        details = (details or "").strip() or None

        sql = f"""
        UPDATE {self.TABLE}
        SET customer_id = ?,
            doctor_name = ?,
            date_issued = ?,
            details = ?,
            valid_till = ?
        WHERE prescription_id = ?;
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (customer_id, doctor_name, date_issued, details, valid_till, prescription_id))
            conn.commit()

    def delete(self, prescription_id: int) -> None:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {self.TABLE} WHERE prescription_id = ?;", (prescription_id,))
            conn.commit()
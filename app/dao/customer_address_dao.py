# app/dao/customer_address_dao.py
from __future__ import annotations

from typing import List, Tuple, Optional

from app.db.connection import get_conn


class CustomerAddressDao:
    TABLE = "dbo.Customer_Address"

    # -------------------------
    # Dropdown data
    # -------------------------
    def list_customers_for_dropdown(self, limit: int = 500) -> List[Tuple[int, str]]:
        """
        Returns list of (customer_id, label) for the dropdown.
        label example: "13 - Ersi Çejku"
        """
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
    def fetch_one(self, customer_id: int) -> Optional[tuple]:
        sql = f"""
        SELECT
            customer_id,
            street,
            city,
            postal_code,
            country
        FROM {self.TABLE}
        WHERE customer_id = ?;
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (customer_id,))
            return cur.fetchone()

    def fetch_all(self, limit: int = 200) -> list[tuple]:
        sql = f"""
        SELECT TOP ({limit})
            customer_id,
            street,
            city,
            postal_code,
            country
        FROM {self.TABLE}
        ORDER BY customer_id DESC;
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            return cur.fetchall()

    # -------------------------
    # Write: UPSERT
    # -------------------------
    def upsert(
        self,
        customer_id: int,
        street: str | None,
        city: str | None,
        postal_code: str | None,
        country: str | None,
    ) -> str:
        """
        Insert if customer_id not present in dbo.Customer_Address,
        otherwise update.
        Returns: "inserted" or "updated"
        """

        # normalize empty strings -> NULL
        street = (street or "").strip() or None
        city = (city or "").strip() or None
        postal_code = (postal_code or "").strip() or None
        country = (country or "").strip() or None

        with get_conn() as conn:
            cur = conn.cursor()

            # 1) check existence (SELECT -> safe to fetchone)
            cur.execute(f"SELECT 1 FROM {self.TABLE} WHERE customer_id = ?;", (customer_id,))
            exists = cur.fetchone() is not None

            if exists:
                # 2a) UPDATE (NO fetching here!)
                cur.execute(
                    f"""
                    UPDATE {self.TABLE}
                    SET street = ?, city = ?, postal_code = ?, country = ?
                    WHERE customer_id = ?;
                    """,
                    (street, city, postal_code, country, customer_id),
                )
                conn.commit()
                return "updated"

            # 2b) INSERT (NO fetching here!)
            cur.execute(
                f"""
                INSERT INTO {self.TABLE} (customer_id, street, city, postal_code, country)
                VALUES (?, ?, ?, ?, ?);
                """,
                (customer_id, street, city, postal_code, country),
            )
            conn.commit()
            return "inserted"

    # -------------------------
    # Delete
    # -------------------------
    def delete(self, customer_id: int) -> None:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {self.TABLE} WHERE customer_id = ?;", (customer_id,))
            conn.commit()
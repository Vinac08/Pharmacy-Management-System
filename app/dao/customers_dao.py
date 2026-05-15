# app/dao/customers_dao.py
from __future__ import annotations

from typing import Optional, Tuple
from app.db.connection import get_conn


class CustomersDao:
    """
    Handles the correct DB order:
      - Person (person_type='Customer')
      - Customers (FK person_id)
    """

    # ---------- READ ----------
    def fetch_joined(self, limit: int = 200) -> list[tuple]:
        sql = f"""
        SELECT TOP ({limit})
            c.customer_id,
            c.person_id,
            p.first_name,
            p.last_name,
            c.phone_number,
            c.email,
            c.address
        FROM dbo.Customers c
        JOIN dbo.Person p ON p.person_id = c.person_id
        ORDER BY c.customer_id DESC;
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            return cur.fetchall()

    # ---------- CREATE ----------
    def create_customer(
        self,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Tuple[int, int]:
        """
        Returns (customer_id, person_id)
        """
        with get_conn() as conn:
            cur = conn.cursor()

            # 1) Person
            cur.execute(
                """
                INSERT INTO dbo.Person (first_name, last_name, person_type)
                OUTPUT INSERTED.person_id
                VALUES (?, ?, 'Customer');
                """,
                (first_name, last_name),
            )
            person_id = int(cur.fetchone()[0])

            # 2) Customers
            cur.execute(
                """
                INSERT INTO dbo.Customers (person_id, phone_number, email, address)
                OUTPUT INSERTED.customer_id
                VALUES (?, ?, ?, ?);
                """,
                (person_id, phone, email, address),
            )
            customer_id = int(cur.fetchone()[0])

            conn.commit()
            return customer_id, person_id

    # ---------- UPDATE ----------
    def update_customer(
        self,
        customer_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
    ) -> None:
        with get_conn() as conn:
            cur = conn.cursor()

            # get person_id
            cur.execute("SELECT person_id FROM dbo.Customers WHERE customer_id = ?;", (customer_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Customer not found (customer_id={customer_id})")
            person_id = int(row[0])

            # update Person if provided
            if first_name is not None or last_name is not None:
                sets = []
                params = []
                if first_name is not None:
                    sets.append("first_name = ?")
                    params.append(first_name)
                if last_name is not None:
                    sets.append("last_name = ?")
                    params.append(last_name)
                params.append(person_id)
                cur.execute(
                    f"UPDATE dbo.Person SET {', '.join(sets)} WHERE person_id = ?;",
                    tuple(params),
                )

            # update Customers (these can be NULL)
            sets = []
            params = []
            if phone is not None:
                sets.append("phone_number = ?")
                params.append(phone)
            if email is not None:
                sets.append("email = ?")
                params.append(email)
            if address is not None:
                sets.append("address = ?")
                params.append(address)

            if sets:
                params.append(customer_id)
                cur.execute(
                    f"UPDATE dbo.Customers SET {', '.join(sets)} WHERE customer_id = ?;",
                    tuple(params),
                )

            conn.commit()

    # ---------- DELETE ----------
    def delete_customer(self, customer_id: int) -> None:
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("SELECT person_id FROM dbo.Customers WHERE customer_id = ?;", (customer_id,))
            row = cur.fetchone()
            if not row:
                return
            person_id = int(row[0])

            # delete customer first (FK)
            cur.execute("DELETE FROM dbo.Customers WHERE customer_id = ?;", (customer_id,))
            # delete person after
            cur.execute("DELETE FROM dbo.Person WHERE person_id = ?;", (person_id,))

            conn.commit()
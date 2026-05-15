# app/dao/people_crud_dao.py
from __future__ import annotations

from app.db.connection import get_conn


class PeopleCrudDao:
    """
    Supertype/Subtype-safe CRUD for:
      - dbo.Person (supertype)
      - dbo.Customers (subtype)
      - dbo.Sellers (subtype)

    Rules supported:
      - CK_Person_Type: person_type in ('Customer', 'Seller')
      - Customers.person_id NOT NULL (FK -> Person)
      - Sellers.person_id NOT NULL + UNIQUE (FK -> Person)
      - Trigger on Sellers: blocks insert/update if linked Person.person_type <> 'Seller'

    NOTE:
      - dbo.Sellers in your DB does NOT have is_active -> removed.
    """

    # -------------------------
    # CREATE
    # -------------------------

    def create_customer(
        self,
        first_name: str,
        last_name: str,
        phone: str | None,
        email: str | None,
        customer_name: str,
        address: str | None,
    ) -> tuple[int, int]:
        """Returns: (customer_id, person_id)"""
        with get_conn() as conn:
            cur = conn.cursor()

            # Insert Person
            sql_person = """
            INSERT INTO dbo.Person (first_name, last_name, phone_number, email, person_type)
            OUTPUT INSERTED.person_id
            VALUES (?, ?, ?, ?, 'Customer');
            """
            cur.execute(sql_person, (first_name, last_name, phone, email))
            person_id = int(cur.fetchone()[0])

            # Insert Customer
            sql_customer = """
            INSERT INTO dbo.Customers (name, phone_number, email, address, person_id)
            OUTPUT INSERTED.customer_id
            VALUES (?, ?, ?, ?, ?);
            """
            cur.execute(sql_customer, (customer_name, phone, email, address, person_id))
            customer_id = int(cur.fetchone()[0])

            return customer_id, person_id

    def create_seller(
        self,
        first_name: str,
        last_name: str,
        phone: str | None,
        email: str | None,
        hire_date=None,
        position: str | None = None,
        salary: float | None = None,
    ) -> tuple[int, int]:
        """
        Returns: (seller_id, person_id)

        IMPORTANT:
        dbo.Sellers has a trigger, so avoid OUTPUT directly on Sellers.
        We use the fact that Sellers.person_id is UNIQUE to fetch seller_id reliably.
        """
        with get_conn() as conn:
            cur = conn.cursor()

            # 1) Insert Person as Seller (required by trigger)
            sql_person = """
            INSERT INTO dbo.Person (first_name, last_name, phone_number, email, person_type)
            OUTPUT INSERTED.person_id
            VALUES (?, ?, ?, ?, 'Seller');
            """
            cur.execute(sql_person, (first_name, last_name, phone, email))
            person_id = int(cur.fetchone()[0])

            # 2) Insert Sellers (NO is_active column)
            cur.execute(
                """
                INSERT INTO dbo.Sellers (person_id, hire_date, position, salary)
                VALUES (?, ?, ?, ?);
                """,
                (person_id, hire_date, position, salary),
            )

            # 3) Retrieve seller_id using UNIQUE person_id
            cur.execute("SELECT seller_id FROM dbo.Sellers WHERE person_id = ?;", (person_id,))
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Seller inserted but seller_id could not be retrieved.")
            seller_id = int(row[0])

            return seller_id, person_id

    # -------------------------
    # UPDATE
    # -------------------------

    def update_customer(
        self,
        customer_id: int,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        customer_name: str | None = None,
        address: str | None = None,
    ) -> None:
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("SELECT person_id FROM dbo.Customers WHERE customer_id = ?;", (customer_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Customer not found: customer_id={customer_id}")
            person_id = int(row[0])

            # Update Person (guard type)
            person_sets, person_vals = [], []
            if first_name is not None:
                person_sets.append("first_name = ?"); person_vals.append(first_name)
            if last_name is not None:
                person_sets.append("last_name = ?"); person_vals.append(last_name)
            if phone is not None:
                person_sets.append("phone_number = ?"); person_vals.append(phone)
            if email is not None:
                person_sets.append("email = ?"); person_vals.append(email)

            if person_sets:
                sql = f"""
                UPDATE dbo.Person
                SET {", ".join(person_sets)}
                WHERE person_id = ? AND person_type = 'Customer';
                """
                cur.execute(sql, (*person_vals, person_id))

            # Update Customers
            cust_sets, cust_vals = [], []
            if customer_name is not None:
                cust_sets.append("name = ?"); cust_vals.append(customer_name)
            if phone is not None:
                cust_sets.append("phone_number = ?"); cust_vals.append(phone)
            if email is not None:
                cust_sets.append("email = ?"); cust_vals.append(email)
            if address is not None:
                cust_sets.append("address = ?"); cust_vals.append(address)

            if cust_sets:
                sql = f"""
                UPDATE dbo.Customers
                SET {", ".join(cust_sets)}
                WHERE customer_id = ?;
                """
                cur.execute(sql, (*cust_vals, customer_id))

    def update_seller(
        self,
        seller_id: int,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        hire_date=None,
        position: str | None = None,
        salary: float | None = None,
    ) -> None:
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("SELECT person_id FROM dbo.Sellers WHERE seller_id = ?;", (seller_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Seller not found: seller_id={seller_id}")
            person_id = int(row[0])

            # Update Person (guard type for trigger safety)
            person_sets, person_vals = [], []
            if first_name is not None:
                person_sets.append("first_name = ?"); person_vals.append(first_name)
            if last_name is not None:
                person_sets.append("last_name = ?"); person_vals.append(last_name)
            if phone is not None:
                person_sets.append("phone_number = ?"); person_vals.append(phone)
            if email is not None:
                person_sets.append("email = ?"); person_vals.append(email)

            if person_sets:
                sql = f"""
                UPDATE dbo.Person
                SET {", ".join(person_sets)}
                WHERE person_id = ? AND person_type = 'Seller';
                """
                cur.execute(sql, (*person_vals, person_id))

            # Update Sellers (NO is_active column)
            seller_sets, seller_vals = [], []
            if hire_date is not None:
                seller_sets.append("hire_date = ?"); seller_vals.append(hire_date)
            if position is not None:
                seller_sets.append("position = ?"); seller_vals.append(position)
            if salary is not None:
                seller_sets.append("salary = ?"); seller_vals.append(salary)

            if seller_sets:
                sql = f"""
                UPDATE dbo.Sellers
                SET {", ".join(seller_sets)}
                WHERE seller_id = ?;
                """
                cur.execute(sql, (*seller_vals, seller_id))

    # -------------------------
    # DELETE (DESTRUCTIVE)
    # -------------------------

    def delete_customer(self, customer_id: int) -> None:
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("SELECT person_id FROM dbo.Customers WHERE customer_id = ?;", (customer_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Customer not found: customer_id={customer_id}")
            person_id = int(row[0])

            cur.execute("DELETE FROM dbo.Customers WHERE customer_id = ?;", (customer_id,))

            cur.execute("SELECT COUNT(1) FROM dbo.Sellers WHERE person_id = ?;", (person_id,))
            if int(cur.fetchone()[0]) > 0:
                raise ValueError(f"Refusing to delete Person {person_id}: still referenced by Sellers.")

            cur.execute(
                "DELETE FROM dbo.Person WHERE person_id = ? AND person_type = 'Customer';",
                (person_id,),
            )

    def delete_seller(self, seller_id: int) -> None:
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("SELECT person_id FROM dbo.Sellers WHERE seller_id = ?;", (seller_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Seller not found: seller_id={seller_id}")
            person_id = int(row[0])

            cur.execute("DELETE FROM dbo.Sellers WHERE seller_id = ?;", (seller_id,))

            cur.execute("SELECT COUNT(1) FROM dbo.Customers WHERE person_id = ?;", (person_id,))
            if int(cur.fetchone()[0]) > 0:
                raise ValueError(f"Refusing to delete Person {person_id}: still referenced by Customers.")

            cur.execute(
                "DELETE FROM dbo.Person WHERE person_id = ? AND person_type = 'Seller';",
                (person_id,),
            )
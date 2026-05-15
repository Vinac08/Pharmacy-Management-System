from app.db.connection import get_conn


class MedicinesDao:
    def find_all(self) -> list[dict]:
        sql = """
        SELECT TOP 200
            medicine_id,
            name,
            type,
            brand,
            composition,
            price,
            quantity_in_stock,
            expiry_date,
            batch_number,
            reorder_level
        FROM dbo.Medicines
        ORDER BY medicine_id DESC;
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def insert(self, name: str, type_: str, brand: str, composition: str, price: float, quantity_in_stock: int = 0, expiry_date=None, batch_number=None, reorder_level=None) -> int:
        sql = """
        INSERT INTO dbo.Medicines (
            name, type, brand, composition, price, quantity_in_stock, expiry_date, batch_number, reorder_level
        )
        OUTPUT INSERTED.medicine_id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (name, type_, brand, composition, price, quantity_in_stock, expiry_date, batch_number, reorder_level))
            new_id = cur.fetchone()[0]
            return int(new_id)

    def update(self, medicine_id: int, name: str, price: float, quantity_in_stock: int) -> None:
        sql = """
        UPDATE dbo.Medicines
        SET name = ?, price = ?, quantity_in_stock = ?
        WHERE medicine_id = ?;
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (name, price, quantity_in_stock, medicine_id))

    def delete(self, medicine_id: int) -> None:
        sql = "DELETE FROM dbo.Medicines WHERE medicine_id = ?;"
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (medicine_id,))

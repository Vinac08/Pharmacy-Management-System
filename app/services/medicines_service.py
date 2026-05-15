# app/services/medicines_service.py
from app.dao.medicines_dao import MedicinesDao


class MedicinesService:
    def __init__(self):
        self.dao = MedicinesDao()

    def list_medicines(self) -> list[dict]:
        return self.dao.find_all()

    def add_medicine(
        self,
        name: str,
        type_: str,
        brand: str,
        composition: str,
        price: float,
        quantity_in_stock: int = 0,
        expiry_date=None,
        batch_number=None,
        reorder_level=None
    ) -> int:
        name = (name or "").strip()
        type_ = (type_ or "").strip()

        if not name:
            raise ValueError("Medicine name is required.")
        if not type_:
            raise ValueError("Medicine type is required.")
        if price < 0:
            raise ValueError("Price cannot be negative.")
        if quantity_in_stock < 0:
            raise ValueError("Stock quantity cannot be negative.")

        return self.dao.insert(
            name=name,
            type_=type_,
            brand=brand,
            composition=composition,
            price=price,
            quantity_in_stock=quantity_in_stock,
            expiry_date=expiry_date,
            batch_number=batch_number,
            reorder_level=reorder_level
        )

    def update_medicine(self, medicine_id: int, name: str, price: float, quantity_in_stock: int) -> None:
        if medicine_id is None:
            raise ValueError("medicine_id is required.")

        name = (name or "").strip()
        if not name:
            raise ValueError("Medicine name is required.")
        if price < 0:
            raise ValueError("Price cannot be negative.")
        if quantity_in_stock < 0:
            raise ValueError("Stock quantity cannot be negative.")

        self.dao.update(
            medicine_id=medicine_id,
            name=name,
            price=price,
            quantity_in_stock=quantity_in_stock
        )

    def delete_medicine(self, medicine_id: int) -> None:
        if medicine_id is None:
            raise ValueError("medicine_id is required.")
        self.dao.delete(medicine_id)
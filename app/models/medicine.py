from dataclasses import dataclass


@dataclass
class Medicine:
    medicine_id: int | None
    medicine_name: str
    price: float
    stock_quantity: int = 0

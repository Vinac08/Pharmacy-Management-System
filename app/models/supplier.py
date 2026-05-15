from dataclasses import dataclass


@dataclass
class Supplier:
    supplier_id: int | None
    supplier_name: str
    phone: str | None = None
    email: str | None = None

from dataclasses import dataclass


@dataclass
class Customer:
    customer_id: int | None
    # If you use IS-A with Person, you may store person_id here:
    person_id: int | None = None

    # Optional fields (depends on your schema)
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None

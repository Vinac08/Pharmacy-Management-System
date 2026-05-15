# scripts/test_people_crud.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.dao.people_crud_dao import PeopleCrudDao


def main():
    dao = PeopleCrudDao()

    customer_id, customer_person_id = dao.create_customer(
        first_name="Test",
        last_name="Customer",
        phone="000000000",
        email="test.customer@example.com",
        customer_name="Test Customer",
        address="Test Address",
    )
    print("✅ Created customer:", customer_id, "| person:", customer_person_id)

    seller_id, seller_person_id = dao.create_seller(
        first_name="Test",
        last_name="Seller",
        phone="111111111",
        email="test.seller@example.com",
        hire_date=None,
        position="Cashier",
        salary=500.00,
        is_active=True,
    )
    print("✅ Created seller:", seller_id, "| person:", seller_person_id)

    dao.update_customer(customer_id, phone="999999999", address="Updated Address")
    print("✅ Updated customer:", customer_id)

    dao.update_seller(seller_id, position="Senior Cashier", salary=650.00)
    print("✅ Updated seller:", seller_id)

    print("⚠️ Deleting the test records created above...")
    dao.delete_customer(customer_id)
    print("🗑️ Deleted customer:", customer_id)

    dao.delete_seller(seller_id)
    print("🗑️ Deleted seller:", seller_id)

    print("🎉 All CRUD operations completed successfully.")


if __name__ == "__main__":
    main()
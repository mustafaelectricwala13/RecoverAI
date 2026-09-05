from datetime import datetime

from app.database import SessionLocal
from app.models.customer import Customer
from app.models.payment import Payment


demo_data = [
    ("Demo Customer 01", "demo01@recoverai.test", 4999, "BANK_DECLINED", 1),
    ("Demo Customer 02", "demo02@recoverai.test", 1499, "TIMEOUT", 1),
    ("Demo Customer 03", "demo03@recoverai.test", 12500, "BANK_DECLINED", 2),
    ("Demo Customer 04", "demo04@recoverai.test", 799, "TEMPORARY_FAILURE", 1),
    ("Demo Customer 05", "demo05@recoverai.test", 8999, "CARD_EXPIRED", 1),
    ("Demo Customer 06", "demo06@recoverai.test", 3200, "BANK_DECLINED", 3),
    ("Demo Customer 07", "demo07@recoverai.test", 6750, "NETWORK_ERROR", 1),
    ("Demo Customer 08", "demo08@recoverai.test", 2100, "UNKNOWN", 1),
]


db = SessionLocal()

try:
    for name, email, amount, reason, attempt in demo_data:

        existing_customer = (
            db.query(Customer)
            .filter(Customer.email == email)
            .first()
        )

        if existing_customer:
            print(f"Skipping existing customer: {email}")
            continue

        customer = Customer(
            name=name,
            email=email
        )

        db.add(customer)
        db.flush()

        payment = Payment(
            customer_id=customer.id,
            amount=amount,
            status="FAILED",
            failure_reason=reason,
            attempt_count=attempt,
            created_at=datetime.utcnow()
        )

        db.add(payment)

    db.commit()

    print("Demo batch created successfully.")

finally:
    db.close()
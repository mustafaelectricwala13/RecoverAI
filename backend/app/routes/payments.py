from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate


router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


@router.post("/")
def create_payment(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db)
):
    customer = db.get(Customer, payment_data.customer_id)

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    payment = Payment(
        customer_id=payment_data.customer_id,
        amount=payment_data.amount,
        status=payment_data.status,
        failure_reason=payment_data.failure_reason,
        attempt_count=payment_data.attempt_count,
        created_at=datetime.utcnow()
    )

    db.add(payment)

    if payment_data.status.upper() == "FAILED":
        customer.total_failed_payments += 1
    else:
        customer.total_successful_payments += 1
        customer.last_payment_date = payment.created_at

    db.commit()
    db.refresh(payment)

    return payment

@router.get("/")
def get_payments(
    db: Session = Depends(get_db)
):
    payments = db.query(Payment).order_by(
        Payment.id.desc()
    ).all()

    return payments
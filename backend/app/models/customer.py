from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    total_successful_payments: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    total_failed_payments: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    last_payment_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    opted_out: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
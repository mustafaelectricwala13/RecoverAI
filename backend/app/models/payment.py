from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
        index=True
    )

    amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    failure_reason: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=1
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False
    )
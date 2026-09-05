from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecoveryOutcome(Base):
    __tablename__ = "recovery_outcomes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id"),
        nullable=False,
        index=True
    )

    action_id: Mapped[int] = mapped_column(
        ForeignKey("recovery_actions.id"),
        nullable=False,
        index=True
    )

    result: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    amount_recovered: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
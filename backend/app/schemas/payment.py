from datetime import datetime

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    customer_id: int
    amount: float = Field(gt=0)
    status: str
    failure_reason: str | None = None
    attempt_count: int = Field(default=1, ge=1)
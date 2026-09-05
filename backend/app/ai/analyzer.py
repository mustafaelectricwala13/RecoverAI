import os

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field
from typing import Literal

load_dotenv()


class AIRecoveryResult(BaseModel):
    root_cause: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    recommended_action: Literal[
        "RETRY_PAYMENT",
        "REVIEW",
        "ESCALATE",
        "STOP"
    ]
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class AIRecoveryAnalyzer:

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(api_key=api_key)

    def analyze(
        self,
        amount,
        failure_reason,
        attempt_count,
        total_successful_payments,
        total_failed_payments
    ):

        prompt = f"""
You are RecoverAI, an AI-powered revenue recovery analyst.

Analyze this failed payment and recommend the safest recovery intervention.

Payment amount: ₹{amount}
Failure reason: {failure_reason}
Attempt count: {attempt_count}
Previous successful payments: {total_successful_payments}
Previous failed payments: {total_failed_payments}

Your responsibilities:

1. Identify the likely root cause.
2. Assess revenue recovery risk.
3. Recommend ONE recovery action.
4. Explain why the action is appropriate.
5. Provide a confidence score between 0 and 1.

Available actions:

RETRY_PAYMENT
REVIEW
ESCALATE
STOP

IMPORTANT SAFETY RULES:

- You are an advisory AI only.
- Never authorize unlimited retries.
- Never directly execute a payment.
- Do not invent customer information.
- The deterministic RecoverAI policy engine will make the final decision.
- Prefer conservative actions when information is insufficient.
"""

        response = self.client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": AIRecoveryResult,
            },
        )

        return AIRecoveryResult.model_validate_json(response.text)
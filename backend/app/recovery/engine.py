from app.models.payment import Payment
from app.models.customer import Customer


def analyze_payment(payment: Payment, customer: Customer):

    # Safety: only failed payments enter recovery
    if payment.status.upper() != "FAILED":
        return {
            "eligible": False,
            "action": "NO_ACTION",
            "confidence": 1.0,
            "reason": "Payment is not failed."
        }

    # Safety: respect customer opt-out
    if customer.opted_out:
        return {
            "eligible": False,
            "action": "STOP",
            "confidence": 1.0,
            "reason": "Customer has opted out of recovery communication."
        }

    # Safety: don't retry indefinitely
    if payment.attempt_count >= 3:
        return {
            "eligible": False,
            "action": "ESCALATE",
            "confidence": 1.0,
            "reason": "Maximum retry attempts reached."
        }

    failure_reason = (payment.failure_reason or "").upper()

    # Retryable payment failures
    retryable_reasons = {
        "BANK_DECLINED",
        "NETWORK_ERROR",
        "TIMEOUT",
        "TEMPORARY_FAILURE"
    }

    if failure_reason in retryable_reasons:
        return {
            "eligible": True,
            "action": "RETRY_PAYMENT",
            "confidence": 0.90,
            "reason": (
                f"Failure reason '{failure_reason}' is retryable "
                "and retry limit has not been reached."
            )
        }

    # Unknown/non-retryable failures
    return {
        "eligible": True,
        "action": "REVIEW",
        "confidence": 0.70,
        "reason": (
            f"Failure reason '{failure_reason}' requires "
            "additional review before recovery."
        )
    }
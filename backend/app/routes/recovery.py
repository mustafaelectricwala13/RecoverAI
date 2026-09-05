from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.models.payment import Payment
from app.models.recovery_action import RecoveryAction
from app.models.recovery_outcome import RecoveryOutcome
from app.models.audit_log import AuditLog
from app.recovery.engine import analyze_payment
from app.ai.analyzer import AIRecoveryAnalyzer
from datetime import datetime

router = APIRouter(
    prefix="/recovery",
    tags=["Recovery"]
)


@router.post("/analyze/{payment_id}")
def analyze_recovery(
    payment_id: int,
    db: Session = Depends(get_db)
):
    payment = db.get(Payment, payment_id)

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    customer = db.get(Customer, payment.customer_id)

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    decision = analyze_payment(payment, customer)

    return {
        "payment_id": payment.id,
        "customer_id": customer.id,
        "amount": float(payment.amount),
        "failure_reason": payment.failure_reason,
        **decision
    }


@router.post("/execute/{payment_id}")
def execute_recovery(
    payment_id: int,
    db: Session = Depends(get_db)
):
    payment = db.get(Payment, payment_id)

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    customer = db.get(Customer, payment.customer_id)

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    # Always analyze before executing
    decision = analyze_payment(payment, customer)

    # Safety guardrail
    if not decision["eligible"]:
        audit = AuditLog(
            payment_id=payment.id,
            event="RECOVERY_BLOCKED",
            description=decision["reason"]
        )

        db.add(audit)
        db.commit()

        return {
            "payment_id": payment.id,
            "executed": False,
            "action": decision["action"],
            "reason": decision["reason"]
        }

    # Record the recovery decision
    action = RecoveryAction(
        payment_id=payment.id,
        action=decision["action"],
        ai_reason=decision["reason"],
        confidence=decision["confidence"],
        status="EXECUTING"
    )

    db.add(action)
    db.flush()

    # Demo/sandbox execution
    if decision["action"] == "RETRY_PAYMENT":
        result = "SUCCESS"
        amount_recovered = payment.amount

        action.status = "COMPLETED"

        payment.status = "RECOVERED"

        customer.total_successful_payments += 1
        customer.total_failed_payments = max(
            0,
            customer.total_failed_payments - 1
        )

    else:
        result = "NOT_EXECUTED"
        amount_recovered = 0

        action.status = "STOPPED"

    # Record outcome
    outcome = RecoveryOutcome(
        payment_id=payment.id,
        action_id=action.id,
        result=result,
        amount_recovered=amount_recovered
    )

    db.add(outcome)

    # Record audit trail
    audit = AuditLog(
        payment_id=payment.id,
        event="RECOVERY_EXECUTED",
        description=(
            f"Action={decision['action']}; "
            f"Result={result}; "
            f"Amount recovered={float(amount_recovered)}"
        )
    )

    db.add(audit)

    db.commit()
    db.refresh(outcome)

    return {
        "payment_id": payment.id,
        "action": decision["action"],
        "result": result,
        "amount_recovered": float(amount_recovered),
        "confidence": decision["confidence"],
        "audit_logged": True
    }

@router.get("/dashboard")
def recovery_dashboard(
    db: Session = Depends(get_db)
):
    payments = db.query(Payment).all()
    outcomes = db.query(RecoveryOutcome).all()

    # Currently unresolved failed payments
    revenue_at_risk = sum(
        float(payment.amount)
        for payment in payments
        if payment.status == "FAILED"
    )

    # Money successfully recovered
    total_recovered = sum(
        float(outcome.amount_recovered)
        for outcome in outcomes
        if outcome.result == "SUCCESS"
    )

    # Number of successful recovery actions
    successful_recoveries = sum(
        1
        for outcome in outcomes
        if outcome.result == "SUCCESS"
    )

    # Total recovery opportunity = recovered + still unresolved
    total_recovery_opportunity = revenue_at_risk + total_recovered

    # Recovery rate against the original recovery opportunity
    recovery_rate = (
        (total_recovered / total_recovery_opportunity) * 100
        if total_recovery_opportunity > 0
        else 0
    )

    return {
        "payments_analyzed": len(payments),

        "revenue_at_risk": round(revenue_at_risk, 2),

        "revenue_recovered": round(total_recovered, 2),

        "total_recovery_opportunity": round(
            total_recovery_opportunity, 2
        ),

        "successful_recoveries": successful_recoveries,

        "recovery_rate_percent": round(
            recovery_rate, 2
        )
    }

@router.post("/analyze-batch")
def analyze_batch(
    db: Session = Depends(get_db)
):
    payments = (
        db.query(Payment)
        .filter(Payment.status == "FAILED")
        .all()
    )

    results = []

    for payment in payments:

        customer = db.get(Customer, payment.customer_id)

        if not customer:
            continue

        decision = analyze_payment(payment, customer)

        results.append({
            "payment_id": payment.id,
            "customer_id": customer.id,
            "amount": float(payment.amount),
            "failure_reason": payment.failure_reason,
            "eligible": decision["eligible"],
            "action": decision["action"],
            "confidence": decision["confidence"],
            "reason": decision["reason"]
        })

    return {
        "payments_analyzed": len(results),
        "results": results
    }

@router.post("/execute-batch")
def execute_batch(
    db: Session = Depends(get_db)
):
    payments = (
        db.query(Payment)
        .filter(Payment.status == "FAILED")
        .all()
    )

    total_revenue_at_risk = 0.0
    total_recovered = 0.0
    successful_recoveries = 0
    stopped = 0
    escalated = 0

    results = []

    for payment in payments:

        customer = db.get(Customer, payment.customer_id)

        if not customer:
            continue

        total_revenue_at_risk += float(payment.amount)

        decision = analyze_payment(payment, customer)

        # Guardrail blocked the recovery
        if not decision["eligible"]:

            if decision["action"] == "STOP":
                stopped += 1
            elif decision["action"] == "ESCALATE":
                escalated += 1

            audit = AuditLog(
                payment_id=payment.id,
                event="RECOVERY_BLOCKED",
                description=decision["reason"]
            )

            db.add(audit)

            results.append({
                "payment_id": payment.id,
                "action": decision["action"],
                "result": "NOT_EXECUTED",
                "amount_recovered": 0
            })

            continue

        # Create recovery action
        action = RecoveryAction(
            payment_id=payment.id,
            action=decision["action"],
            ai_reason=decision["reason"],
            confidence=decision["confidence"],
            status="EXECUTING"
        )

        db.add(action)
        db.flush()

        # Demo execution
        if decision["action"] == "RETRY_PAYMENT":

            result = "SUCCESS"
            amount_recovered = float(payment.amount)

            action.status = "COMPLETED"
            payment.status = "RECOVERED"

            total_recovered += amount_recovered
            successful_recoveries += 1

            customer.total_successful_payments += 1
            customer.total_failed_payments = max(
                0,
                customer.total_failed_payments - 1
            )

        else:

            result = "NOT_EXECUTED"
            amount_recovered = 0.0

            action.status = "STOPPED"

        # Outcome
        outcome = RecoveryOutcome(
            payment_id=payment.id,
            action_id=action.id,
            result=result,
            amount_recovered=amount_recovered
        )

        db.add(outcome)

        # Audit
        audit = AuditLog(
            payment_id=payment.id,
            event="RECOVERY_EXECUTED",
            description=(
                f"Action={decision['action']}; "
                f"Result={result}; "
                f"Amount recovered={amount_recovered}"
            )
        )

        db.add(audit)

        results.append({
            "payment_id": payment.id,
            "action": decision["action"],
            "result": result,
            "amount_recovered": amount_recovered
        })

    db.commit()

    recovery_rate = (
        (total_recovered / total_revenue_at_risk) * 100
        if total_revenue_at_risk > 0
        else 0
    )

    return {
        "payments_processed": len(results),
        "revenue_at_risk": round(total_revenue_at_risk, 2),
        "revenue_recovered": round(total_recovered, 2),
        "recovery_rate_percent": round(recovery_rate, 2),
        "successful_recoveries": successful_recoveries,
        "stopped": stopped,
        "escalated": escalated,
        "results": results
    }

@router.post("/ai-analyze/{payment_id}")
def ai_analyze_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    payment = db.get(Payment, payment_id)

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    customer = db.get(Customer, payment.customer_id)

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    if payment.status.upper() != "FAILED":
        raise HTTPException(
            status_code=400,
            detail="AI analysis is only available for failed payments"
        )

    analyzer = AIRecoveryAnalyzer()

    result = analyzer.analyze(
        amount=float(payment.amount),
        failure_reason=payment.failure_reason or "UNKNOWN",
        attempt_count=payment.attempt_count,
        total_successful_payments=customer.total_successful_payments,
        total_failed_payments=customer.total_failed_payments
    )

    return {
        "payment_id": payment.id,
        "customer_id": customer.id,
        "amount": float(payment.amount),
        "failure_reason": payment.failure_reason,
        "ai_analysis": result.model_dump()
    }

@router.post("/ai-decide/{payment_id}")
def ai_decide_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    payment = db.get(Payment, payment_id)

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    customer = db.get(Customer, payment.customer_id)

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    # --------------------------------------------------
    # 1. Get deterministic policy decision
    # --------------------------------------------------

    policy_result = analyze_payment(payment, customer)

    # --------------------------------------------------
    # 2. Get AI recommendation
    # --------------------------------------------------

    analyzer = AIRecoveryAnalyzer()

    ai_result = analyzer.analyze(
        amount=float(payment.amount),
        failure_reason=payment.failure_reason or "UNKNOWN",
        attempt_count=payment.attempt_count,
        total_successful_payments=customer.total_successful_payments,
        total_failed_payments=customer.total_failed_payments
    )

    # --------------------------------------------------
    # 3. Compare AI recommendation with policy
    # --------------------------------------------------

    ai_action = ai_result.recommended_action
    policy_action = policy_result["action"]

    if not policy_result["eligible"]:
        final_action = policy_action
        decision = "POLICY_OVERRIDE"
        decision_reason = policy_result["reason"]

    elif ai_action == policy_action:
        final_action = policy_action
        decision = "AI_POLICY_MATCH"
        decision_reason = "AI recommendation matches the deterministic recovery policy."

    else:
        final_action = policy_action
        decision = "POLICY_OVERRIDE"
        decision_reason = (
            f"AI recommended '{ai_action}', "
            f"but policy engine allows '{policy_action}'. "
            "The deterministic policy engine has final authority."
        )

    # --------------------------------------------------
    # 4. Audit the decision
    # --------------------------------------------------

    audit = AuditLog(
        payment_id=payment.id,
        event="AI_DECISION",
        description=(
            f"AI={ai_action}; "
            f"AI_confidence={ai_result.confidence}; "
            f"POLICY={policy_action}; "
            f"FINAL={final_action}; "
            f"DECISION={decision}; "
            f"REASON={decision_reason}"
        )
    )

    db.add(audit)
    db.commit()

    # --------------------------------------------------
    # 5. Return complete decision
    # --------------------------------------------------

    return {
        "payment_id": payment.id,
        "amount": float(payment.amount),
        "failure_reason": payment.failure_reason,

        "ai_analysis": ai_result.model_dump(),

        "policy_decision": {
            "eligible": policy_result["eligible"],
            "action": policy_action,
            "confidence": policy_result["confidence"],
            "reason": policy_result["reason"]
        },

        "final_decision": {
            "action": final_action,
            "decision": decision,
            "reason": decision_reason
        },

        "audit_logged": True
    }

@router.post("/ai-execute/{payment_id}")
def ai_execute_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    payment = db.get(Payment, payment_id)

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    customer = db.get(Customer, payment.customer_id)

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    # 1. Get policy decision
    policy_result = analyze_payment(payment, customer)

    # 2. Stop immediately if policy blocks recovery
    if not policy_result["eligible"]:
        audit = AuditLog(
            payment_id=payment.id,
            event="RECOVERY_BLOCKED",
            description=(
                f"AI execution blocked by policy. "
                f"Final action={policy_result['action']}. "
                f"Reason={policy_result['reason']}"
            )
        )

        db.add(audit)
        db.commit()

        return {
            "payment_id": payment.id,
            "status": "NOT_EXECUTED",
            "final_action": policy_result["action"],
            "reason": policy_result["reason"],
            "audit_logged": True
        }

    # 3. Ask Gemini for recommendation
    analyzer = AIRecoveryAnalyzer()

    ai_result = analyzer.analyze(
        amount=float(payment.amount),
        failure_reason=payment.failure_reason or "UNKNOWN",
        attempt_count=payment.attempt_count,
        total_successful_payments=customer.total_successful_payments,
        total_failed_payments=customer.total_failed_payments
    )

    ai_action = ai_result.recommended_action
    policy_action = policy_result["action"]

    # 4. Policy engine has final authority
    if ai_action == policy_action:
        final_action = policy_action
        decision = "AI_POLICY_MATCH"
    else:
        final_action = policy_action
        decision = "POLICY_OVERRIDE"

    # 5. Execute ONLY the policy-approved retry
    if final_action == "RETRY_PAYMENT":

        payment.status = "RECOVERED"

        customer.total_failed_payments = max(
            0,
            customer.total_failed_payments - 1
        )

        customer.total_successful_payments += 1
        customer.last_payment_date = datetime.utcnow()

        action = RecoveryAction(
            payment_id=payment.id,
            action=final_action,
            ai_reason=ai_result.reason,
            confidence=ai_result.confidence,
            status="COMPLETED"
        )

        db.add(action)
        db.flush()

        outcome = RecoveryOutcome(
            payment_id=payment.id,
            action_id=action.id,
            result="SUCCESS",
            amount_recovered=payment.amount
        )

        audit = AuditLog(
            payment_id=payment.id,
            event="AI_RECOVERY_EXECUTED",
            description=(
                f"AI={ai_action}; "
                f"Policy={policy_action}; "
                f"Final={final_action}; "
                f"Decision={decision}; "
                f"Amount recovered=₹{payment.amount}"
            )
        )

        db.add(outcome)
        db.add(audit)
        db.commit()

        return {
            "payment_id": payment.id,
            "result": "SUCCESS",
            "amount_recovered": float(payment.amount),
            "ai_action": ai_action,
            "policy_action": policy_action,
            "final_action": final_action,
            "decision": decision,
            "audit_logged": True
        }

    # 6. REVIEW / ESCALATE / STOP → never execute automatically
    action = RecoveryAction(
        payment_id=payment.id,
        action=final_action,
        ai_reason=ai_result.reason,
        confidence=ai_result.confidence,
        status="STOPPED"
    )

    db.add(action)
    db.flush()

    outcome = RecoveryOutcome(
        payment_id=payment.id,
        action_id=action.id,
        result="NOT_EXECUTED",
        amount_recovered=0
    )

    audit = AuditLog(
        payment_id=payment.id,
        event="AI_RECOVERY_STOPPED",
        description=(
            f"AI={ai_action}; "
            f"Policy={policy_action}; "
            f"Final={final_action}; "
            f"Decision={decision}. "
            f"Automatic execution not permitted."
        )
    )

    db.add(outcome)
    db.add(audit)
    db.commit()

    return {
        "payment_id": payment.id,
        "result": "NOT_EXECUTED",
        "amount_recovered": 0,
        "ai_action": ai_action,
        "policy_action": policy_action,
        "final_action": final_action,
        "decision": decision,
        "reason": "Automatic execution is not permitted for this action.",
        "audit_logged": True
    }

@router.get("/audit")
def get_audit_logs(
    db: Session = Depends(get_db)
):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    return [
        {
            "id": log.id,
            "payment_id": log.payment_id,
            "event": log.event,
            "description": log.description,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]
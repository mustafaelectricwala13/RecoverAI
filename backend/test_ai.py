from app.ai.analyzer import AIRecoveryAnalyzer

analyzer = AIRecoveryAnalyzer()

result = analyzer.analyze(
    amount=4999,
    failure_reason="BANK_DECLINED",
    attempt_count=1,
    total_successful_payments=5,
    total_failed_payments=1
)

print("\n===== RECOVERAI AI RESULT =====")
print(result.model_dump_json(indent=2))
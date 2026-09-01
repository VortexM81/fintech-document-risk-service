from fintech_docs.risk_policy import PaymentEvent, decide_payment


def test_high_risk_payment_is_held_for_review() -> None:
    decision = decide_payment(
        PaymentEvent(event_id="pay_2026_081", amount_minor=125_00, currency="USD", risk_score=84)
    )

    assert decision.action == "review"
    assert decision.event_id == "pay_2026_081"
    assert "manual-review threshold" in decision.notification

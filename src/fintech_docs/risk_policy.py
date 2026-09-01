from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class PaymentEvent(BaseModel):
    event_id: str
    amount_minor: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    risk_score: int = Field(ge=0, le=100)


class RiskDecision(BaseModel):
    event_id: str
    action: Literal["allow", "review"]
    reason: str
    notification: str
    decided_at: datetime


def decide_payment(event: PaymentEvent) -> RiskDecision:
    if event.risk_score >= 70:
        action = "review"
        reason = "risk score reached the manual-review threshold"
    else:
        action = "allow"
        reason = "risk score remained below the manual-review threshold"
    notification = f"payment {event.event_id}: {action}; {reason}"
    return RiskDecision(
        event_id=event.event_id,
        action=action,
        reason=reason,
        notification=notification,
        decided_at=datetime.now(timezone.utc),
    )

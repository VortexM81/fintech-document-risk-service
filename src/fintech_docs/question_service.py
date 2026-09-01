from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_client import InfraiClient, InfraiError
from .risk_policy import PaymentEvent, RiskDecision, decide_payment


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3)
    collection: str = "fintech-policies"
    top_k: int = Field(default=3, ge=1, le=20)


class Evidence(BaseModel):
    text: str
    document_id: str


class QuestionAnswer(BaseModel):
    answer: str
    evidence: list[Evidence]


app = FastAPI(title="Fintech document risk service")


def _matches(data: dict[str, Any]) -> list[dict[str, Any]]:
    value = data.get("matches", data.get("results", []))
    return value if isinstance(value, list) else []


@app.post("/questions", response_model=QuestionAnswer)
def answer_question(request: QuestionRequest) -> QuestionAnswer:
    client = InfraiClient()
    try:
        embedding = client.embed(request.question)
        found = _matches(client.query(request.collection, embedding, request.top_k * 2))
        evidence = [
            Evidence(
                text=str(item.get("metadata", {}).get("text", "")),
                document_id=str(item.get("metadata", {}).get("document_id", item.get("id", "unknown"))),
            )
            for item in found
            if item.get("metadata", {}).get("text")
        ]
        ranked = client.rerank(request.question, [item.text for item in evidence], request.top_k)
        ordered_text = ranked.get("results", ranked.get("candidates", []))
        if ordered_text and isinstance(ordered_text[0], dict):
            ordered_text = [item.get("text", item.get("candidate", "")) for item in ordered_text]
        by_text = {item.text: item for item in evidence}
        selected = [by_text[text] for text in ordered_text if text in by_text][: request.top_k]
        if not selected:
            selected = evidence[: request.top_k]
        answer = selected[0].text if selected else "No matching policy passage was found."
        return QuestionAnswer(answer=answer, evidence=selected)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": str(exc)}) from exc


@app.post("/payments/decision", response_model=RiskDecision)
def payment_decision(event: PaymentEvent) -> RiskDecision:
    return decide_payment(event)


def run() -> None:
    uvicorn.run("fintech_docs.question_service:app", host="127.0.0.1", port=8000)

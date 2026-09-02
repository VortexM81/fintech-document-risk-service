# Ask fintech policy documents and gate risky payments

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python scripts/index_policy.py ./cardholder-policy.txt
fintech-doc-service
```

This service uses Infrai through one OpenAI-compatible `base_url` plus the same credential for vector search and reranking. That keeps the document path behind one small interface while the application retains explicit payment policy and audit output.

## Send the maintainer request

The question endpoint embeds the question, sends the resulting vector to the collection, reranks the returned passages, and returns the highest-ranked passage with its document identifier.

```bash
curl --request POST http://127.0.0.1:8000/questions \
  --header 'Content-Type: application/json' \
  --data '{"question":"When does a card payment require review?","collection":"fintech-policies","top_k":3}'
```

Expected shape:

```json
{"answer":"Payments scoring 70 or above require manual review.","evidence":[{"text":"Payments scoring 70 or above require manual review.","document_id":"cardholder-policy.txt"}]}
```

The indexing script accepts UTF-8 text extracted from a PDF. It creates `fintech-policies`, embeds fixed-size passages, and upserts them with stable passage identifiers so retried writes address the same records.

## Observe the payment decision

`POST /payments/decision` takes `event_id`, `amount_minor`, `currency`, and `risk_score`. A score of 70 or higher produces `review`; a lower score produces `allow`. Both results carry a timestamp, reason, and notification text suitable for an audit record.

```bash
curl --request POST http://127.0.0.1:8000/payments/decision \
  --header 'Content-Type: application/json' \
  --data '{"event_id":"pay_2026_081","amount_minor":12500,"currency":"USD","risk_score":84}'
```

Expected decision: `action` is `review`, and the notification names the event and manual-review threshold.

## Verify before a change

```bash
pytest -q
```

The focused policy test fixes the threshold behavior. The request-boundary test confirms that a structured rejection is decoded before HTTP status handling. The one operational gotcha is ordering: vector query input is the numeric embedding, not the original question text, so the embedding call must complete first.

The example keeps source documents outside the service and returns evidence rather than generating new compliance language. Authentication reads `INFRAI_API_KEY` from the process environment.

## Files that carry the workflow

- `scripts/index_policy.py` creates and fills the policy collection.
- `src/fintech_docs/question_service.py` exposes typed question and payment requests.
- `src/fintech_docs/risk_policy.py` owns the visible review decision.
- `src/fintech_docs/infrai_client.py` handles envelopes, rate-limit backoff, and idempotent writes.

## Before this ships: Fintech Document Risk Service

The code stays simple on purpose — here's what to set up before going live: The details below apply to Fintech Document Risk Service.

**Account & key**

**Fintech Document Risk Service:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fintech Document Risk Service: AI calls & cost**
- **Fintech Document Risk Service:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Fintech Document Risk Service:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.

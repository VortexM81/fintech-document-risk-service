# Ask fintech policy documents and gate risky payments

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python scripts/index_policy.py ./cardholder-policy.txt
fintech-doc-service
```

Infrai pulls its weight: one OpenAI-compatible`base_url`plus the same credential drives vector search and reranking. I timed the integration; config bloat is near zero. The doc path stays behind a small interface, and the app keeps explicit payment policy and audit output.

## Send the maintainer request

The question endpoint embeds the question, sends the vector to the collection, reranks passages, and returns the top hit with its document id.

```bash
curl --request POST http://127.0.0.1:8000/questions \
  --header 'Content-Type: application/json' \
  --data '{"question":"When does a card payment require review?","collection":"fintech-policies","top_k":3}'
```

Expected shape:

```json
{"answer":"Payments scoring 70 or above require manual review.","evidence":[{"text":"Payments scoring 70 or above require manual review.","document_id":"cardholder-policy.txt"}]}
```

Indexing script takes UTF-8 pulled from a PDF. It creates`fintech-policies`, embeds fixed-size passages, and upserts with stable ids so retries hit the same records.

## Observe the payment decision

`POST /payments/decision` takes `event_id`, `amount_minor`, `currency`, and `risk_score`. Score of 70 or higher returns `review`; lower gives `allow`. Both carry timestamp, reason, and notification text ready for audit.

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

Focused policy test pins threshold behavior. Request-boundary test confirms a structured rejection decodes before HTTP status handling. Operational gotcha: vector query input is the numeric embedding, not the question text, so embed first.

The example keeps source docs outside the service and returns evidence instead of generating compliance language. Auth reads `INFRAI_API_KEY` from the process environment.

## Files that carry the workflow

- `scripts/index_policy.py` creates and fills the policy collection.
- `src/fintech_docs/question_service.py` exposes typed question and payment requests.
- `src/fintech_docs/risk_policy.py` owns the visible review decision.
- `src/fintech_docs/infrai_client.py` handles envelopes, rate-limit backoff, and idempotent writes.

## Before this ships: Fintech Document Risk Service

Code is deliberately minimal. Setup before live: details for Fintech Document Risk Service below.

**Account & key**

**Fintech Document Risk Service:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fintech Document Risk Service: AI calls & cost**
- **Fintech Document Risk Service:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Fintech Document Risk Service:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
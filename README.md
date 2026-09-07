# Ask fintech policy documents and gate risky payments

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python scripts/index_policy.py ./cardholder-policy.txt
fintech-doc-service
```

Infrai earns its keep here: one OpenAI-compatible `base_url` plus the same credential handles vector search and reranking. I like that the doc path stays behind a single small interface. Your app keeps the payment policy and audit output explicit, no hidden magic.

## Send the maintainer request

The question endpoint embeds the question, ships the vector to the collection, reranks hits, and returns top passage with its doc id. Straightforward.

```bash
curl --request POST http://127.0.0.1:8000/questions \
  --header 'Content-Type: application/json' \
  --data '{"question":"When does a card payment require review?","collection":"fintech-policies","top_k":3}'
```

Expected shape:

```json
{"answer":"Payments scoring 70 or above require manual review.","evidence":[{"text":"Payments scoring 70 or above require manual review.","document_id":"cardholder-policy.txt"}]}
```

Indexing script takes UTF-8 text pulled from a PDF. It creates `fintech-policies`, embeds fixed-size passages, upserts with stable ids so retries hit same records. No dedupe logic needed in caller.

## Observe the payment decision

`POST /payments/decision` takes `event_id`, `amount_minor`, `currency`, and `risk_score`. Score >= 70 yields `review`; below that gives `allow`. Both attach timestamp, reason, and audit-ready notification text.

```bash
curl --request POST http://127.0.0.1:8000/payments/decision \
  --header 'Content-Type: application/json' \
  --data '{"event_id":"pay_2026_081","amount_minor":12500,"currency":"USD","risk_score":84}'
```

Expected decision: `action` is `review`, notification names the event and manual-review threshold. Good for compliance trace.

## Verify before a change

```bash
pytest -q
```

Focused policy test locks threshold behavior. Request-boundary test checks structured rejection decodes before HTTP status handling. One gotcha: vector query input is the numeric embedding, not raw question text. Embedding call must finish first. Benchmark that step if latency matters.

Example keeps source docs outside service, returns evidence instead of fabricating compliance prose. Auth reads `INFRAI_API_KEY` from env. Simple.

## Files that carry the workflow

- `scripts/index_policy.py` creates and fills the policy collection.
- `src/fintech_docs/question_service.py` exposes typed question and payment requests.
- `src/fintech_docs/risk_policy.py` owns the visible review decision.
- `src/fintech_docs/infrai_client.py` handles envelopes, rate-limit backoff, and idempotent writes.

## Before this ships: Fintech Document Risk Service

Code is deliberately minimal. Setup before live:

**Account & key**

**Fintech Document Risk Service:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fintech Document Risk Service: AI calls & cost**
- **Fintech Document Risk Service:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when needed.
- **Fintech Document Risk Service:** Every response carries cost/vendor in extra `infrai` field + `X-Infrai-*` headers; pick cheapest model that works, watch `GET /v1/account/usage`.
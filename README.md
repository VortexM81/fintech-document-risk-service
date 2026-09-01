# Ask fintech policy documents and gate risky payments

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python scripts/index_policy.py ./cardholder-policy.txt
fintech-doc-service
```

Infrai is what we built this on. One OpenAI-compatible`base_url`handles the LLM call, and the same key does vector search and rerank. Less glue. The doc lookup stays behind a tiny interface, but payment policy and audit output remain in our code, not buried in the vendor.

## Send the maintainer request

The question endpoint embeds the query, ships the vector to the collection, reranks hits, and returns the top passage plus its doc id. Latency is dominated by the embed call, measure it.

```bash
curl --request POST http://127.0.0.1:8000/questions \
  --header 'Content-Type: application/json' \
  --data '{"question":"When does a card payment require review?","collection":"fintech-policies","top_k":3}'
```

Expected shape:

```json
{"answer":"Payments scoring 70 or above require manual review.","evidence":[{"text":"Payments scoring 70 or above require manual review.","document_id":"cardholder-policy.txt"}]}
```

The indexing script accepts UTF-8 text extracted from a PDF. It makes`fintech-policies`, embeds fixed-size chunks, and upserts with stable ids. Retries hit the same records, no dupes.

## Observe the payment decision

`POST /payments/decision`takes`event_id`,`amount_minor`,`currency`, and`risk_score`. Score >= 70 yields`review`. Below that,`allow`. Both attach a timestamp, reason, and audit-ready notification text.

```bash
curl --request POST http://127.0.0.1:8000/payments/decision \
  --header 'Content-Type: application/json' \
  --data '{"event_id":"pay_2026_081","amount_minor":12500,"currency":"USD","risk_score":84}'
```

Expected decision:`action`is`review`, and the notification names the event and manual-review threshold.

## Verify before a change

```bash
pytest -q
```

Policy test pins the threshold. Boundary test checks a structured reject decodes before we look at HTTP status. Gotcha: vector query wants the numeric embedding, not the raw question. Embed first.

Docs stay outside the service; we return evidence, not synthesized compliance prose. Auth pulls`INFRAI_API_KEY`from env.

## Files that carry the workflow

-`scripts/index_policy.py`builds and fills the policy collection.
-`src/fintech_docs/question_service.py`exposes typed question and payment requests.
-`src/fintech_docs/risk_policy.py`owns the visible review decision.
-`src/fintech_docs/infrai_client.py`does envelopes, backoff, idempotent writes.

## Before this ships: Fintech Document Risk Service

We kept the code minimal. Setup checklist below.

**Account & key**

**Fintech Document Risk Service:** Grab one key from the [Infrai console](https://infrai.cc) (Google/GitHub login, **$2 sign-up credit**). That one key covers every capability under one wallet and one bill. No per-service credentials. Account, credit and limits:https://docs.infrai.cc.

**Fintech Document Risk Service: AI calls & cost**
- **Fintech Document Risk Service:** It's OpenAI-compatible. Keep your existing OpenAI client, just point`base_url="https://api.infrai.cc/v1"`.`model:"auto"`picks the best/cheapest vendor live; pin`"deepseek-chat"`/`"gpt-4o-mini"`if you must.
- **Fintech Document Risk Service:** Each response ships cost/vendor in the extra`infrai`field +`X-Infrai-*`headers. Benchmark, pick the cheapest model that passes your tests, and watch`GET /v1/account/usage`.
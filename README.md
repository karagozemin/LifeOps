# 🛡️ LifeOps

**Paste your document, save your money.** Deadline + `money_at_risk` + `.ics` in a single call.
An agent-consumable ASP (Agentic Service Provider). Paid over **A2MCP on X Layer (USDT0)**.

> OKX.AI Genesis Hackathon — Lifestyle Companion category.

---

## Why it's different

ChatGPT does not give you a callable API + a **guaranteed JSON schema** + `.ics` output + a `money_at_risk` field. LifeOps does. The core is not x402 — the core is the **document → money-saving action** transformation.

---

## Architecture

```
frontend/               Next.js 14 (App Router) + TypeScript + Tailwind
  app/page.tsx          split-screen UI: paste -> result | live x402 tx log
  components/           ResultView (money-at-risk cards) + TxTerminal
  lib/                  api client (x402 flow), types, samples

backend/app/
  schema.py             guaranteed Pydantic schema (NO free text)
  extract.py            LLM (if available) + deterministic regex fallback
  money.py              money_at_risk rule engine
  ics.py                pure-Python .ics generator (zero deps)
  payment.py            x402 payment gate + tx log
  pipeline.py           extract -> normalize -> money -> .ics -> schema
  main.py               FastAPI endpoints
```

**Critical design:** with no `OPENAI_API_KEY`, the system falls back to a deterministic path and still produces a **guaranteed schema + valid .ics**. The demo works even offline / without a key.

---

## Run

### 1) Backend
```bash
cd backend
bash run.sh        # venv + deps + uvicorn (localhost:8000)
```
Optional LLM: `export OPENAI_API_KEY=sk-...`

### 2) Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

### 3) Verify (serverless smoke test)
```bash
cd backend && source .venv/bin/activate && python test_smoke.py
```
Proves all 6 scenarios (5 single-document + 1 multi_audit bundle) produce a
guaranteed schema + valid `.ics` (no LLM).

### 4) Agent-to-agent demo (Use Case 6 — A2MCP proof)
```bash
# with the backend running:
cd backend && source .venv/bin/activate && python agent_call_demo.py
```
Shows a TravelPlanner agent calling LifeOps over x402: 402 → payment → JSON.

---

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Service catalog + network info |
| GET | `/health` | Readiness probe (`ready_for_listing` = payTo wallet configured) |
| GET | `/pricing` | Prices (USDT0) + A2MCP payment requirements per service |
| POST | `/scan` | Document analysis (x402: needs `X-Payment` header; demo: `demo`) |
| GET | `/tx` | Live tx log |
| GET | `/ics/{result_id}.ics` | Calendar file of a specific result (concurrency-safe) |
| GET | `/ics/latest.ics` | Calendar file of the latest result (demo convenience) |

`/scan` body: `{ "text": "...", "service": "full_action_pack", "caller": "human" }`
`/scan` response includes `result_id` and a per-result `ics_url` so concurrent
callers never collide on the calendar download.

**multi_audit:** send several documents in one `text` payload, separated by
`---` lines (or blank lines). The response merges every obligation into one
audit — sorted by urgency, `total_money_at_risk_usd` aggregated, and a single
combined `.ics` covering all deadlines. `documents_scanned` reports how many
documents were parsed.

---

## Services

| Service | Price | Contents |
|---|---|---|
| Life Document Scan | 0.01 USDT0 | Type + deadline + entities |
| Full Action Pack | 0.05 USDT0 | + .ics + reminders + action plan |
| Multi-Document Life Audit | 0.20 USDT0 | Multiple documents + merged calendar + total risk |

---

## Payment (A2MCP / X Layer)

Per the OKX A2MCP spec, an unpaid call to a paid service returns **HTTP 402**
with a `PAYMENT-REQUIRED` header carrying base64(JSON) requirements:

```json
{
  "scheme": "exact",
  "network": "eip155:196",
  "asset": "0x779ded0c9e1022225f8e0630b35a9b54be713736",
  "amount": "10000",
  "payTo": "<X Layer wallet — set via LIFEOPS_PAYTO env>"
}
```

- Network: **X Layer mainnet** (`eip155:196`)
- Asset: **USDT0** (6 decimals — `"10000"` = 0.01 USDT0)
- Receiving wallet: set `LIFEOPS_PAYTO=0x...` before starting the backend
  (the server logs a loud warning and `/health` reports `ready_for_listing: false` if you forget).
- Demo flow: `X-Payment: demo` triggers a clearly-labeled `demo-settlement`
  so the UI stays live and repeatable; real settlement runs on OKX.AI rails.

---

## Deploy + OKX.AI listing

- `backend/Dockerfile` — production image for Render / Railway / Fly / any Docker host
  (start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, env: `LIFEOPS_PAYTO`).
- **`LISTING.md`** — the complete copy-paste kit for the OKX.AI ASP registration
  (Onchain OS commands, ASP/service descriptions, prices in base units, endpoint
  requirements, review flow, hackathon submission checklist).

---

## 90-second demo flow

1. Click the Passport (agent) sample → right panel streams the x402 402 → settle flow.
2. Left: result card + `money_at_risk` + steps.
3. Download the `.ics` → drops into the calendar.
4. Multi-audit sample (3 docs, 0.20 USDT0) → one merged audit, obligations sorted by urgency, single combined `.ics`.
5. Warranty sample → "39 days left" URGENT card → close.

No mocks in the result, no time-skipping. Everything is live and repeatable.

# 🛡️ LifeOps

**Paste your document, save your money.** Deadline + `money_at_risk` + `.ics` in a single call.
An agent-consumable ASP (Agentic Service Provider). Paid over x402 / A2MCP.

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
Proves all 5 scenarios produce a guaranteed schema + valid `.ics` (no LLM).

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
| GET | `/` | Health + service catalog |
| GET | `/pricing` | Prices (USDT) |
| POST | `/scan` | Document analysis (x402: needs `X-Payment` header; demo: `demo`) |
| GET | `/tx` | Live tx log |
| GET | `/ics/latest.ics` | Calendar file of the latest result |

`/scan` body: `{ "text": "...", "service": "full_action_pack", "caller": "human" }`

---

## Services

| Service | Price | Contents |
|---|---|---|
| Life Document Scan | 0.01 USDT | Type + deadline + entities |
| Full Action Pack | 0.05 USDT | + .ics + reminders + action plan |
| Multi-Document Life Audit | 0.20 USDT | Multiple documents + merged calendar + total risk |

---

## 90-second demo flow

1. Click the Passport (agent) sample → right panel streams the x402 402 → settle flow.
2. Left: result card + `money_at_risk` + steps.
3. Download the `.ics` → drops into the calendar.
4. Warranty sample → "39 days left" URGENT card → close.

No mocks in the result, no time-skipping. Everything is live and repeatable.

# OKX.AI ASP Listing — Vekil LifeOps (copy-paste kit)

Everything the Onchain OS registration flow will ask, ready to paste.
Deadline: **27 July 2026, 23:59 UTC** (HackQuest). Listing must be LIVE before submission counts.

---

## 0) Prerequisites checklist

- [ ] Backend deployed to a **public HTTPS** URL (see DEPLOY section below)
- [ ] `LIFEOPS_PAYTO=0x...` set to YOUR X Layer wallet before starting the backend
- [ ] `curl -i -X POST https://<domain>/scan -H "Content-Type: application/json" -d '{"text":"test"}'` returns **HTTP 402 + PAYMENT-REQUIRED header**
- [ ] Onchain OS skills installed: `npx skills add okx/onchainos-skills --yes -g` (then open a NEW Claude Code session)
- [ ] Logged in: `Log in to Agentic Wallet on Onchain OS with my email`

## 1) Registration command (paste into Claude Code)

```text
Help me register an A2MCP ASP on OKX.AI using OKX Agent Identity from Onchain OS
```

## 2) ASP-level answers

| Field | Value |
|---|---|
| ASP name | `Vekil LifeOps` |
| ASP description | `Life-admin autopilot for agents and humans. Paste any life document (passport, warranty, bill, subscription email) and get back guaranteed JSON: deadline, money_at_risk_usd, step-by-step action plan and a downloadable .ics calendar file — in a single paid call.` |
| Receiving wallet | `<YOUR X LAYER WALLET — same as LIFEOPS_PAYTO>` |
| Network | X Layer mainnet (`eip155:196`) |
| Settlement asset | USDT0 — `0x779ded0c9e1022225f8e0630b35a9b54be713736` (6 decimals) |

## 3) Services (three under one ASP)

### Service 1 — Life Document Scan
- **Description:** `Classifies a life document and extracts the critical deadline, entities and money at risk. Returns guaranteed JSON (no free text).`
- **Endpoint:** `https://<domain>/scan`
- **Method:** POST
- **Price:** 0.01 USDT0 → amount `"10000"`
- **Input parameters:**
  - `text` (string, required) — raw document/message text
  - `service` (string) — must be `"scan"`
  - `caller` (string, optional) — calling agent identity
- **Output:** `{ payment, result: { document_type, entities, obligations[], reminders[], total_money_at_risk_usd, confidence }, result_id }`

### Service 2 — Full Action Pack
- **Description:** `Everything in Scan plus a step-by-step action plan, reminder dates and a downloadable .ics calendar file covering the deadline.`
- **Endpoint:** `https://<domain>/scan`
- **Method:** POST
- **Price:** 0.05 USDT0 → amount `"50000"`
- **Input parameters:** same as Service 1, `service` = `"full_action_pack"`
- **Output:** Scan output + `ics_base64` + `ics_url` (per-result `.ics` download)

### Service 3 — Multi-Document Life Audit
- **Description:** `Send several documents in one payload (separated by --- lines). Returns ONE merged audit: obligations sorted by urgency, aggregated total_money_at_risk_usd and a single combined .ics covering every deadline.`
- **Endpoint:** `https://<domain>/scan`
- **Method:** POST
- **Price:** 0.20 USDT0 → amount `"200000"`
- **Input parameters:** same, `service` = `"multi_audit"`, `text` = documents joined with `\n---\n`
- **Output:** merged audit + `documents_scanned` + combined `.ics`

## 4) Payment behaviour (A2MCP compliance — already implemented)

- Unpaid POST → **HTTP 402** with `PAYMENT-REQUIRED: base64({scheme:"exact", network:"eip155:196", asset:"0x779d…3736", amount:"<base units>", payTo:"<wallet>"})`
- Paid POST → HTTP 200, guaranteed JSON.

## 5) Submit to marketplace review (paste into Claude Code)

```text
Help me list my ASP on OKX.AI using Onchain OS
```

Save the returned **Agent ID / ASP ID**. Review ≈ 24h / 1 business day; result lands in the Agentic Wallet email + Claude session. If rejected → fix per feedback → resubmit.

## 6) After approval — hackathon submission

1. Confirm the listing is LIVE on OKX.AI.
2. Record ≤90s demo (flow already scripted in README).
3. Post on X with `#OKXAI`.
4. Fill the Google Form (HackQuest Start Submit) with ASP details + X post link.

---

## DEPLOY (fastest paths to public HTTPS)

**Option A — Render/Railway/Fly (recommended, stable URL):**
- Root: `backend/`, start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env vars: `LIFEOPS_PAYTO=0x...` (and optionally `OPENAI_API_KEY`)

**Option B — quick tunnel for review (fine for 24h review window):**
```bash
cd backend && LIFEOPS_PAYTO=0x... bash run.sh
# in another terminal:
npx cloudflared tunnel --url http://localhost:8000
```
Use the printed `https://*.trycloudflare.com` URL as the endpoint.
⚠️ Tunnel URLs die when the process stops — keep it alive through review, or prefer Option A.

**Verify before registering:**
```bash
curl -i -X POST https://<domain>/scan \
  -H "Content-Type: application/json" \
  -d '{"text":"Passport expiry 2026-11-05","service":"scan"}'
# expect: HTTP/2 402 + PAYMENT-REQUIRED header
```

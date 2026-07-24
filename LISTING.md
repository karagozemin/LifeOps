# OKX.AI ASP Listing Kit

Deadline: 27 July 2026, 23:59 UTC. The listing must be live before the HackQuest submission.

## Readiness gate

- [ ] Public HTTPS API is stable.
- [ ] `GET /health` returns `ready_for_listing: true`.
- [ ] `LIFEOPS_DEMO_MODE=false` in production.
- [ ] Unpaid `POST /scan` returns 402 plus a standard `PAYMENT-REQUIRED` header.
- [ ] A funded Agentic Wallet completes one real 0.01 USDT0 call.
- [ ] The real `PAYMENT-RESPONSE` decodes to an X Layer transaction hash.
- [ ] The tx hash is recorded in `SUBMISSION.md`.

## ASP identity

| Field | Value |
|---|---|
| Name | `LifeOps` |
| Role | `ASP` |
| Category | `Lifestyle Companion` |
| Description | `Personal deadline intelligence for agents and humans. LifeOps turns passports, warranties, subscriptions, bills, and appointments into guaranteed JSON with source evidence, conservative money-at-risk calculations, action steps, reminders, and downloadable calendar files.` |
| Network | X Layer mainnet (`eip155:196`) |
| Asset | USDT0 (`0x779ded0c9e1022225f8e0630b35a9b54be713736`, 6 decimals) |
| Receiving wallet | `<LIFEOPS_PAYTO>` |
| Repository | `https://github.com/karagozemin/LifeOps` |
| Web app | `<PUBLIC_WEB_URL>` |

## Services

### Life Document Scan

| Field | Value |
|---|---|
| Type | `A2MCP` |
| Endpoint | `<PUBLIC_API_URL>/scan` |
| Method | `POST` |
| Fee | `0.01 USDT0` |
| Description | `Classifies a personal-life document and returns a deadline, entities, source evidence, status, and explainable money at risk in guaranteed JSON.` |
| Input | `text` required string; `service` = `scan`; `caller` optional string |

### Full Action Pack

| Field | Value |
|---|---|
| Type | `A2MCP` |
| Endpoint | `<PUBLIC_API_URL>/scan` |
| Method | `POST` |
| Fee | `0.05 USDT0` |
| Description | `Adds action steps, future reminders, risk basis, and a TTL-bound .ics calendar to the evidence-backed document analysis.` |
| Input | `text` required string; `service` = `full_action_pack`; `caller` optional string |

### Multi-Document Life Audit

| Field | Value |
|---|---|
| Type | `A2MCP` |
| Endpoint | `<PUBLIC_API_URL>/scan` |
| Method | `POST` |
| Fee | `0.20 USDT0` |
| Description | `Audits multiple personal documents, deduplicates risk, sorts obligations by urgency, and returns one combined calendar and total money at risk.` |
| Input | Documents joined with `\n---\n`; `service` = `multi_audit` |

## Production variables

```text
LIFEOPS_PAYTO=<X_LAYER_WALLET>
OKX_API_KEY=<secret>
OKX_SECRET_KEY=<secret>
OKX_PASSPHRASE=<secret>
UPSTASH_REDIS_REST_URL=<secret>
UPSTASH_REDIS_REST_TOKEN=<secret>
LIFEOPS_DEMO_MODE=false
LIFEOPS_CORS_ORIGINS=<PUBLIC_WEB_URL>
```

## Verification commands

```bash
curl -i -X POST <PUBLIC_API_URL>/scan \
  -H 'Content-Type: application/json' \
  -d '{"text":"Warranty ends 2027-09-01. Value 120 USD.","service":"scan"}'

curl <PUBLIC_API_URL>/health

LIFEOPS_API_BASE=<PUBLIC_API_URL> python backend/agent_call_demo.py
```

Expected: the first command returns 402; health is listing-ready; the demo asks for explicit payment confirmation and then prints a real receipt and merchant result.

## Review handoff

After all fields are final, create one ASP identity, add all three services, explicitly finish service collection, review the confirmation card, and only then confirm the on-chain registration. Record the returned ASP ID immediately in `SUBMISSION.md`.

# Vekil LifeOps — Product Requirements Document (PRD)

> **Version:** 1.0
> **Date:** 2026-07-21
> **Owner:** Emin Karagöz
> **Goal:** OKX.AI Genesis Hackathon — Guaranteed prize in the Lifestyle Companion category (top 3 slots, 3 × $2,500) + parallel Social Buzz ($1,000)
> **Status:** Scope-locked. The orchestrator / autonomous-spending idea is REJECTED.

---

## 0. Executive Summary (TL;DR)

Vekil LifeOps takes a document/message/screenshot sent by a person (or another agent) and, **in a single call**:
- extracts deadlines and obligations,
- computes the money that will be lost if missed (`money_at_risk`),
- returns a structured JSON + `.ics` calendar file + a set of reminders.

It is a **flat-per-call priced, agent-consumable ASP (Agentic Service Provider)** service.

The heart of the product is NOT x402; the heart is the **guaranteed structured output + a real-life, money-saving action plan**. x402 is present naturally, simply as a requirement of being a "paid service."

---

## 1. Problem Statement

People miss critical deadlines in their lives, and this directly costs **money**:
- Driver's license/passport/visa expires → fines, canceled travel.
- Warranty lapses → cost of a new device.
- Free trial converts to a paid subscription → unwanted charge.
- A bill is late → late-payment interest + service cutoff.
- Inspection/appointment missed → penalty + rescheduling.

Existing solutions (calendar apps, reminders) require **manual entry** and **do not monetize the risk**. General tools like ChatGPT do not provide a callable API, a guaranteed schema, an `.ics` output, or a `money_at_risk` field.

---

## 2. Solution

**Vekil LifeOps** = a single-call service that automates the document → action transformation.

Input: text / JSON payload / image.
Output: guaranteed JSON schema + `.ics` + risk summary.

**Critical distinction (prevents drifting into Utility):** The scope is only **personal-life** documents (driver's license, passport, visa, warranty, subscription, bill, inspection/appointment). Corporate/financial/technical documents are OUT of scope.

---

## 3. Target Users

| Persona | Need | How they use it |
|---|---|---|
| Individual end user | "What happens if I miss this document?" | Pastes the document into the frontend |
| Other AI agents | Obligation analysis on behalf of the user | Calls the Vekil endpoint via A2MCP (x402-paid) |
| Travel/assistant agents | Passport/visa validity check | Integrates it as a plug-in |

---

## 4. Category & Positioning

- **Primary category:** Lifestyle Companion (3 slots × $2,500 USDT, equal distribution).
- **Parallel:** Social Buzz ($1,000) — by sharing the build process on X.
- **Rationale:** The Finance category is extremely crowded; Utility/Art fill up on the last day. Lifestyle is the lowest-variance, most defensible area.
- **Framing:** "Life assistant" — the personal-life scope lock prevents the Utility perception.

---

## 5. Functional Requirements

### 5.1 Service Packages (Pricing)

| Service | Description | Price |
|---|---|---|
| Life Document Scan | Single document → deadline + type + basic entity extraction | 0.01 USDT |
| Full Action Pack | JSON + `.ics` + reminder set + step-by-step plan | 0.05 USDT |
| Multi-Document Life Audit | Multiple documents → unified calendar + total risk | 0.20 USDT |

### 5.2 Input Channels

1. **Text / JSON payload** — the primary channel (the demo uses this, zero OCR risk).
2. **Image** — optional, via a vision model (kept on the list, not used in the demo).

### 5.3 Core Processing

- The LLM layer is called with **JSON-schema enforcement** (free text FORBIDDEN — guaranteed schema).
- `money_at_risk` computation logic is rule-based per document type + LLM estimate.
- `.ics` generation is pure Python (minimal dependencies).
- A `confidence` score in every output.

### 5.4 Payment Layer

- An **x402 payment-required** header in front of the endpoint.
- Call in the **A2MCP standard**.
- Payment confirmation (tx hash) is written to a live log.
- x402 = a service requirement, not the heart, not decoration.

### 5.5 OKX.AI Listing

- Vekil is listed as a **single ASP**.
- The counterparty (the agent-call scenario) is NOT a separate ASP on OKX; it is a lightweight independent endpoint.
- This reduces review risk to a single point.

---

## 6. Guaranteed JSON Output Schema

```json
{
  "document_type": "drivers_license",
  "entities": { "expiry_date": "2027-03-14", "holder": "..." },
  "obligations": [
    {
      "title": "Driver's license renewal",
      "due_date": "2027-03-14",
      "start_action_by": "2027-01-28",
      "risk_if_missed": "Fine for driving with an invalid license + inability to drive",
      "money_at_risk_usd": 150,
      "steps": ["...", "..."]
    }
  ],
  "reminders": ["2027-01-28", "2027-02-28", "2027-03-12"],
  "ics_base64": "…",
  "confidence": 0.93
}
```

This schema is the true value of the product. ChatGPT does not provide a callable API + a guaranteed `.ics` + a `money_at_risk` field.

---

## 7. Frontend Requirements

**Role:** Not the product — the **credibility layer**. It turns abstract API value into visible proof.

**Stack:** Next.js + Tailwind (default). Single page, fast, split-screen friendly. A 1-day job — it must not steal time from the backend.

**The 3 must-have visual elements:**
1. A document/message paste area (drag-drop + text box).
2. Result cards — each obligation is a card: title, due date, a red **"money at risk" badge**, steps.
3. A **live Tx Log terminal** at the bottom right (proof that the x402 payment really flows).

---

## 8. Use Cases

### 🅰️ Demo money-shot use cases

1. **Driver's license / Passport / Visa expiry** — "Expires on March 14, 2027, start 45 days early, 3 reminders + document list." Risk: fine + canceled travel.
2. **Warranty document** — "Headphone warranty expires in 39 days, file the service request now." Risk: cost of a new device.

### 🅱️ Strong marketplace use cases

3. **Subscription / free-trial end** — "The trial converts to $19.99 in 3 days, cancel link + deadline." The clearest money-saving story.
4. **Bill due date** — "The electricity bill, if late on July 22, incurs a 5% penalty + cutoff."
5. **Inspection / vehicle inspection / appointment** — calendar + prep list + late penalty.

### 🅲️ Agent-economy use case (A2MCP proof)

6. **Another agent calls Vekil as a plug-in** — e.g., a travel agent sends a passport photo → Vekil returns JSON saying "passport valid for 4 months, some countries require 6, risky." A real, outward-facing service. The most valuable use case — proof of agent-to-agent infrastructure.

---

## 9. The 90-Second Demo Scenario

Split-screen — app on the left, live Tx Log terminal at the bottom right.

| Time | Action |
|---|---|
| 0-15s | An agent sends Vekil an insurance policy text (payload flows, not an image) |
| 15-30s | The x402 payment header + tx confirmation scrolls live in the right terminal (proof it's not mocked) |
| 30-60s | Deadlines, `money_at_risk`, and a step-by-step plan appear on the left screen |
| 60-75s | The `.ics` is downloaded and drops into the calendar (visual proof) |
| 75-90s | Second document (warranty) → "expires in 39 days, file the request now" → closing |

NO time-skipping / proactivity simulation. Everything is live and reproducible.

---

## 10. Technical Architecture

- **Backend:** FastAPI, single service, single repo.
- **LLM:** structured output with JSON-schema/function-calling enforcement.
- **`.ics`:** pure Python generator.
- **Payment:** x402 payment layer, A2MCP standard.
- **Frontend:** Next.js + Tailwind, single page.
- **Image channel:** optional vision model (not used in the demo).

```
[User / Agent]
        │  (text | JSON | image)
        ▼
[x402 Payment Gate] ──► tx log
        │
        ▼
[FastAPI Endpoint]
        │
        ├─► [LLM + JSON-schema enforcement]
        ├─► [money_at_risk rule engine]
        └─► [.ics generator]
        │
        ▼
[Guaranteed JSON + .ics_base64]
        │
        ▼
[Frontend: result cards + Tx Log]
```

---

## 11. 6-Day Roadmap

### Day 1 — Skeleton
- FastAPI setup, single endpoint, JSON-schema-enforced LLM call.
- 2 document types (driver's license + warranty).
- Evening: an end-to-end response returns via a text payload.

### Day 2 — Core + LISTING (critical threshold)
- `.ics` generation + `money_at_risk` + reminders.
- The x402 payment layer is attached to the endpoint.
- **NON-NEGOTIABLE: submit the OKX.AI listing application.** (Review ~24h in parallel; latecomers get eliminated.)

### Day 3 — Hardening
- 3rd service (Multi-Document Audit).
- 5+ document types, error handling, confidence score.
- Image/OCR channel added optionally (not used in the demo).

### Day 4 — Polish + real calls
- Marketplace description, pricing, sample inputs.
- Generate a few real orders with test calls (order/review criterion).
- Follow up on listing approval.

### Day 5 — Demo video
- 90s scenario, split-screen + live tx log.
- Shoot twice, edit the clean take.

### Day 6 — Submission + Social Buzz
- Final submission form, repo cleanup, README.
- Social Buzz: share the build process as a thread on X, post the demo clip.

---

## 12. Risk Register

| Risk | Mitigation |
|---|---|
| Getting stuck in listing review | Submit at end of Day 2, single ASP, clean description |
| OCR blowing up in the demo | Demo with a text payload, image optional |
| The "ChatGPT is free" objection | Guaranteed JSON + .ics + callable API + money_at_risk |
| Perception of drifting into Utility | Scope is personal-life only, "life assistant" framing |
| Solo time pressure | Scope locked, even 2 document types are a sufficient MVP |
| Perception of x402 bloat | Position x402 as a service requirement, not the heart |

---

## 13. Success Metrics

- ✅ An approved, callable single ASP on OKX.AI.
- ✅ At least a few real orders + positive reviews.
- ✅ A live, reproducible 90s demo (no mocks).
- ✅ A top-3 slot in the Lifestyle category.
- ✅ Social Buzz participation.

---

## 14. Out of Scope (Non-Goals)

- ❌ Orchestrator / budget-managing agent (REJECTED).
- ❌ Autonomous spending mode.
- ❌ The "my own agent pays my own agent" setup.
- ❌ Corporate/financial/technical document processing.
- ❌ Time-skipping / proactivity simulation in the demo.
- ❌ Heavy frontend / multi-page app.

---

## 15. Open Questions

1. **Solo or team?** (If a team, Days 1-3 parallelize, 5+ document types + a rich demo → higher chance of first place. If solo, the scope lock stands as-is.)
2. Frontend stack approval: Next.js + Tailwind by default?
3. LLM provider choice (cost/speed tradeoff).

---

*This document is scope-locked. Change requests are considered as long as they don't collide with the "Out of Scope" section.*

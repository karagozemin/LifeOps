# LifeOps Submission Evidence

This file is the release gate. Do not mark an item complete without a public link or verifiable identifier.

## Public proof

| Evidence | Value | Verified |
|---|---|---|
| Repository | https://github.com/karagozemin/LifeOps | Yes |
| Web app | https://life-ops-web1.vercel.app/ | Yes |
| API health | https://lifeops-75gx.onrender.com/health | Yes |
| ASP ID | `#9204` | Yes |
| OKX.AI listing | Submitted for review | No |
| Real payment tx hash | `0xb8d39f8425bc4ae8ba1d846aacf3b9fcd5868799d5356c8534f5d72f06971d75` | Yes |
| X Layer explorer | https://www.oklink.com/x-layer/tx/0xb8d39f8425bc4ae8ba1d846aacf3b9fcd5868799d5356c8534f5d72f06971d75 | Yes |
| Demo video (90s max) | `<PENDING>` | No |
| X post with `#OKXAI` | `<PENDING>` | No |
| HackQuest submission | `<PENDING>` | No |

## Final technical checks

- [x] Production `/health` reports `ready_for_listing: true` and `demo_mode: false`.
- [x] The 402 challenge has `x402Version: 2`, `resource`, and `accepts[]`.
- [x] The paid retry uses `PAYMENT-SIGNATURE`, not `X-Payment`.
- [x] The response has `PAYMENT-RESPONSE` with a real transaction.
- [ ] Reusing the same signature returns 409.
- [x] The public UI labels web analysis as preview and shows only real settlements.
- [x] Passport travel risk is not double-counted.
- [x] Empty or deadline-free text does not fabricate an obligation.
- [ ] `.ics` imports successfully into a calendar.
- [x] Desktop and mobile layouts have no overlap or horizontal overflow.
- [x] Backend tests, frontend typecheck/build, and npm audit pass.

## 90-second demo cut

| Time | Shot |
|---:|---|
| 0-20s | TravelPlanner requests LifeOps, receives 402, confirms 0.05 USDT0, and gets the real X Layer receipt. |
| 20-42s | Passport result shows the six-month travel rule, source evidence, action dates, and one non-duplicated risk total. |
| 42-60s | Download the generated `.ics` and open the calendar event. |
| 60-78s | Run the three-document audit; show urgency ordering, total risk, and combined reminders. |
| 78-87s | Open the tx hash in OKLink and show the live ASP listing. |
| 87-90s | LifeOps name, Lifestyle Companion, repository URL. |

## Recording rules

- No demo payment, fake tx hash, edited terminal output, or time skip.
- Keep the browser, terminal, OKLink receipt, and marketplace identity readable.
- Use one clean take if possible; captions should name the product outcome, not explain the UI.

## Submission order

1. Wallet login and funding.
2. Public deploy with production secrets and a persistent replay store.
3. Real 0.01 USDT0 smoke payment and tx evidence.
4. ASP registration with all services.
5. Marketplace review submission.
6. Responsive visual QA and final screenshot.
7. Record and upload the demo.
8. Publish the X post with `#OKXAI`.
9. Submit HackQuest form and preserve confirmation proof.

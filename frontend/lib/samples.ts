import type { Sample } from "./types";

export const SAMPLES: Sample[] = [
  {
    id: "passport",
    label: "🛂 Passport (agent call)",
    caller: "TravelPlanner-Agent-v2",
    service: "full_action_pack",
    text:
      "PASSPORT - Holder: Alex Morgan. Passport No: U12345678. Expiry Date: 2026-11-05. Planned travel 2026-10-20, Schengen area (6-month validity rule).",
  },
  {
    id: "warranty",
    label: "🎧 Warranty (39 days left)",
    caller: "human",
    service: "full_action_pack",
    text:
      "WARRANTY CERTIFICATE. Product: Wireless Headphones Pro. Warranty ends in 39 days. Device value approx. 120 USD.",
  },
  {
    id: "subscription",
    label: "💳 Free trial auto-renew",
    caller: "human",
    service: "full_action_pack",
    text:
      "Hi! Your StreamPlus free trial ends in 3 days. It will then convert to the paid plan at 19.99 USD per month unless you cancel in account settings.",
  },
  {
    id: "bill",
    label: "⚡ Electricity bill",
    caller: "human",
    service: "full_action_pack",
    text:
      "ELECTRICITY BILL. Amount Due: 45.00 USD. Payment Due Date: 07/22/2026. A 5% late fee applies and service may be interrupted.",
  },
  {
    id: "license",
    label: "🚗 Driver's license",
    caller: "human",
    service: "full_action_pack",
    text:
      "DRIVER'S LICENSE. Name: Alex Morgan. Class: B. Expiry Date: March 14, 2027. Must be renewed before it expires.",
  },
  {
    id: "multi",
    label: "📚 Multi-audit (3 docs)",
    caller: "LifeAdmin-Agent-v1",
    service: "multi_audit",
    text: [
      "PASSPORT - Holder: Alex Morgan. Passport No: U12345678. Expiry Date: 2026-11-05. Planned travel 2026-10-20, Schengen area.",
      "---",
      "Hi! Your StreamPlus free trial ends in 3 days. It will then convert to the paid plan at 19.99 USD per month unless you cancel in account settings.",
      "---",
      "ELECTRICITY BILL. Amount Due: 45.00 USD. Payment Due Date: 07/22/2026. A 5% late fee applies and service may be interrupted.",
    ].join("\n"),
  },
];

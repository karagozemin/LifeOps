import type { ScanResponse, Payment402, PaymentTx, Service } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface StepEvent {
  kind: "info" | "http" | "tx" | "ok" | "error";
  text: string;
}

/**
 * Runs the full x402 flow against the backend:
 *   1. Unpaid POST /scan   -> expect HTTP 402 + price headers
 *   2. Paid POST /scan     -> settle + guaranteed JSON result
 * Emits log events via onStep so the UI terminal can narrate it live.
 */
export async function scanWithX402(
  text: string,
  service: Service,
  caller: string,
  onStep: (e: StepEvent) => void
): Promise<ScanResponse> {
  const body = JSON.stringify({ text, service, caller });

  // --- 1) unpaid call -> 402 -------------------------------------------------
  onStep({ kind: "info", text: `${caller} → POST /scan (no payment)` });
  const res402 = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  if (res402.status === 402) {
    const info = (await res402.json()) as Payment402;
    const req = info.payment_requirements;
    const human = req ? Number(req.amount) / 1e6 : null;
    onStep({
      kind: "http",
      text: `← HTTP 402 + PAYMENT-REQUIRED · ${human ?? "?"} USDT0 on X Layer (${req?.network ?? "eip155:196"})`,
    });
    onStep({ kind: "info", text: info.message });
  } else {
    onStep({
      kind: "error",
      text: `Expected 402, got HTTP ${res402.status}`,
    });
  }

  // --- 2) paid call ----------------------------------------------------------
  onStep({ kind: "info", text: "Settling payment via A2MCP (X Layer / USDT0)…" });
  const resPaid = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Payment": "demo" },
    body,
  });

  if (!resPaid.ok) {
    onStep({ kind: "error", text: `Scan failed: HTTP ${resPaid.status}` });
    throw new Error(`scan failed: ${resPaid.status}`);
  }

  const data = (await resPaid.json()) as ScanResponse;
  const tx: PaymentTx = data.payment;
  onStep({
    kind: "tx",
    text: `settled ${tx.amount} ${tx.asset} on ${tx.network} · ${tx.tx_hash}`,
  });
  onStep({
    kind: "ok",
    text: `← HTTP 200 · guaranteed JSON · confidence ${data.result.confidence}`,
  });

  return data;
}

export function icsDownloadUrl(icsPath?: string | null): string {
  // Per-result URL when available (concurrency-safe), else latest.
  return `${API_BASE}${icsPath ?? "/ics/latest.ics"}`;
}

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
    const price = res402.headers.get("x402-price");
    const currency = res402.headers.get("x402-currency");
    const network = res402.headers.get("x402-network");
    const info = (await res402.json()) as Payment402;
    onStep({
      kind: "http",
      text: `← HTTP 402 Payment Required · ${price} ${currency} on ${network}`,
    });
    onStep({ kind: "info", text: info.message });
  } else {
    onStep({
      kind: "error",
      text: `Expected 402, got HTTP ${res402.status}`,
    });
  }

  // --- 2) paid call ----------------------------------------------------------
  onStep({ kind: "info", text: "Settling x402 payment (A2MCP)…" });
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
    text: `settled ${tx.amount_usdt} USDT · ${tx.tx_hash}`,
  });
  onStep({
    kind: "ok",
    text: `← HTTP 200 · guaranteed JSON · confidence ${data.result.confidence}`,
  });

  return data;
}

export function icsDownloadUrl(): string {
  return `${API_BASE}/ics/latest.ics`;
}

import type {
  PaymentRequired,
  PaymentTx,
  PreviewResponse,
  Service,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface StepEvent {
  kind: "info" | "http" | "tx" | "ok" | "error";
  text: string;
}

function decodeChallenge(header: string | null): PaymentRequired | null {
  if (!header) return null;
  try {
    const bytes = Uint8Array.from(atob(header), (char) => char.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes)) as PaymentRequired;
  } catch {
    return null;
  }
}

export async function scanPreview(
  text: string,
  service: Service,
  caller: string,
  onStep: (event: StepEvent) => void
): Promise<PreviewResponse> {
  const body = JSON.stringify({ text, service, caller });
  onStep({ kind: "info", text: `${caller} -> POST /scan` });

  const challengeResponse = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  if (challengeResponse.status !== 402) {
    throw new Error(`Expected x402 challenge, received HTTP ${challengeResponse.status}`);
  }

  const challenge = decodeChallenge(challengeResponse.headers.get("PAYMENT-REQUIRED"));
  const accepted = challenge?.accepts[0];
  onStep({
    kind: "http",
    text: `HTTP 402 · ${accepted ? Number(accepted.amount) / 1e6 : "?"} USDT0 · ${accepted?.network ?? "unknown"}`,
  });
  onStep({ kind: "info", text: "PAYMENT-REQUIRED verified · x402 v2" });
  onStep({ kind: "info", text: "Opening rate-limited web preview" });

  const previewResponse = await fetch(`${API_BASE}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  if (!previewResponse.ok) {
    const detail = await previewResponse.text();
    throw new Error(`Preview failed: HTTP ${previewResponse.status} ${detail}`);
  }

  const data = (await previewResponse.json()) as PreviewResponse;
  onStep({
    kind: "ok",
    text: `HTTP 200 · ${data.result.obligations.length} obligations · ${(data.result.confidence * 100).toFixed(0)}% confidence`,
  });
  return data;
}

export async function recentTransactions(): Promise<PaymentTx[]> {
  const response = await fetch(`${API_BASE}/tx?limit=8`, { cache: "no-store" });
  if (!response.ok) return [];
  const data = (await response.json()) as { transactions: PaymentTx[] };
  return data.transactions.filter((transaction) => transaction.mode === "x402");
}

export function icsDownloadUrl(icsPath?: string | null): string {
  return `${API_BASE}${icsPath ?? "/ics/latest.ics"}`;
}

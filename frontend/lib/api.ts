import type {
  PaymentRequired,
  PaymentRequirements,
  PaymentTx,
  PreviewResponse,
  Service,
  SettlementReceipt,
  VerifiedScanResponse,
} from "./types";
import {
  decodePaymentResponseHeader,
  wrapFetchWithPaymentFromConfig,
  type PaymentRequirements as X402PaymentRequirements,
} from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { createOkxSigner, ensureXLayer, type InjectedProvider } from "./wallet";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface StepEvent {
  kind: "info" | "http" | "tx" | "ok" | "error";
  text: string;
}

const X_LAYER = "eip155:196";
const USDT0 = "0x779ded0c9e1022225f8e0630b35a9b54be713736";
const SERVICE_AMOUNTS: Record<Service, string> = {
  scan: "10000",
  full_action_pack: "50000",
  multi_audit: "200000",
};

function decodeChallenge(header: string | null): PaymentRequired | null {
  if (!header) return null;
  try {
    const bytes = Uint8Array.from(atob(header), (char) => char.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes)) as PaymentRequired;
  } catch {
    return null;
  }
}

function assertSafeRequirement(
  requirement: PaymentRequirements | undefined,
  service: Service
): PaymentRequirements {
  if (!requirement) throw new Error("LifeOps did not return a supported payment option.");
  if (requirement.scheme !== "exact") throw new Error("Only one-time exact payments are supported.");
  if (requirement.network !== X_LAYER) throw new Error("The payment challenge is not for X Layer.");
  if (requirement.asset.toLowerCase() !== USDT0) throw new Error("The payment challenge is not for USDT0.");
  if (requirement.amount !== SERVICE_AMOUNTS[service]) {
    throw new Error("The payment amount does not match the selected LifeOps service.");
  }
  if (!/^0x[0-9a-f]{40}$/i.test(requirement.payTo)) {
    throw new Error("The payment recipient is invalid.");
  }
  return requirement;
}

function sameRequirement(left: X402PaymentRequirements, right: PaymentRequirements): boolean {
  return left.scheme === right.scheme
    && left.network === right.network
    && left.asset.toLowerCase() === right.asset.toLowerCase()
    && left.amount === right.amount
    && left.payTo.toLowerCase() === right.payTo.toLowerCase();
}

async function responseError(response: Response, fallback: string): Promise<Error> {
  try {
    const data = await response.json() as { message?: string; detail?: string; error?: string };
    return new Error(data.message ?? data.detail ?? data.error ?? fallback);
  } catch {
    return new Error(fallback);
  }
}

export async function paymentQuote(
  text: string,
  service: Service,
  caller: string
): Promise<PaymentRequirements> {
  const response = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, service, caller }),
  });
  if (response.status !== 402) {
    throw await responseError(response, `Expected a payment challenge, received HTTP ${response.status}.`);
  }
  const challenge = decodeChallenge(response.headers.get("PAYMENT-REQUIRED"));
  return assertSafeRequirement(challenge?.accepts[0], service);
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

export async function verifiedScan(
  text: string,
  service: Service,
  caller: string,
  approved: PaymentRequirements,
  provider: InjectedProvider,
  address: `0x${string}`,
  onStep: (event: StepEvent) => void
): Promise<VerifiedScanResponse> {
  assertSafeRequirement(approved, service);
  await ensureXLayer(provider);

  let requestNumber = 0;
  const observedFetch: typeof globalThis.fetch = async (input, init) => {
    requestNumber += 1;
    const request = new Request(input, init);
    request.headers.delete("Access-Control-Expose-Headers");
    const isSigned = request.headers.has("PAYMENT-SIGNATURE");

    if (requestNumber === 1) onStep({ kind: "info", text: `${caller} -> POST /scan` });
    if (isSigned) onStep({ kind: "tx", text: "Wallet authorization signed · submitting for settlement" });

    const response = await fetch(request);
    if (requestNumber === 1 && response.status === 402) {
      onStep({ kind: "http", text: `HTTP 402 · ${Number(approved.amount) / 1e6} USDT0 · ${approved.network}` });
      onStep({ kind: "info", text: "Payment terms matched the user-approved quote" });
    }
    if (isSigned && response.ok) {
      onStep({ kind: "ok", text: "HTTP 200 · settlement confirmed on X Layer" });
    }
    return response;
  };

  const fetchWithPayment = wrapFetchWithPaymentFromConfig(observedFetch, {
    schemes: [{ network: X_LAYER, client: new ExactEvmScheme(createOkxSigner(provider, address)) }],
    paymentRequirementsSelector: (_version, candidates) => {
      const matched = candidates.find((candidate) => sameRequirement(candidate, approved));
      if (!matched) throw new Error("Payment terms changed after confirmation. No payment was authorized.");
      return matched;
    },
  });

  const response = await fetchWithPayment(`${API_BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, service, caller }),
  });
  if (!response.ok) {
    throw await responseError(response, `Verified run failed with HTTP ${response.status}.`);
  }

  const receiptHeader = response.headers.get("PAYMENT-RESPONSE");
  if (!receiptHeader) throw new Error("Settlement succeeded without a readable payment receipt.");
  const decoded = decodePaymentResponseHeader(receiptHeader);
  if (!decoded.success || !decoded.transaction) throw new Error(decoded.errorMessage ?? "Settlement was not confirmed.");

  const data = await response.json() as Omit<VerifiedScanResponse, "settlement">;
  const settlement: SettlementReceipt = {
    success: decoded.success,
    transaction: decoded.transaction,
    network: decoded.network,
    amount: decoded.amount ?? approved.amount,
    payer: decoded.payer,
  };
  onStep({ kind: "ok", text: `Receipt · ${decoded.transaction.slice(0, 10)}...${decoded.transaction.slice(-6)}` });
  return { ...data, settlement };
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

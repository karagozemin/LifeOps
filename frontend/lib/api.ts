import type {
  PaymentRequired,
  PaymentRequirements,
  PaymentTx,
  PreviewResponse,
  Service,
  SettlementReceipt,
  VerifiedScanResponse,
} from "./types";
import type { InjectedProvider } from "./wallet";

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

// UTF-8-safe base64. The payment challenge's extra.name is "USD\u20AE0" (the
// \u20AE glyph), and a plain btoa() THROWS on any non-Latin1 character, killing
// the request before the header is even built. Encode/decode through TextEncoder
// so the unicode token name survives the round trip intact.
function base64EncodeUtf8(input: string): string {
  const bytes = new TextEncoder().encode(input);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function base64DecodeUtf8(input: string): string {
  const binary = atob(input);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
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

// EIP-3009 TransferWithAuthorization typed-data types. Mirrors the backend's
// AUTHORIZATION_TYPES exactly so the facilitator recovers the same signer.
const EIP3009_TYPES = {
  EIP712Domain: [
    { name: "name", type: "string" },
    { name: "version", type: "string" },
    { name: "chainId", type: "uint256" },
    { name: "verifyingContract", type: "address" },
  ],
  TransferWithAuthorization: [
    { name: "from", type: "address" },
    { name: "to", type: "address" },
    { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce", type: "bytes32" },
  ],
} as const;

interface SettleResponsePayload {
  success?: boolean;
  transaction?: string;
  network?: string;
  amount?: string;
  payer?: string;
  errorReason?: string;
  errorMessage?: string;
}

function randomNonce(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  let hex = "";
  for (const byte of bytes) hex += byte.toString(16).padStart(2, "0");
  return "0x" + hex;
}

// Library-free x402 v2 flow. The @x402/fetch + @x402/evm wrapper hangs before
// ever reaching the signer (BigInt in its await chain with the OKX provider),
// so we drive the 402 -> sign -> resend loop by hand. Every value is a string,
// the signature is the exact eth_signTypedData_v4 call proven to open OKX, and
// the resend uses PAYMENT-SIGNATURE (the only header the backend accepts).
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
  const body = JSON.stringify({ text, service, caller });
  const chainId = Number(approved.network.split(":")[1]); // eip155:196 -> 196

  onStep({ kind: "info", text: `${caller} -> POST /scan` });

  // 1) First call to confirm the live 402 (terms already user-approved).
  const challengeResponse = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  if (challengeResponse.status !== 402) {
    if (!challengeResponse.ok) {
      throw await responseError(challengeResponse, `Verified run failed with HTTP ${challengeResponse.status}.`);
    }
    throw new Error(`Expected a payment challenge, received HTTP ${challengeResponse.status}.`);
  }
  onStep({ kind: "http", text: `HTTP 402 · ${Number(approved.amount) / 1e6} USDT0 · ${approved.network}` });
  onStep({ kind: "info", text: "Payment terms matched the user-approved quote" });

  // 2) Build the EIP-3009 authorization. All fields are decimal/hex strings so
  //    JSON.stringify never sees a BigInt (the freeze the library never escaped).
  const now = Math.floor(Date.now() / 1000);
  const validAfter = String(now - 600); // clock-skew buffer, matches SDK default
  const validBefore = String(now + (approved.maxTimeoutSeconds || 3600));
  const nonce = randomNonce();
  const authorization = {
    from: address,
    to: approved.payTo,
    value: approved.amount,
    validAfter,
    validBefore,
    nonce,
  };

  // 3) Sign directly through OKX. domain.name carries the unicode token name
  //    (USD\u20AE0) exactly as the backend uses it in the EIP-712 domain.
  const typedData = {
    types: EIP3009_TYPES,
    primaryType: "TransferWithAuthorization",
    domain: {
      name: approved.extra.name,
      version: approved.extra.version,
      chainId,
      verifyingContract: approved.asset,
    },
    message: authorization,
  };

  const signature = await provider.request<`0x${string}`>({
    method: "eth_signTypedData_v4",
    params: [address, JSON.stringify(typedData)],
  });
  onStep({ kind: "tx", text: "Wallet authorization signed · submitting for settlement" });

  // 4) Wrap into the exact PaymentPayload the backend's decode expects. The
  //    `accepted` block must be byte-identical to the server requirements, so
  //    reuse the decoded challenge object verbatim (camelCase, incl. extra).
  const paymentPayload = {
    x402Version: 2,
    payload: { authorization, signature },
    accepted: {
      scheme: approved.scheme,
      network: approved.network,
      asset: approved.asset,
      amount: approved.amount,
      payTo: approved.payTo,
      maxTimeoutSeconds: approved.maxTimeoutSeconds,
      extra: approved.extra,
    },
  };
  const paymentHeader = base64EncodeUtf8(JSON.stringify(paymentPayload));

  // 5) Resend with PAYMENT-SIGNATURE (X-PAYMENT is rejected by the backend).
  const response = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "PAYMENT-SIGNATURE": paymentHeader,
    },
    body,
  });
  if (!response.ok) {
    throw await responseError(response, `Verified run failed with HTTP ${response.status}.`);
  }
  onStep({ kind: "ok", text: "HTTP 200 · settlement confirmed on X Layer" });

  const receiptHeader = response.headers.get("PAYMENT-RESPONSE");
  if (!receiptHeader) throw new Error("Settlement succeeded without a readable payment receipt.");
  const decoded = JSON.parse(base64DecodeUtf8(receiptHeader)) as SettleResponsePayload;
  if (!decoded.success || !decoded.transaction) {
    throw new Error(decoded.errorMessage ?? decoded.errorReason ?? "Settlement was not confirmed.");
  }

  const data = await response.json() as Omit<VerifiedScanResponse, "settlement">;
  const settlement: SettlementReceipt = {
    success: decoded.success,
    transaction: decoded.transaction,
    network: decoded.network ?? approved.network,
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

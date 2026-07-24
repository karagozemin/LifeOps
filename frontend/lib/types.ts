export interface Obligation {
  title: string;
  due_date: string;
  start_action_by: string;
  risk_if_missed: string;
  money_at_risk_usd: number;
  days_remaining: number;
  steps: string[];
  status: "overdue" | "due_soon" | "upcoming";
  risk_basis: string;
  money_at_risk_is_estimate: boolean;
}

export interface EvidenceItem {
  field: string;
  value: string;
  source_text: string;
}

export interface Entities {
  expiry_date: string | null;
  holder: string | null;
  provider: string | null;
  amount_usd: number | null;
  reference: string | null;
}

export interface LifeOpsResult {
  document_type: string;
  entities: Entities;
  obligations: Obligation[];
  reminders: string[];
  total_money_at_risk_usd: number;
  ics_base64: string;
  confidence: number;
  documents_scanned: number;
  evidence: EvidenceItem[];
  warnings: string[];
  extraction_mode: "deterministic" | "llm" | "hybrid";
}

export interface PaymentTx {
  ts: string;
  service: string;
  caller: string;
  payer: string | null;
  amount: number;
  amount_base_units: string;
  asset: string;
  network: string;
  chain: string;
  tx_hash: string;
  status: string;
  mode: "x402" | "demo";
  protocol: string;
}

export interface PreviewResponse {
  result: LifeOpsResult;
  result_id: string;
  ics_url: string | null;
  preview: true;
}

export interface PaymentRequirements {
  scheme: string;
  network: string;
  asset: string;
  amount: string;
  payTo: string;
  maxTimeoutSeconds: number;
  extra: { name: string; version: string };
}

export interface PaymentRequired {
  x402Version: number;
  error?: string;
  resource?: { url: string; description?: string; mimeType?: string; serviceName?: string };
  accepts: PaymentRequirements[];
}

export type Service = "scan" | "full_action_pack" | "multi_audit";

export interface Sample {
  id: string;
  label: string;
  caller: string;
  service: Service;
  text: string;
}

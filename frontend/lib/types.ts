export interface Obligation {
  title: string;
  due_date: string;
  start_action_by: string;
  risk_if_missed: string;
  money_at_risk_usd: number;
  days_remaining: number;
  steps: string[];
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
}

export interface PaymentTx {
  ts: string;
  service: string;
  caller: string;
  amount: number;
  asset: string;
  network: string;
  chain: string;
  tx_hash: string;
  status: string;
  mode: string;
  protocol: string;
}

export interface ScanResponse {
  payment: PaymentTx;
  result: LifeOpsResult;
  result_id: string;
  ics_url: string | null;
}

export interface PaymentRequirements {
  scheme: string;
  network: string;
  asset: string;
  amount: string;
  payTo: string;
  description?: string;
}

export interface Payment402 {
  error: string;
  message: string;
  payment_requirements?: PaymentRequirements;
  how_to_pay: string;
}

export type Service = "scan" | "full_action_pack" | "multi_audit";

export interface Sample {
  id: string;
  label: string;
  caller: string;
  service: Service;
  text: string;
}

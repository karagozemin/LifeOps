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
}

export interface PaymentTx {
  ts: string;
  service: string;
  caller: string;
  amount_usdt: number;
  tx_hash: string;
  status: string;
  protocol: string;
}

export interface ScanResponse {
  payment: PaymentTx;
  result: LifeOpsResult;
}

export interface Payment402 {
  error: string;
  message: string;
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

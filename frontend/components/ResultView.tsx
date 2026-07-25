"use client";

import {
  AlertTriangle,
  ArrowUpRight,
  CalendarDays,
  Check,
  CircleDollarSign,
  Download,
  FileCheck2,
  Fingerprint,
  Quote,
} from "lucide-react";
import type { LifeOpsResult, Obligation } from "@/lib/types";
import { icsDownloadUrl } from "@/lib/api";

function statusMeta(obligation: Obligation) {
  if (obligation.status === "overdue") return { label: "Overdue", tone: "overdue" };
  if (obligation.status === "due_soon") return { label: `${obligation.days_remaining} days`, tone: "soon" };
  return { label: `${obligation.days_remaining} days`, tone: "upcoming" };
}

export default function ResultView({ result, icsUrl }: { result: LifeOpsResult; icsUrl?: string | null }) {
  const isMulti = result.document_type === "multi";

  return (
    <div className="result-shell result-enter">
      <header className="result-header">
        <div className="result-title">
          <span className="result-icon"><FileCheck2 size={17} /></span>
          <div>
            <span className="section-index">02 / INTELLIGENCE</span>
            <h2>Life action plan</h2>
          </div>
        </div>
        <div className="result-meta">
          <span>{result.document_type.replaceAll("_", " ")}</span>
          {isMulti && <span>{result.documents_scanned} documents</span>}
          <span>{(result.confidence * 100).toFixed(0)}% confidence</span>
          <span>{result.extraction_mode}</span>
        </div>
        {icsUrl && (
          <a href={icsDownloadUrl(icsUrl)} className="calendar-button">
            <Download size={15} />
            Add to calendar
          </a>
        )}
      </header>

      <section className="risk-overview" aria-label="Risk overview">
        <div className="risk-primary">
          <span>Money exposed</span>
          <strong>${result.total_money_at_risk_usd.toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong>
          <small>Conservative total across detected obligations</small>
        </div>
        <Metric value={String(result.obligations.length)} label="Obligations" />
        <Metric value={String(result.reminders.length)} label="Reminders" />
        <Metric value={String(result.evidence.length)} label="Evidence points" />
      </section>

      {result.warnings.length > 0 && (
        <div className="warning-row">
          {result.warnings.map((warning) => (
            <span key={warning}><AlertTriangle size={13} />{warning.replaceAll("_", " ")}</span>
          ))}
        </div>
      )}

      <section className="obligation-list" aria-label="Detected obligations">
        <div className="subsection-heading">
          <span>PRIORITY QUEUE</span>
          <span>{result.obligations.length.toString().padStart(2, "0")} detected</span>
        </div>
        {result.obligations.length === 0 ? (
          <div className="no-obligations">No supported deadline found. LifeOps did not fabricate one.</div>
        ) : (
          result.obligations.map((obligation, index) => {
            const status = statusMeta(obligation);
            return (
              <article key={`${obligation.title}-${obligation.due_date}-${index}`} className="obligation-row">
                <div className="obligation-number">{String(index + 1).padStart(2, "0")}</div>
                <div className="obligation-main">
                  <div className="obligation-title-row">
                    <div>
                      <span className="obligation-date">DUE {obligation.due_date} · START {obligation.start_action_by}</span>
                      <h3>{obligation.title}</h3>
                    </div>
                    <span className={`status-chip ${status.tone}`}>{status.label}</span>
                  </div>
                  <p className="risk-copy">{obligation.risk_if_missed}</p>
                  <ol className="action-steps">
                    {obligation.steps.map((step, stepIndex) => (
                      <li key={`${stepIndex}-${step}`}><span><Check size={12} /></span>{step}</li>
                    ))}
                  </ol>
                </div>
                <aside className="risk-basis">
                  <CircleDollarSign size={16} />
                  <strong>${obligation.money_at_risk_usd.toLocaleString()}</strong>
                  <p>{obligation.risk_basis}</p>
                  <span>{obligation.money_at_risk_is_estimate ? "Conservative estimate" : "Document-backed"}</span>
                </aside>
              </article>
            );
          })
        )}
      </section>

      <div className="result-details">
        <section aria-label="Extracted entities">
          <DetailTitle icon={Fingerprint}>Extracted entities</DetailTitle>
          <dl className="entity-list">
            {result.entities.holder && <DataRow label="Holder" value={result.entities.holder} />}
            {result.entities.provider && <DataRow label="Provider" value={result.entities.provider} />}
            {result.entities.expiry_date && <DataRow label="Expiry" value={result.entities.expiry_date} />}
            {result.entities.amount_usd != null && <DataRow label="Amount" value={`$${result.entities.amount_usd}`} />}
            {result.entities.reference && <DataRow label="Reference" value={result.entities.reference} />}
            {!Object.values(result.entities).some((value) => value != null) && <p className="detail-empty">No entities extracted</p>}
          </dl>
        </section>
        <section aria-label="Calendar reminders">
          <DetailTitle icon={CalendarDays}>Calendar sequence</DetailTitle>
          <ol className="reminder-list">
            {result.reminders.map((reminder, index) => (
              <li key={reminder}><span>{String(index + 1).padStart(2, "0")}</span>{reminder}</li>
            ))}
            {result.reminders.length === 0 && <li className="detail-empty">No future reminders</li>}
          </ol>
        </section>
      </div>

      {result.evidence.length > 0 && (
        <section className="evidence-section" aria-label="Source evidence">
          <div className="evidence-heading">
            <DetailTitle icon={Quote}>Source evidence</DetailTitle>
            <span><Check size={12} /> Traceable to input</span>
          </div>
          <div className="evidence-list">
            {result.evidence.map((item, index) => (
              <blockquote key={`${item.field}-${index}`}>
                <span>{item.field}</span>
                <p>“{item.source_text}”</p>
                <ArrowUpRight size={14} aria-hidden="true" />
              </blockquote>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="risk-metric"><strong>{value}</strong><span>{label}</span></div>;
}

function DetailTitle({ icon: Icon, children }: { icon: typeof Fingerprint; children: React.ReactNode }) {
  return <h3 className="detail-title"><Icon size={14} />{children}</h3>;
}

function DataRow({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}

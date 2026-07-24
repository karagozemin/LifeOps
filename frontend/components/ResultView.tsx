"use client";

import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  Download,
  FileCheck2,
  Quote,
} from "lucide-react";
import type { LifeOpsResult, Obligation } from "@/lib/types";
import { icsDownloadUrl } from "@/lib/api";

function statusStyle(obligation: Obligation) {
  if (obligation.status === "overdue") {
    return { label: "Overdue", className: "border-danger/40 bg-danger/10 text-red-300" };
  }
  if (obligation.status === "due_soon") {
    return { label: `${obligation.days_remaining} days`, className: "border-warn/40 bg-warn/10 text-warn" };
  }
  return { label: `${obligation.days_remaining} days`, className: "border-ok/30 bg-ok/10 text-ok" };
}

export default function ResultView({
  result,
  icsUrl,
}: {
  result: LifeOpsResult;
  icsUrl?: string | null;
}) {
  const isMulti = result.document_type === "multi";

  return (
    <div className="rounded-lg border border-edge bg-panel">
      <div className="flex flex-wrap items-center gap-3 border-b border-edge px-4 py-3">
        <FileCheck2 size={17} className="text-accent" aria-hidden="true" />
        <h2 className="text-sm font-medium text-white">Analysis result</h2>
        <span className="rounded border border-edge bg-surface px-2 py-1 font-mono text-[11px] uppercase text-gray-300">
          {result.document_type.replaceAll("_", " ")}
        </span>
        {isMulti && <span className="text-xs text-warn">{result.documents_scanned} documents</span>}
        <span className="ml-auto font-mono text-xs text-muted">
          {(result.confidence * 100).toFixed(0)}% · {result.extraction_mode}
        </span>
        {icsUrl && (
          <a
            href={icsDownloadUrl(icsUrl)}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-edge bg-surface px-3 text-xs font-medium text-white hover:border-accent"
          >
            <Download size={14} aria-hidden="true" />
            Calendar
          </a>
        )}
      </div>

      <div className="grid border-b border-edge sm:grid-cols-[220px_1fr]">
        <div className="border-b border-edge bg-danger/5 p-4 sm:border-b-0 sm:border-r">
          <p className="text-xs text-red-300">Money at risk</p>
          <p className="mt-1 text-3xl font-semibold text-danger">
            ${result.total_money_at_risk_usd.toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-px bg-edge sm:grid-cols-3">
          <Metric label="Obligations" value={String(result.obligations.length)} />
          <Metric label="Reminders" value={String(result.reminders.length)} />
          <Metric label="Evidence" value={String(result.evidence.length)} />
        </div>
      </div>

      {result.warnings.length > 0 && (
        <div className="flex flex-wrap gap-2 border-b border-edge px-4 py-3">
          {result.warnings.map((warning) => (
            <span key={warning} className="inline-flex items-center gap-1.5 text-xs text-warn">
              <AlertTriangle size={13} aria-hidden="true" />
              {warning.replaceAll("_", " ")}
            </span>
          ))}
        </div>
      )}

      <div className="divide-y divide-edge">
        {result.obligations.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted">No supported deadline found</div>
        ) : (
          result.obligations.map((obligation, index) => {
            const status = statusStyle(obligation);
            return (
              <article key={`${obligation.title}-${obligation.due_date}-${index}`} className="p-4">
                <div className="flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <h3 className="font-medium text-white">{obligation.title}</h3>
                    <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                      <span>Due {obligation.due_date}</span>
                      <span>Start {obligation.start_action_by}</span>
                    </p>
                  </div>
                  <span className={`shrink-0 rounded border px-2 py-1 font-mono text-[11px] ${status.className}`}>
                    {status.label}
                  </span>
                </div>

                <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_220px]">
                  <div>
                    <p className="text-sm leading-6 text-gray-300">{obligation.risk_if_missed}</p>
                    <ol className="mt-3 space-y-2">
                      {obligation.steps.map((step, stepIndex) => (
                        <li key={`${stepIndex}-${step}`} className="flex gap-2 text-sm text-gray-300">
                          <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-accent" aria-hidden="true" />
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                  <div className="rounded-md border border-edge bg-surface p-3">
                    <p className="font-mono text-lg font-semibold text-danger">
                      ${obligation.money_at_risk_usd.toLocaleString()}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-muted">{obligation.risk_basis}</p>
                    <p className="mt-2 font-mono text-[10px] uppercase text-gray-600">
                      {obligation.money_at_risk_is_estimate ? "Estimated" : "Document-backed"}
                    </p>
                  </div>
                </div>
              </article>
            );
          })
        )}
      </div>

      <div className="grid border-t border-edge lg:grid-cols-2">
        <section className="border-b border-edge p-4 lg:border-b-0 lg:border-r" aria-label="Extracted entities">
          <SectionTitle icon={FileCheck2}>Entities</SectionTitle>
          <dl className="mt-3 space-y-2 text-sm">
            {result.entities.holder && <Row label="Holder" value={result.entities.holder} />}
            {result.entities.provider && <Row label="Provider" value={result.entities.provider} />}
            {result.entities.expiry_date && <Row label="Expiry" value={result.entities.expiry_date} />}
            {result.entities.amount_usd != null && <Row label="Amount" value={`$${result.entities.amount_usd}`} />}
            {result.entities.reference && <Row label="Reference" value={result.entities.reference} />}
            {!Object.values(result.entities).some((value) => value != null) && (
              <p className="text-sm text-muted">No entities extracted</p>
            )}
          </dl>
        </section>

        <section className="p-4" aria-label="Calendar reminders">
          <SectionTitle icon={CalendarDays}>Reminders</SectionTitle>
          <ul className="mt-3 space-y-2 font-mono text-xs text-gray-300">
            {result.reminders.map((reminder) => <li key={reminder}>{reminder}</li>)}
            {result.reminders.length === 0 && <li className="text-muted">No future reminders</li>}
          </ul>
        </section>
      </div>

      {result.evidence.length > 0 && (
        <section className="border-t border-edge p-4" aria-label="Source evidence">
          <SectionTitle icon={Quote}>Source evidence</SectionTitle>
          <div className="mt-3 divide-y divide-edge">
            {result.evidence.map((item, index) => (
              <blockquote key={`${item.field}-${index}`} className="grid gap-1 py-3 text-sm sm:grid-cols-[130px_1fr]">
                <span className="font-mono text-xs text-accent">{item.field}</span>
                <span className="text-gray-300">“{item.source_text}”</span>
              </blockquote>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-panel p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 font-mono text-lg text-white">{value}</p>
    </div>
  );
}

function SectionTitle({ icon: Icon, children }: { icon: typeof FileCheck2; children: React.ReactNode }) {
  return (
    <h3 className="flex items-center gap-2 text-xs font-medium uppercase text-muted">
      <Icon size={14} aria-hidden="true" />
      {children}
    </h3>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[90px_1fr] gap-3">
      <dt className="text-muted">{label}</dt>
      <dd className="break-words text-gray-200">{value}</dd>
    </div>
  );
}

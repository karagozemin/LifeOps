"use client";

import type { LifeOpsResult } from "@/lib/types";
import { icsDownloadUrl } from "@/lib/api";

function urgency(days: number): { label: string; cls: string } {
  if (days <= 7) return { label: "URGENT", cls: "bg-danger/15 text-danger border-danger/40" };
  if (days <= 45) return { label: "SOON", cls: "bg-warn/15 text-warn border-warn/40" };
  return { label: "PLANNED", cls: "bg-ok/15 text-ok border-ok/40" };
}

export default function ResultView({
  result,
  icsUrl,
}: {
  result: LifeOpsResult;
  icsUrl?: string | null;
}) {
  const { entities } = result;
  const isMulti = result.document_type === "multi";

  return (
    <div className="space-y-4">
      {/* header row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="rounded-md border border-edge bg-panel px-2.5 py-1 font-mono text-xs uppercase tracking-wide text-accent">
            {result.document_type}
          </span>
          {isMulti && (
            <span className="rounded-md border border-warn/40 bg-warn/10 px-2.5 py-1 font-mono text-xs text-warn">
              {result.documents_scanned} docs audited
            </span>
          )}
          <span className="text-xs text-gray-500">
            confidence {(result.confidence * 100).toFixed(0)}%
          </span>
        </div>
        <a
          href={icsDownloadUrl(icsUrl)}
          className="rounded-lg border border-accent/50 bg-accent/10 px-3 py-1.5 text-sm font-medium text-accent transition hover:bg-accent/20"
        >
          ⬇ Download .ics
        </a>
      </div>

      {/* total money at risk — the money shot */}
      <div className="rounded-xl border border-danger/40 bg-danger/10 p-5">
        <p className="text-xs uppercase tracking-widest text-danger/80">
          Total money at risk
        </p>
        <p className="mt-1 text-4xl font-bold text-danger">
          ${result.total_money_at_risk_usd.toLocaleString()}
        </p>
      </div>

      {/* obligations */}
      <div className="space-y-3">
        {result.obligations.map((ob, i) => {
          const u = urgency(ob.days_remaining);
          return (
            <div
              key={i}
              className="rounded-xl border border-edge bg-panel p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-gray-100">{ob.title}</h3>
                  <p className="mt-0.5 text-sm text-gray-400">
                    Due {ob.due_date} · start by {ob.start_action_by}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-md border px-2 py-1 font-mono text-xs ${u.cls}`}
                >
                  {ob.days_remaining}d · {u.label}
                </span>
              </div>

              <p className="mt-3 text-sm text-gray-300">
                <span className="text-danger">⚠ Risk:</span> {ob.risk_if_missed}{" "}
                <span className="font-semibold text-danger">
                  (${ob.money_at_risk_usd.toLocaleString()})
                </span>
              </p>

              {ob.steps.length > 0 && (
                <ol className="mt-3 space-y-1.5">
                  {ob.steps.map((s, j) => (
                    <li key={j} className="flex gap-2 text-sm text-gray-300">
                      <span className="font-mono text-accent">{j + 1}.</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          );
        })}
      </div>

      {/* entities + reminders */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-edge bg-panel p-4">
          <p className="mb-2 text-xs uppercase tracking-wide text-gray-500">
            Entities
          </p>
          <dl className="space-y-1 text-sm">
            {entities.holder && <Row k="Holder" v={entities.holder} />}
            {entities.provider && <Row k="Provider" v={entities.provider} />}
            {entities.expiry_date && <Row k="Expiry" v={entities.expiry_date} />}
            {entities.amount_usd != null && (
              <Row k="Amount" v={`$${entities.amount_usd}`} />
            )}
            {entities.reference && <Row k="Ref" v={entities.reference} />}
          </dl>
        </div>
        <div className="rounded-xl border border-edge bg-panel p-4">
          <p className="mb-2 text-xs uppercase tracking-wide text-gray-500">
            Reminders
          </p>
          <ul className="space-y-1 font-mono text-sm text-gray-300">
            {result.reminders.map((r, i) => (
              <li key={i}>🔔 {r}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-gray-500">{k}</dt>
      <dd className="text-gray-200">{v}</dd>
    </div>
  );
}

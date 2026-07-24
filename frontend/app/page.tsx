"use client";

import { useState } from "react";
import {
  Activity,
  Bot,
  FileSearch,
  Layers3,
  ScanText,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { SAMPLES } from "@/lib/samples";
import { scanPreview, type StepEvent } from "@/lib/api";
import type { LifeOpsResult, Service } from "@/lib/types";
import TxTerminal from "@/components/TxTerminal";
import ResultView from "@/components/ResultView";

const SERVICES: Array<{ id: Service; label: string; price: string }> = [
  { id: "scan", label: "Scan", price: "0.01" },
  { id: "full_action_pack", label: "Action pack", price: "0.05" },
  { id: "multi_audit", label: "Multi-audit", price: "0.20" },
];

export default function Home() {
  const [text, setText] = useState("");
  const [caller, setCaller] = useState("human");
  const [service, setService] = useState<Service>("full_action_pack");
  const [icsUrl, setIcsUrl] = useState<string | null>(null);
  const [log, setLog] = useState<StepEvent[]>([]);
  const [result, setResult] = useState<LifeOpsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function loadSample(id: string) {
    const sample = SAMPLES.find((item) => item.id === id);
    if (!sample) return;
    setText(sample.text);
    setCaller(sample.caller);
    setService(sample.service);
    setResult(null);
    setIcsUrl(null);
    setError(null);
    setLog([]);
  }

  async function runScan() {
    if (!text.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setIcsUrl(null);
    setLog([]);
    const push = (event: StepEvent) => setLog((previous) => [...previous, event]);

    try {
      const data = await scanPreview(text, service, caller, push);
      setResult(data.result);
      setIcsUrl(data.ics_url);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Request failed";
      setError(message);
      push({ kind: "error", text: message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-edge bg-ink/95">
        <div className="mx-auto flex max-w-[1480px] items-center gap-4 px-4 py-4 sm:px-6">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-accent/40 bg-accent/10 text-accent">
            <ShieldCheck size={20} aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-semibold text-white">LifeOps</h1>
            <p className="truncate text-xs text-muted">Personal deadline intelligence</p>
          </div>
          <div className="ml-auto hidden items-center gap-5 text-xs sm:flex">
            <Status icon={Activity} label="API ready" tone="green" />
            <Status icon={Layers3} label="X Layer" />
            <span className="font-mono text-muted">x402 v2 · USDT0</span>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1480px] gap-5 px-4 py-5 sm:px-6 xl:grid-cols-[minmax(0,1.12fr)_minmax(380px,.88fr)]">
        <section className="min-w-0 space-y-5" aria-label="Document analysis">
          <div className="rounded-lg border border-edge bg-panel">
            <div className="flex flex-col gap-3 border-b border-edge p-4 sm:flex-row sm:items-center">
              <div className="flex items-center gap-2 text-sm font-medium text-white">
                <FileSearch size={17} className="text-accent" aria-hidden="true" />
                Document input
              </div>
              <label className="sm:ml-auto">
                <span className="sr-only">Load sample</span>
                <select
                  defaultValue=""
                  onChange={(event) => loadSample(event.target.value)}
                  className="h-9 w-full rounded-md border border-edge bg-surface px-3 text-sm text-gray-200 outline-none focus:border-accent sm:w-52"
                >
                  <option value="" disabled>Load a sample</option>
                  {SAMPLES.map((sample) => (
                    <option key={sample.id} value={sample.id}>{sample.label}</option>
                  ))}
                </select>
              </label>
            </div>

            <div className="p-4">
              <textarea
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="Paste a passport, warranty, subscription notice, bill, or appointment text"
                maxLength={50000}
                className="h-48 w-full resize-y rounded-md border border-edge bg-surface p-3 font-mono text-sm leading-6 text-gray-100 outline-none placeholder:text-gray-600 focus:border-accent"
              />

              <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-center">
                <div className="grid grid-cols-3 rounded-md border border-edge bg-surface p-1" role="group" aria-label="Service level">
                  {SERVICES.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setService(item.id)}
                      aria-pressed={service === item.id}
                      className={`min-h-11 px-3 py-1 text-left text-xs transition ${
                        service === item.id
                          ? "rounded bg-white text-black"
                          : "text-gray-400 hover:text-white"
                      }`}
                    >
                      <span className="block font-medium">{item.label}</span>
                      <span className="block font-mono opacity-70">{item.price} USDT0</span>
                    </button>
                  ))}
                </div>

                <div className="flex min-w-0 items-center gap-2 text-xs text-muted">
                  {caller.toLowerCase().includes("agent") ? <Bot size={15} /> : <UserRound size={15} />}
                  <span className="truncate font-mono">{caller}</span>
                  <span className="text-gray-700">/</span>
                  <span className="font-mono">{text.length.toLocaleString()} chars</span>
                </div>

                <button
                  type="button"
                  onClick={runScan}
                  disabled={loading || !text.trim()}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-accent px-5 text-sm font-semibold text-black transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-40 lg:ml-auto"
                >
                  <ScanText size={17} aria-hidden="true" />
                  {loading ? "Analyzing" : "Run preview"}
                </button>
              </div>
            </div>
          </div>

          {error && (
            <div role="alert" className="rounded-md border border-danger/40 bg-danger/10 p-3 text-sm text-red-200">
              {error}
            </div>
          )}

          {result ? (
            <ResultView result={result} icsUrl={icsUrl} />
          ) : (
            <div className="flex min-h-44 items-center justify-center rounded-lg border border-dashed border-edge text-sm text-muted">
              No analysis yet
            </div>
          )}
        </section>

        <aside className="min-w-0 xl:sticky xl:top-5 xl:h-[calc(100vh-2.5rem)]" aria-label="x402 activity">
          <TxTerminal log={log} />
        </aside>
      </div>
    </main>
  );
}

function Status({
  icon: Icon,
  label,
  tone = "neutral",
}: {
  icon: typeof Activity;
  label: string;
  tone?: "green" | "neutral";
}) {
  return (
    <span className={`inline-flex items-center gap-1.5 ${tone === "green" ? "text-ok" : "text-gray-300"}`}>
      <Icon size={14} aria-hidden="true" />
      {label}
    </span>
  );
}

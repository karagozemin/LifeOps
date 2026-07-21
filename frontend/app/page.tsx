"use client";

import { useState } from "react";
import { SAMPLES } from "@/lib/samples";
import { scanWithX402, type StepEvent } from "@/lib/api";
import type { LifeOpsResult, Service } from "@/lib/types";
import TxTerminal from "@/components/TxTerminal";
import ResultView from "@/components/ResultView";

export default function Home() {
  const [text, setText] = useState("");
  const [caller, setCaller] = useState("human");
  const [service] = useState<Service>("full_action_pack");
  const [log, setLog] = useState<StepEvent[]>([]);
  const [result, setResult] = useState<LifeOpsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function loadSample(id: string) {
    const s = SAMPLES.find((x) => x.id === id);
    if (!s) return;
    setText(s.text);
    setCaller(s.caller);
    setResult(null);
    setError(null);
    setLog([]);
  }

  async function runScan() {
    if (!text.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setLog([]);

    const push = (e: StepEvent) => setLog((prev) => [...prev, e]);

    try {
      const data = await scanWithX402(text, service, caller, push);
      setResult(data.result);
    } catch (err) {
      setError(
        "Could not reach the backend. Is it running on http://localhost:8000 ?"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-8">
      {/* header */}
      <header className="mb-8">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/15 text-xl">
            🛡️
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">LifeOps</h1>
            <p className="text-sm text-gray-400">
              Paste your document, save your money.
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2 text-xs">
            <span className="rounded-full border border-edge bg-panel px-3 py-1 font-mono text-gray-400">
              x402 / A2MCP
            </span>
            <span className="rounded-full border border-ok/40 bg-ok/10 px-3 py-1 font-mono text-ok">
              guaranteed JSON + .ics
            </span>
          </div>
        </div>
      </header>

      {/* split screen */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* LEFT: input + result */}
        <section className="space-y-4">
          <div className="rounded-xl border border-edge bg-panel p-4">
            <div className="mb-3 flex flex-wrap gap-2">
              {SAMPLES.map((s) => (
                <button
                  key={s.id}
                  onClick={() => loadSample(s.id)}
                  className="rounded-lg border border-edge bg-black/30 px-3 py-1.5 text-sm text-gray-300 transition hover:border-accent/50 hover:text-white"
                >
                  {s.label}
                </button>
              ))}
            </div>

            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste any life document: a passport, warranty, bill, subscription email…"
              className="h-40 w-full resize-none rounded-lg border border-edge bg-black/40 p-3 font-mono text-sm text-gray-200 outline-none focus:border-accent/60"
            />

            <div className="mt-3 flex items-center gap-3">
              <span className="font-mono text-xs text-gray-500">
                caller: {caller}
              </span>
              <button
                onClick={runScan}
                disabled={loading || !text.trim()}
                className="ml-auto rounded-lg bg-accent px-5 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {loading ? "Processing…" : "Scan & Settle (0.05 USDT)"}
              </button>
            </div>
          </div>

          {error && (
            <div className="rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger">
              {error}
            </div>
          )}

          {result ? (
            <ResultView result={result} />
          ) : (
            <div className="rounded-xl border border-dashed border-edge p-10 text-center text-sm text-gray-600">
              The guaranteed JSON result — deadline, money at risk, action steps
              and a downloadable .ics — appears here.
            </div>
          )}
        </section>

        {/* RIGHT: live tx terminal */}
        <section className="lg:sticky lg:top-8 lg:h-[calc(100vh-8rem)]">
          <TxTerminal log={log} />
        </section>
      </div>
    </main>
  );
}

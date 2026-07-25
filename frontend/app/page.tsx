"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import {
  Activity,
  ArrowDown,
  ArrowRight,
  Bot,
  CalendarCheck,
  Check,
  FileSearch,
  Fingerprint,
  Layers3,
  LockKeyhole,
  ScanLine,
  Sparkles,
  UserRound,
  WalletCards,
} from "lucide-react";
import { SAMPLES } from "@/lib/samples";
import { scanPreview, type StepEvent } from "@/lib/api";
import type { LifeOpsResult, Service } from "@/lib/types";
import TxTerminal from "@/components/TxTerminal";
import ResultView from "@/components/ResultView";

const SERVICES: Array<{
  id: Service;
  label: string;
  detail: string;
  price: string;
}> = [
  { id: "scan", label: "Scan", detail: "Deadline + risk", price: "0.01" },
  { id: "full_action_pack", label: "Action pack", detail: "Plan + calendar", price: "0.05" },
  { id: "multi_audit", label: "Life audit", detail: "Multiple documents", price: "0.20" },
];

const PROOF = [
  { value: "x402 v2", label: "Verified settlement" },
  { value: "X Layer", label: "Live on mainnet" },
  { value: "< 1 call", label: "Document to action" },
  { value: "0 storage", label: "Transient processing" },
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
  const [entered, setEntered] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setEntered(true), 120);
    return () => window.clearTimeout(timer);
  }, []);

  function openWorkspace() {
    document.getElementById("workspace")?.scrollIntoView({ behavior: "smooth" });
  }

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
      window.setTimeout(() => {
        document.getElementById("analysis-result")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 120);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Request failed";
      setError(message);
      push({ kind: "error", text: message });
    } finally {
      setLoading(false);
    }
  }

  const selectedService = SERVICES.find((item) => item.id === service) ?? SERVICES[1];

  return (
    <main className="site-shell">
      <nav className="site-nav" aria-label="Primary navigation">
        <div className="nav-inner">
          <a href="#top" className="brand-link" aria-label="LifeOps home">
            <Image
              src="/lifeops-symbol.png"
              alt=""
              width={380}
              height={380}
              priority
              className="brand-symbol"
            />
            <span>LifeOps</span>
          </a>
          <div className="nav-proof">
            <span className="live-dot" aria-hidden="true" />
            Live on X Layer
          </div>
          <button type="button" onClick={openWorkspace} className="nav-cta">
            Open workspace
            <ArrowRight size={15} aria-hidden="true" />
          </button>
        </div>
      </nav>

      <section id="top" className={`hero ${entered ? "hero-entered" : ""}`}>
        <div className="hero-grid" aria-hidden="true">
          <span /><span /><span /><span /><span />
        </div>
        <div className="hero-scan" aria-hidden="true" />

        <div className="hero-content">
          <div className="hero-kicker reveal-item">
            <Sparkles size={14} aria-hidden="true" />
            Lifestyle intelligence for agents and humans
          </div>

          <Image
            src="/lifeops-wordmark.png"
            alt="LifeOps"
            width={1100}
            height={460}
            priority
            className="hero-wordmark reveal-item"
          />

          <h1 className="sr-only">LifeOps</h1>
          <p className="hero-copy reveal-item">
            Your documents already know what happens next.
            <span> LifeOps turns that signal into a deadline, a risk, and a plan.</span>
          </p>

          <div className="hero-actions reveal-item">
            <button type="button" onClick={openWorkspace} className="primary-cta">
              Enter the workspace
              <ArrowDown size={17} aria-hidden="true" />
            </button>
            <a href="https://www.okx.ai/agents/9204" target="_blank" rel="noreferrer" className="secondary-cta">
              View agent #9204
              <ArrowRight size={15} aria-hidden="true" />
            </a>
          </div>
        </div>

        <div className="hero-stage reveal-item" aria-label="LifeOps product preview">
          <div className="stage-rail">
            <div className="stage-window-dots"><span /><span /><span /></div>
            <span className="stage-route">lifeops / document intelligence</span>
            <span className="stage-secure"><LockKeyhole size={12} /> transient</span>
          </div>
          <div className="stage-body">
            <div className="stage-document">
              <span className="micro-label">INCOMING DOCUMENT</span>
              <p>Passport expires 05 Nov 2026.</p>
              <p>Planned travel: Schengen, 20 Oct.</p>
              <div className="document-line"><span /><span /><span /></div>
            </div>
            <ArrowRight className="stage-arrow" size={20} aria-hidden="true" />
            <div className="stage-outcome">
              <div><span className="micro-label">MONEY AT RISK</span><strong>$300</strong></div>
              <div><span className="micro-label">ACT BY</span><strong>21 Aug</strong></div>
              <div><span className="micro-label">EVIDENCE</span><strong>2 sources</strong></div>
            </div>
            <div className="stage-verified"><Check size={14} /> Evidence verified</div>
          </div>
        </div>

        <button type="button" onClick={openWorkspace} className="scroll-cue" title="Scroll to workspace">
          <ArrowDown size={16} aria-hidden="true" />
          <span className="sr-only">Scroll to workspace</span>
        </button>
      </section>

      <section className="proof-band" aria-label="Platform proof">
        <div className="proof-inner">
          {PROOF.map((item) => (
            <div key={item.value} className="proof-item">
              <strong>{item.value}</strong>
              <span>{item.label}</span>
            </div>
          ))}
        </div>
      </section>

      <section id="workspace" className="workspace-section">
        <div className="workspace-heading">
          <div>
            <span className="section-index">01 / WORKSPACE</span>
            <h2>Turn paperwork into leverage.</h2>
          </div>
          <p>Paste the document. LifeOps surfaces what matters, what it could cost, and what to do next.</p>
        </div>

        <div className="workspace-grid">
          <section className="input-panel" aria-label="Document analysis">
            <div className="panel-heading">
              <div>
                <span className="panel-eyebrow"><FileSearch size={14} /> Document intake</span>
                <h3>What needs your attention?</h3>
              </div>
              <label className="sample-control">
                <span>Sample</span>
                <select defaultValue="" onChange={(event) => loadSample(event.target.value)}>
                  <option value="" disabled>Choose a document</option>
                  {SAMPLES.map((sample) => (
                    <option key={sample.id} value={sample.id}>{sample.label}</option>
                  ))}
                </select>
              </label>
            </div>

            <div className="document-field">
              <div className="field-gutter" aria-hidden="true">01<br />02<br />03<br />04<br />05</div>
              <textarea
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="Paste a passport, warranty, subscription notice, bill, or appointment text..."
                maxLength={50000}
                aria-label="Document text"
              />
              <ScanLine className={`field-scan ${loading ? "is-scanning" : ""}`} size={19} aria-hidden="true" />
            </div>

            <div className="service-label-row">
              <span>Choose intelligence depth</span>
              <span>{text.length.toLocaleString()} / 50,000</span>
            </div>
            <div className="service-selector" role="group" aria-label="Service level">
              {SERVICES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setService(item.id)}
                  aria-pressed={service === item.id}
                  className={service === item.id ? "selected" : ""}
                >
                  <span className="service-radio"><span /></span>
                  <span className="service-name">{item.label}</span>
                  <span className="service-detail">{item.detail}</span>
                  <span className="service-price">{item.price}<small> USDT0</small></span>
                </button>
              ))}
            </div>

            <div className="run-row">
              <div className="caller-id">
                {caller.toLowerCase().includes("agent") ? <Bot size={16} /> : <UserRound size={16} />}
                <div><span>Caller</span><strong>{caller}</strong></div>
              </div>
              <div className="privacy-note"><Fingerprint size={15} /> Processed transiently</div>
              <button type="button" onClick={runScan} disabled={loading || !text.trim()} className="run-button">
                <span>{loading ? "Reading signals" : `Run ${selectedService.label}`}</span>
                {loading ? <span className="button-loader" /> : <ArrowRight size={17} />}
              </button>
            </div>
          </section>

          <aside className="activity-panel" aria-label="x402 activity">
            <TxTerminal log={log} />
          </aside>
        </div>

        {error && <div role="alert" className="error-banner">{error}</div>}

        <div id="analysis-result" className="result-anchor">
          {result ? (
            <ResultView result={result} icsUrl={icsUrl} />
          ) : (
            <div className="empty-result">
              <div className="empty-visual" aria-hidden="true">
                <CalendarCheck size={28} />
                <span className="empty-pulse" />
              </div>
              <div>
                <span className="section-index">02 / INTELLIGENCE</span>
                <h3>Your action plan will appear here.</h3>
                <p>Load a sample or paste a real document to reveal deadlines, evidence, money at risk, and calendar-ready actions.</p>
              </div>
              <div className="empty-capabilities">
                <span><WalletCards size={14} /> Financial exposure</span>
                <span><Layers3 size={14} /> Multi-document audit</span>
                <span><Activity size={14} /> Source evidence</span>
              </div>
            </div>
          )}
        </div>
      </section>

      <footer className="site-footer">
        <div className="footer-inner">
          <a href="#top" className="footer-brand" aria-label="LifeOps home">
            <Image src="/lifeops-symbol.png" alt="" width={380} height={380} />
            <span>LifeOps</span>
          </a>
          <p>Personal deadline intelligence. Built for the OKX.AI agent economy.</p>
          <div className="footer-status"><span className="live-dot" /> API ready</div>
        </div>
      </footer>
    </main>
  );
}

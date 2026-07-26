"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import {
  Activity,
  ArrowDown,
  ArrowRight,
  Bot,
  CalendarCheck,
  ChevronDown,
  Check,
  CircleCheck,
  FileText,
  FileSearch,
  Fingerprint,
  Layers3,
  LockKeyhole,
  ScanLine,
  ShieldCheck,
  Sparkles,
  UserRound,
  Wallet,
  WalletCards,
  X,
} from "lucide-react";
import { SAMPLES } from "@/lib/samples";
import { paymentQuote, scanPreview, verifiedScan, type StepEvent } from "@/lib/api";
import type { LifeOpsResult, PaymentRequirements, Service, SettlementReceipt } from "@/lib/types";
import {
  connectOkxWallet,
  connectedOkxAccount,
  shortAddress,
  walletErrorMessage,
  type InjectedProvider,
} from "@/lib/wallet";
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

interface PaymentReview {
  requirement: PaymentRequirements;
  address: `0x${string}`;
  provider: InjectedProvider;
}

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
  const [sampleId, setSampleId] = useState("");
  const [processingStep, setProcessingStep] = useState(0);
  const [walletAddress, setWalletAddress] = useState<`0x${string}` | null>(null);
  const [paymentReview, setPaymentReview] = useState<PaymentReview | null>(null);
  const [preparingPayment, setPreparingPayment] = useState(false);
  const [runMode, setRunMode] = useState<"preview" | "verified">("preview");
  const [settlement, setSettlement] = useState<SettlementReceipt | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setEntered(true), 120);
    connectedOkxAccount().then(setWalletAddress).catch(() => undefined);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!loading) return;
    setProcessingStep(0);
    const timers = [
      window.setTimeout(() => setProcessingStep(1), 700),
      window.setTimeout(() => setProcessingStep(2), 1450),
      window.setTimeout(() => setProcessingStep(3), 2750),
    ];
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [loading]);

  function openWorkspace() {
    document.getElementById("workspace")?.scrollIntoView({ behavior: "smooth" });
  }

  function loadSample(id: string) {
    const sample = SAMPLES.find((item) => item.id === id);
    if (!sample) return;
    setSampleId(id);
    setText(sample.text);
    setCaller(sample.caller);
    setService(sample.service);
    setResult(null);
    setIcsUrl(null);
    setError(null);
    setLog([]);
    setSettlement(null);
  }

  async function connectWalletOnly() {
    try {
      setError(null);
      const connection = await connectOkxWallet();
      setWalletAddress(connection.address);
    } catch (caught) {
      setError(walletErrorMessage(caught));
    }
  }

  async function prepareVerifiedRun() {
    if (!text.trim() || loading || preparingPayment) return;
    setPreparingPayment(true);
    setError(null);
    try {
      const connection = await connectOkxWallet();
      setWalletAddress(connection.address);
      const requirement = await paymentQuote(text, service, caller);
      setPaymentReview({ requirement, address: connection.address, provider: connection.provider });
    } catch (caught) {
      // Surface the real server/quote error (e.g. invalid payTo) instead of a
      // generic wallet message so misconfigured payment terms are visible.
      const message = caught instanceof Error ? caught.message : walletErrorMessage(caught);
      setError(message);
    } finally {
      setPreparingPayment(false);
    }
  }

  async function runScan(approved?: PaymentReview) {
    if (!text.trim() || loading) return;
    const startedAt = performance.now();
    const mode = approved ? "verified" : "preview";
    setRunMode(mode);
    setLoading(true);
    setError(null);
    setResult(null);
    setIcsUrl(null);
    setLog([]);
    setSettlement(null);
    let visualEventIndex = 0;
    const push = (event: StepEvent) => {
      const delay = visualEventIndex * 300;
      visualEventIndex += 1;
      window.setTimeout(() => setLog((previous) => [...previous, event]), delay);
    };

    window.setTimeout(() => {
      document.getElementById("protocol-proof")?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 80);
    window.setTimeout(() => {
      document.getElementById("analysis-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 1650);

    try {
      const data = approved
        ? await verifiedScan(
            text,
            service,
            caller,
            approved.requirement,
            approved.provider,
            approved.address,
            push
          )
        : await scanPreview(text, service, caller, push);
      const remainingDisplayTime = Math.max(0, 4200 - (performance.now() - startedAt));
      if (remainingDisplayTime > 0) {
        await new Promise((resolve) => window.setTimeout(resolve, remainingDisplayTime));
      }
      setResult(data.result);
      setIcsUrl(data.ics_url);
      if ("settlement" in data) setSettlement(data.settlement);
    } catch (caught) {
      const message = approved ? walletErrorMessage(caught) : caught instanceof Error ? caught.message : "Request failed";
      setError(message);
      push({ kind: "error", text: message });
    } finally {
      setLoading(false);
    }
  }

  const selectedService = SERVICES.find((item) => item.id === service) ?? SERVICES[1];
  const approvedAmount = paymentReview ? Number(paymentReview.requirement.amount) / 1e6 : 0;

  return (
    <main className="site-shell">
      {paymentReview && (
        <div className="payment-overlay" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setPaymentReview(null);
        }}>
          <section className="payment-dialog" role="dialog" aria-modal="true" aria-labelledby="payment-title">
            <header className="payment-dialog-header">
              <div className="payment-dialog-mark"><ShieldCheck size={19} /></div>
              <div>
                <span className="section-index">VERIFIED EXECUTION</span>
                <h2 id="payment-title">Authorize one settled run</h2>
              </div>
              <button type="button" onClick={() => setPaymentReview(null)} className="dialog-close" title="Close payment review">
                <X size={17} />
                <span className="sr-only">Close payment review</span>
              </button>
            </header>

            <div className="payment-amount">
              <span>EXACT CHARGE</span>
              <strong>{approvedAmount.toFixed(2)} <small>USDT0</small></strong>
              <p>{paymentReview.requirement.amount} atomic units</p>
            </div>

            <dl className="payment-terms">
              <div><dt>Network</dt><dd><span className="live-dot" /> X Layer mainnet</dd></div>
              <div><dt>Service</dt><dd>{selectedService.label}</dd></div>
              <div><dt>Wallet</dt><dd>{shortAddress(paymentReview.address)}</dd></div>
              <div><dt>Recipient</dt><dd title={paymentReview.requirement.payTo}>{paymentReview.requirement.payTo}</dd></div>
            </dl>

            <div className="payment-truth">
              <LockKeyhole size={16} />
              <p>OKX Wallet will sign this exact USDT0 authorization. LifeOps releases the result only after settlement succeeds.</p>
            </div>

            <footer className="payment-actions">
              <button type="button" onClick={() => setPaymentReview(null)} className="payment-cancel">Cancel</button>
              <button type="button" onClick={() => {
                const approved = paymentReview;
                setPaymentReview(null);
                void runScan(approved);
              }} className="payment-confirm">
                <Wallet size={16} />
                Sign &amp; pay {approvedAmount.toFixed(2)} USDT0
              </button>
            </footer>
          </section>
        </div>
      )}
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
                <span className="sample-label">Example document</span>
                <span className="sample-select-shell">
                  <FileText size={17} aria-hidden="true" />
                  <select value={sampleId} onChange={(event) => loadSample(event.target.value)}>
                  <option value="" disabled>Choose a document</option>
                  {SAMPLES.map((sample) => (
                    <option key={sample.id} value={sample.id}>{sample.label}</option>
                  ))}
                  </select>
                  <ChevronDown size={17} aria-hidden="true" />
                </span>
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
              <div className="run-controls">
                <button type="button" onClick={connectWalletOnly} className={`wallet-button ${walletAddress ? "connected" : ""}`}>
                  <Wallet size={15} />
                  <span>{walletAddress ? shortAddress(walletAddress) : "Connect OKX"}</span>
                </button>
                <div className="run-actions">
                  <button type="button" onClick={() => runScan()} disabled={loading || preparingPayment || !text.trim()} className="preview-button">
                    <ScanLine size={16} />
                    <span>{loading && runMode === "preview" ? "Reading" : "Preview"}</span>
                  </button>
                  <button type="button" onClick={prepareVerifiedRun} disabled={loading || preparingPayment || !text.trim()} className="run-button verified-button">
                    <span>{preparingPayment ? "Preparing quote" : loading && runMode === "verified" ? "Settling" : "Verified run"}</span>
                    {loading || preparingPayment ? <span className="button-loader" /> : <ShieldCheck size={17} />}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <aside
            id="protocol-proof"
            className={`activity-panel ${loading ? "is-focused" : ""}`}
            aria-label="x402 activity"
            aria-busy={loading}
          >
            <TxTerminal log={log} loading={loading} />
          </aside>
        </div>

        {error && <div role="alert" className="error-banner">{error}</div>}

        <div id="analysis-result" className="result-anchor">
          {loading ? (
            <ProcessingView step={processingStep} service={selectedService.label} mode={runMode} />
          ) : result ? (
            <ResultView result={result} icsUrl={icsUrl} settlement={settlement} />
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

const PROCESSING_STEPS = [
  "Reading document structure",
  "Mapping dates and obligations",
  "Checking financial exposure",
  "Building your action plan",
];

function ProcessingView({ step, service, mode }: { step: number; service: string; mode: "preview" | "verified" }) {
  const progress = [18, 42, 68, 88][step] ?? 18;

  return (
    <section className="processing-view" role="status" aria-live="polite">
      <div className="processing-orbit" aria-hidden="true">
        <span className="orbit-ring orbit-ring-one" />
        <span className="orbit-ring orbit-ring-two" />
        <span className="processing-core"><ScanLine size={24} /></span>
      </div>
      <div className="processing-copy">
        <span className="section-index">02 / INTELLIGENCE</span>
        <h3>{mode === "verified" ? "LifeOps is settling the run." : "LifeOps is reading the signals."}</h3>
        <p>{PROCESSING_STEPS[step]}</p>
        <div className="processing-meter" aria-hidden="true"><span style={{ width: `${progress}%` }} /></div>
        <div className="processing-meta"><span>{progress}%</span><span>{service}</span><span>{mode === "verified" ? "Verified settlement" : "Free preview"}</span></div>
      </div>
      <ol className="processing-steps">
        {PROCESSING_STEPS.map((label, index) => (
          <li key={label} className={index < step ? "done" : index === step ? "active" : ""}>
            <span>{index < step ? <CircleCheck size={15} /> : String(index + 1).padStart(2, "0")}</span>
            <strong>{label}</strong>
          </li>
        ))}
      </ol>
    </section>
  );
}

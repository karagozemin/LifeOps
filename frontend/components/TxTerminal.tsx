"use client";

import { useEffect, useRef, useState } from "react";
import { Activity, ArrowUpRight, CheckCircle2, Radio, ReceiptText, ShieldCheck } from "lucide-react";
import { recentTransactions, type StepEvent } from "@/lib/api";
import type { PaymentTx } from "@/lib/types";

export default function TxTerminal({ log }: { log: StepEvent[] }) {
  const traceRef = useRef<HTMLDivElement>(null);
  const [transactions, setTransactions] = useState<PaymentTx[]>([]);

  useEffect(() => {
    if (log.length === 0 || !traceRef.current) return;
    traceRef.current.scrollTo({ top: traceRef.current.scrollHeight, behavior: "smooth" });
  }, [log]);

  useEffect(() => {
    let active = true;
    const refresh = () => recentTransactions().then((items) => active && setTransactions(items)).catch(() => undefined);
    refresh();
    const timer = window.setInterval(refresh, 8000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  return (
    <div className="terminal-shell">
      <header className="terminal-header">
        <div><Activity size={16} /><span>Protocol proof</span></div>
        <span className="terminal-live"><Radio size={12} /> LIVE</span>
      </header>

      <div className="protocol-stack" aria-label="Protocol status">
        <Protocol icon={ShieldCheck} title="Challenge" value="x402 v2" />
        <Protocol icon={CheckCircle2} title="Network" value="X Layer" />
        <Protocol icon={ReceiptText} title="Asset" value="USDT0" />
      </div>

      <section className="trace-section" aria-label="Request trace">
        <div className="terminal-section-title"><span>REQUEST TRACE</span><span>POST /scan</span></div>
        <div ref={traceRef} className="trace-log">
          {log.length === 0 ? (
            <div className="awaiting-trace"><span className="trace-cursor" />Awaiting document signal</div>
          ) : (
            log.map((event, index) => (
              <div key={`${index}-${event.text}`} className={`trace-row trace-${event.kind}`}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <p>{event.text}</p>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="settlement-section" aria-label="Real settlements">
        <div className="terminal-section-title"><span>REAL SETTLEMENTS</span><span>{String(transactions.length).padStart(2, "0")}</span></div>
        <div className="settlement-list">
          {transactions.length === 0 ? (
            <div className="empty-settlement"><ReceiptText size={18} /><span>No settled payments in this feed</span></div>
          ) : transactions.map((transaction) => (
            <article key={transaction.tx_hash}>
              <div className="settlement-main">
                <span className="settlement-mark"><CheckCircle2 size={14} /></span>
                <div><strong>{transaction.service}</strong><small>{transaction.chain} · verified</small></div>
                <b>+{transaction.amount} {transaction.asset}</b>
              </div>
              <a href={`https://www.oklink.com/x-layer/tx/${transaction.tx_hash}`} target="_blank" rel="noreferrer" title="Open transaction in OKLink">
                {transaction.tx_hash.slice(0, 10)}...{transaction.tx_hash.slice(-6)}
                <ArrowUpRight size={12} />
              </a>
            </article>
          ))}
        </div>
      </section>

      <footer className="terminal-footer"><span className="live-dot" /> Production endpoint · cryptographic receipts only</footer>
    </div>
  );
}

function Protocol({ icon: Icon, title, value }: { icon: typeof ShieldCheck; title: string; value: string }) {
  return <div><Icon size={14} /><span>{title}</span><strong>{value}</strong></div>;
}

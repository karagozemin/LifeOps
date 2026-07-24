"use client";

import { useEffect, useRef, useState } from "react";
import { Activity, ExternalLink, Radio, ReceiptText } from "lucide-react";
import { recentTransactions, type StepEvent } from "@/lib/api";
import type { PaymentTx } from "@/lib/types";

const COLORS: Record<StepEvent["kind"], string> = {
  info: "text-gray-400",
  http: "text-warn",
  tx: "text-accent",
  ok: "text-ok",
  error: "text-danger",
};

export default function TxTerminal({ log }: { log: StepEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  const [transactions, setTransactions] = useState<PaymentTx[]>([]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [log]);

  useEffect(() => {
    let active = true;
    const refresh = () => recentTransactions().then((items) => active && setTransactions(items)).catch(() => undefined);
    refresh();
    const timer = window.setInterval(refresh, 8000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <div className="flex h-full min-h-[560px] flex-col overflow-hidden rounded-lg border border-edge bg-panel">
      <div className="flex items-center gap-2 border-b border-edge px-4 py-3">
        <Activity size={17} className="text-accent" aria-hidden="true" />
        <h2 className="text-sm font-medium text-white">Protocol activity</h2>
        <span className="ml-auto inline-flex items-center gap-1.5 text-xs text-ok">
          <Radio size={13} aria-hidden="true" /> Live
        </span>
      </div>

      <section className="min-h-0 flex-1 border-b border-edge" aria-label="Request trace">
        <div className="flex items-center gap-2 px-4 py-3 text-xs text-muted">
          <span>Request trace</span>
          <span className="ml-auto font-mono">/scan</span>
        </div>
        <div className="h-[250px] overflow-y-auto px-4 pb-4 font-mono text-xs leading-6">
          {log.length === 0 ? (
            <p className="text-gray-600">Awaiting request</p>
          ) : (
            log.map((event, index) => (
              <div key={`${index}-${event.text}`} className={`${COLORS[event.kind]} grid grid-cols-[18px_1fr] gap-1`}>
                <span className="select-none opacity-50">{String(index + 1).padStart(2, "0")}</span>
                <span className="break-words">{event.text}</span>
              </div>
            ))
          )}
          <div ref={endRef} />
        </div>
      </section>

      <section className="min-h-0 flex-1" aria-label="Real settlements">
        <div className="flex items-center gap-2 px-4 py-3 text-xs text-muted">
          <ReceiptText size={14} aria-hidden="true" />
          <span>Real settlements</span>
          <span className="ml-auto font-mono">{transactions.length}</span>
        </div>
        <div className="h-[250px] overflow-y-auto px-4 pb-4">
          {transactions.length === 0 ? (
            <p className="font-mono text-xs text-gray-600">No settled payments</p>
          ) : (
            <div className="divide-y divide-edge">
              {transactions.map((transaction) => (
                <div key={transaction.tx_hash} className="py-3 text-xs">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-white">{transaction.service}</span>
                    <span className="font-mono text-ok">+{transaction.amount} {transaction.asset}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-muted">
                    <span className="font-mono">{transaction.chain}</span>
                    <a
                      href={`https://www.oklink.com/x-layer/tx/${transaction.tx_hash}`}
                      target="_blank"
                      rel="noreferrer"
                      title="Open transaction in OKLink"
                      className="ml-auto inline-flex items-center gap-1 font-mono text-gray-400 hover:text-white"
                    >
                      {transaction.tx_hash.slice(0, 8)}...{transaction.tx_hash.slice(-6)}
                      <ExternalLink size={12} aria-hidden="true" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

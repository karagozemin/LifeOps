"use client";

import { useEffect, useRef } from "react";
import type { StepEvent } from "@/lib/api";

const COLORS: Record<StepEvent["kind"], string> = {
  info: "text-gray-400",
  http: "text-warn",
  tx: "text-accent",
  ok: "text-ok",
  error: "text-danger",
};

const PREFIX: Record<StepEvent["kind"], string> = {
  info: "·",
  http: "»",
  tx: "$",
  ok: "✓",
  error: "✗",
};

export default function TxTerminal({ log }: { log: StepEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [log]);

  return (
    <div className="flex h-full flex-col rounded-xl border border-edge bg-black/40">
      <div className="flex items-center gap-2 border-b border-edge px-4 py-2.5">
        <span className="h-3 w-3 rounded-full bg-danger/80" />
        <span className="h-3 w-3 rounded-full bg-warn/80" />
        <span className="h-3 w-3 rounded-full bg-ok/80" />
        <span className="ml-2 font-mono text-xs text-gray-500">
          x402 transaction log — live
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 font-mono text-[13px] leading-relaxed">
        {log.length === 0 ? (
          <p className="text-gray-600">
            Waiting for a scan… pick a sample and hit “Scan &amp; Settle”.
          </p>
        ) : (
          log.map((e, i) => (
            <div key={i} className={`${COLORS[e.kind]} flex gap-2`}>
              <span className="select-none opacity-60">{PREFIX[e.kind]}</span>
              <span className="break-all">{e.text}</span>
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}

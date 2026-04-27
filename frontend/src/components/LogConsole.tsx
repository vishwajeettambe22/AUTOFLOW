"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal, ChevronDown, ChevronUp } from "lucide-react";

interface Props {
  logs: string[];
}

export function LogConsole({ logs }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [isExpanded, setIsExpanded] = useState(true);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (logs.length === 0) return null;

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-primary)] overflow-hidden animate-fade-in">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-xs font-medium text-[var(--text-tertiary)]">
            Console
          </span>
          <span className="text-[10px] text-[var(--text-muted)] bg-[var(--bg-tertiary)] px-1.5 py-0.5 rounded">
            {logs.length}
          </span>
        </div>
        {isExpanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-[var(--text-muted)]" />
        ) : (
          <ChevronUp className="w-3.5 h-3.5 text-[var(--text-muted)]" />
        )}
      </button>

      {/* Logs */}
      {isExpanded && (
        <div className="p-3 font-mono text-xs max-h-44 overflow-y-auto">
          {logs.map((log, i) => (
            <div
              key={i}
              className="leading-6 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors"
            >
              <span className="text-[var(--text-muted)] select-none mr-2">
                ›
              </span>
              <span
                className={
                  log.includes("✓")
                    ? "text-emerald-400"
                    : log.includes("✗")
                    ? "text-red-400"
                    : log.includes("⚡")
                    ? "text-blue-400"
                    : log.includes("▸")
                    ? "text-[var(--accent)]"
                    : ""
                }
              >
                {log}
              </span>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}

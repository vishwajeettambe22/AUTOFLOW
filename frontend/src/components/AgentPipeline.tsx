"use client";

import clsx from "clsx";
import { Search, FileText, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import type { AgentStatus } from "@/hooks/useAutoFlow";

/* Only the 2 agents that are active in the workflow */
const PIPELINE = [
  {
    id: "researcher",
    label: "Researcher",
    desc: "Gathers & analyzes data",
    Icon: Search,
  },
  {
    id: "reporter",
    label: "Reporter",
    desc: "Formats final report",
    Icon: FileText,
  },
];

interface Props {
  statuses: Record<string, AgentStatus>;
  outputs: Record<string, string>;
}

export function AgentPipeline({ statuses, outputs }: Props) {
  return (
    <div className="flex items-start gap-3">
      {PIPELINE.map((agent, i) => {
        const status = statuses[agent.id] || "pending";
        const isActive = status === "running";
        const isDone = status === "success";
        const isFailed = status === "failed";
        const output = outputs[agent.id];

        return (
          <div key={agent.id} className="flex items-center gap-3 flex-1">
            {/* Agent card */}
            <div
              className={clsx(
                "flex-1 rounded-xl border p-3.5 transition-all duration-500",
                isActive && "border-[var(--accent)] bg-[var(--accent-subtle)] animate-pulse-glow",
                isDone && "border-emerald-800 bg-emerald-950/30",
                isFailed && "border-red-900 bg-red-950/30",
                !isActive && !isDone && !isFailed && "border-[var(--border-subtle)] bg-[var(--bg-secondary)]"
              )}
            >
              <div className="flex items-center gap-2.5 mb-1">
                {/* Status indicator */}
                {isActive && (
                  <Loader2 className="w-4 h-4 text-[var(--accent)] animate-spin" />
                )}
                {isDone && (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                )}
                {isFailed && (
                  <XCircle className="w-4 h-4 text-red-400" />
                )}
                {!isActive && !isDone && !isFailed && (
                  <agent.Icon className="w-4 h-4 text-[var(--text-muted)]" />
                )}

                <span
                  className={clsx(
                    "text-sm font-medium",
                    isActive && "text-[var(--accent)]",
                    isDone && "text-emerald-300",
                    isFailed && "text-red-300",
                    !isActive && !isDone && !isFailed && "text-[var(--text-tertiary)]"
                  )}
                >
                  {agent.label}
                </span>
              </div>

              <p
                className={clsx(
                  "text-xs",
                  isActive
                    ? "text-[var(--accent)]"
                    : isDone
                    ? "text-emerald-400/60"
                    : "text-[var(--text-muted)]"
                )}
              >
                {isActive
                  ? "Processing..."
                  : isDone
                  ? "Complete"
                  : isFailed
                  ? "Failed"
                  : agent.desc}
              </p>

              {output && isDone && (
                <p className="text-xs text-[var(--text-tertiary)] mt-1.5 line-clamp-2">
                  {output}
                </p>
              )}
            </div>

            {/* Connector arrow */}
            {i < PIPELINE.length - 1 && (
              <div className="flex-shrink-0 flex items-center">
                <div
                  className={clsx(
                    "w-6 h-px transition-colors duration-500",
                    isDone ? "bg-emerald-600" : "bg-[var(--border-default)]"
                  )}
                />
                <div
                  className={clsx(
                    "w-0 h-0 border-y-[4px] border-y-transparent border-l-[6px] transition-colors duration-500",
                    isDone
                      ? "border-l-emerald-600"
                      : "border-l-[var(--border-default)]"
                  )}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

"use client";

import clsx from "clsx";
import type { AgentStatus } from "@/hooks/useAutoFlow";

const AGENTS = [
  { id: "planner", label: "Planner", icon: "P", desc: "Decomposes task" },
  { id: "researcher", label: "Researcher", icon: "R", desc: "Gathers info" },
  { id: "coder", label: "Coder", icon: "C", desc: "Generates output" },
  { id: "reviewer", label: "Reviewer", icon: "Rv", desc: "Validates quality" },
  { id: "critic", label: "Critic", icon: "Cr", desc: "Self-healing" },
  { id: "reporter", label: "Reporter", icon: "Rp", desc: "Final synthesis" },
];

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-800 border-gray-700 text-gray-500",
  running: "bg-blue-950 border-blue-500 text-blue-300 animate-pulse",
  success: "bg-emerald-950 border-emerald-500 text-emerald-300",
  failed: "bg-red-950 border-red-500 text-red-300",
  skipped: "bg-gray-800 border-gray-600 text-gray-500",
};

const STATUS_DOT: Record<string, string> = {
  pending: "bg-gray-600",
  running: "bg-blue-400 animate-ping",
  success: "bg-emerald-400",
  failed: "bg-red-400",
  skipped: "bg-gray-600",
};

interface Props {
  statuses: Record<string, AgentStatus>;
  outputs: Record<string, string>;
}

export function AgentDAG({ statuses, outputs }: Props) {
  return (
    <div className="space-y-2">
      {AGENTS.map((agent, i) => {
        const status = statuses[agent.id] || "pending";
        return (
          <div key={agent.id} className="relative">
            {/* Connector line */}
            {i > 0 && (
              <div className="absolute -top-2 left-6 w-px h-2 bg-gray-700" />
            )}
            <div
              className={clsx(
                "flex items-start gap-3 p-3 rounded-lg border transition-all duration-300",
                STATUS_STYLES[status]
              )}
            >
              {/* Status dot */}
              <div className="mt-0.5 relative flex-shrink-0">
                <div className={clsx("w-2 h-2 rounded-full", STATUS_DOT[status])} />
                {status === "running" && (
                  <div className="absolute inset-0 w-2 h-2 rounded-full bg-blue-400 opacity-50" />
                )}
              </div>

              {/* Agent icon */}
              <div className={clsx(
                "w-7 h-7 rounded-md flex items-center justify-center text-xs font-bold flex-shrink-0",
                status === "success" ? "bg-emerald-800 text-emerald-200" :
                status === "running" ? "bg-blue-800 text-blue-200" :
                status === "failed" ? "bg-red-800 text-red-200" :
                "bg-gray-700 text-gray-400"
              )}>
                {agent.icon}
              </div>

              {/* Label + output */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{agent.label}</span>
                  <span className="text-xs opacity-50">{agent.desc}</span>
                  {status === "running" && (
                    <span className="text-xs text-blue-400 ml-auto">running...</span>
                  )}
                  {status === "success" && (
                    <span className="text-xs text-emerald-500 ml-auto">done</span>
                  )}
                  {status === "failed" && (
                    <span className="text-xs text-red-400 ml-auto">failed</span>
                  )}
                </div>
                {outputs[agent.id] && (
                  <p className="text-xs mt-1 opacity-60 truncate">
                    {outputs[agent.id]}
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

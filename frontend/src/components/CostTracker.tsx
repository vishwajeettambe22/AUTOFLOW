"use client";

import { Coins, ArrowUpRight, ArrowDownRight, Zap } from "lucide-react";
import type { TokenUsage } from "@/hooks/useAutoFlow";

interface Props {
  usage: TokenUsage[];
  totalCost: number;
}

export function CostTracker({ usage, totalCost }: Props) {
  if (usage.length === 0) return null;

  const totalInput = usage.reduce((s, u) => s + u.input_tokens, 0);
  const totalOutput = usage.reduce((s, u) => s + u.output_tokens, 0);

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Coins className="w-3.5 h-3.5 text-[var(--accent)]" />
          <span className="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">
            Usage
          </span>
        </div>
        <span className="text-sm font-semibold text-[var(--accent)] font-mono">
          ${totalCost.toFixed(5)}
        </span>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-[var(--bg-tertiary)] rounded-lg p-2.5 text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <ArrowUpRight className="w-3 h-3 text-blue-400" />
            <span className="text-[10px] text-[var(--text-muted)] uppercase">
              Input
            </span>
          </div>
          <div className="text-sm font-mono text-[var(--text-primary)]">
            {totalInput.toLocaleString()}
          </div>
        </div>
        <div className="bg-[var(--bg-tertiary)] rounded-lg p-2.5 text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <ArrowDownRight className="w-3 h-3 text-emerald-400" />
            <span className="text-[10px] text-[var(--text-muted)] uppercase">
              Output
            </span>
          </div>
          <div className="text-sm font-mono text-[var(--text-primary)]">
            {totalOutput.toLocaleString()}
          </div>
        </div>
        <div className="bg-[var(--bg-tertiary)] rounded-lg p-2.5 text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <Zap className="w-3 h-3 text-amber-400" />
            <span className="text-[10px] text-[var(--text-muted)] uppercase">
              Calls
            </span>
          </div>
          <div className="text-sm font-mono text-[var(--text-primary)]">
            {usage.length}
          </div>
        </div>
      </div>

      {/* Per-agent breakdown */}
      <div className="space-y-1.5">
        {usage.map((u, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-20 text-[var(--text-tertiary)] capitalize truncate">
              {u.agent}
            </span>
            <div className="flex-1 bg-[var(--bg-tertiary)] rounded-full h-1 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[var(--accent)] to-amber-600 transition-all duration-700"
                style={{
                  width: `${Math.min(
                    100,
                    (u.cost_usd / (totalCost || 0.001)) * 100
                  )}%`,
                }}
              />
            </div>
            <span className="text-[var(--text-tertiary)] font-mono w-16 text-right">
              ${u.cost_usd.toFixed(5)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

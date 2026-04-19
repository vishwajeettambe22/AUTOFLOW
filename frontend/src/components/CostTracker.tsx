"use client";

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
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
          Token Usage
        </span>
        <span className="text-sm font-semibold text-amber-400">
          ${totalCost.toFixed(5)}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-gray-800 rounded p-2">
          <div className="text-xs text-gray-500">Input</div>
          <div className="text-sm font-mono text-gray-200">{totalInput.toLocaleString()}</div>
        </div>
        <div className="bg-gray-800 rounded p-2">
          <div className="text-xs text-gray-500">Output</div>
          <div className="text-sm font-mono text-gray-200">{totalOutput.toLocaleString()}</div>
        </div>
        <div className="bg-gray-800 rounded p-2">
          <div className="text-xs text-gray-500">Calls</div>
          <div className="text-sm font-mono text-gray-200">{usage.length}</div>
        </div>
      </div>

      <div className="space-y-1">
        {usage.map((u, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-20 text-gray-500 truncate">{u.agent}</span>
            <div className="flex-1 bg-gray-800 rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full bg-amber-600 rounded-full"
                style={{ width: `${Math.min(100, (u.cost_usd / (totalCost || 0.001)) * 100)}%` }}
              />
            </div>
            <span className="text-gray-400 font-mono w-16 text-right">
              ${u.cost_usd.toFixed(5)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

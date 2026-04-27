"use client";

import { useEffect } from "react";
import {
  Plus,
  Clock,
  CheckCircle2,
  XCircle,
  Workflow,
} from "lucide-react";
import clsx from "clsx";
import type { HistoryRun } from "@/hooks/useAutoFlow";

interface Props {
  history: HistoryRun[];
  activeRunId: string | null;
  onNewTask: () => void;
  onSelectRun: (runId: string) => void;
  onRefresh: () => void;
}

export function Sidebar({
  history,
  activeRunId,
  onNewTask,
  onSelectRun,
  onRefresh,
}: Props) {
  useEffect(() => {
    onRefresh();
  }, [onRefresh]);

  return (
    <aside className="w-64 h-screen flex flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-[var(--border-subtle)]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--accent)] to-amber-700 flex items-center justify-center">
            <Workflow className="w-3.5 h-3.5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-[var(--text-primary)]">
              AutoFlow
            </h1>
            <p className="text-[10px] text-[var(--text-muted)]">
              AI Research Agent
            </p>
          </div>
        </div>
      </div>

      {/* New task button */}
      <div className="p-3">
        <button
          onClick={onNewTask}
          className={clsx(
            "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm",
            "border border-[var(--border-default)] hover:border-[var(--border-active)]",
            "bg-[var(--bg-tertiary)] hover:bg-[var(--bg-hover)]",
            "text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
            "transition-all duration-200"
          )}
        >
          <Plus className="w-4 h-4" />
          New Task
        </button>
      </div>

      {/* History */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {history.length > 0 && (
          <div className="mb-2 px-2">
            <span className="text-[10px] font-medium text-[var(--text-muted)] uppercase tracking-wider">
              Recent
            </span>
          </div>
        )}

        <div className="space-y-0.5">
          {history.map((run) => {
            const isActive = run.run_id === activeRunId;
            const isSuccess = run.status === "success";

            return (
              <button
                key={run.run_id}
                onClick={() => onSelectRun(run.run_id)}
                className={clsx(
                  "w-full text-left px-3 py-2 rounded-lg text-xs transition-all duration-150 group",
                  isActive
                    ? "bg-[var(--bg-hover)] text-[var(--text-primary)]"
                    : "text-[var(--text-tertiary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-secondary)]"
                )}
              >
                <div className="flex items-start gap-2">
                  {isSuccess ? (
                    <CheckCircle2 className="w-3 h-3 text-emerald-500 mt-0.5 flex-shrink-0" />
                  ) : (
                    <XCircle className="w-3 h-3 text-red-500 mt-0.5 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="truncate leading-snug">
                      {run.user_task}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Clock className="w-2.5 h-2.5 text-[var(--text-muted)]" />
                      <span className="text-[10px] text-[var(--text-muted)]">
                        {run.created_at
                          ? new Date(run.created_at).toLocaleDateString(
                              "en-US",
                              {
                                month: "short",
                                day: "numeric",
                              }
                            )
                          : "—"}
                      </span>
                      {run.total_cost_usd > 0 && (
                        <span className="text-[10px] text-[var(--text-muted)] font-mono">
                          ${run.total_cost_usd.toFixed(4)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {history.length === 0 && (
          <div className="px-3 py-8 text-center">
            <p className="text-xs text-[var(--text-muted)]">
              No runs yet.
            </p>
            <p className="text-[10px] text-[var(--text-muted)] mt-1">
              Start a task to see history here.
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}

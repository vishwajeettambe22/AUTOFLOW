"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Sparkles,
  Copy,
  Check,
  RotateCcw,
  AlertCircle,
} from "lucide-react";
import clsx from "clsx";
import { useAutoFlow } from "@/hooks/useAutoFlow";
import { Sidebar } from "@/components/Sidebar";
import { AgentPipeline } from "@/components/AgentPipeline";
import { CostTracker } from "@/components/CostTracker";
import { LogConsole } from "@/components/LogConsole";
import { MarkdownOutput } from "@/components/MarkdownOutput";

const EXAMPLE_TASKS = [
  "Research top 3 Python web frameworks and write a comparison report",
  "Explain how transformers work in AI with architecture details",
  "Compare React, Vue, and Svelte for a startup tech stack",
  "Analyze the latest trends in AI agents and autonomous systems",
];

export default function HomePage() {
  const [task, setTask] = useState("");
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const reportRef = useRef<HTMLDivElement>(null);
  const { state, history, runTask, resetState, loadRun, fetchHistory } =
    useAutoFlow();

  const isIdle = state.status === "idle";
  const isRunning = state.status === "running";
  const isSuccess = state.status === "success";
  const isFailed = state.status === "failed";

  /* Auto-resize textarea */
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 160) + "px";
    }
  }, [task]);

  /* Scroll to report when done */
  useEffect(() => {
    if (isSuccess && reportRef.current) {
      reportRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [isSuccess]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!task.trim() || isRunning) return;
    await runTask(task.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(state.finalReport);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleNewTask = () => {
    resetState();
    setTask("");
    textareaRef.current?.focus();
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        history={history}
        activeRunId={state.runId}
        onNewTask={handleNewTask}
        onSelectRun={loadRun}
        onRefresh={fetchHistory}
      />

      {/* Main content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* ─── Centered content area ─── */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-6 py-8">
            {/* ─── Idle state: Welcome ─── */}
            {isIdle && !state.finalReport && (
              <div className="flex flex-col items-center justify-center min-h-[60vh] animate-fade-in">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-amber-700 flex items-center justify-center mb-6 shadow-lg shadow-[var(--accent)]/10">
                  <Sparkles className="w-6 h-6 text-white" />
                </div>
                <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-2">
                  What would you like to research?
                </h2>
                <p className="text-sm text-[var(--text-tertiary)] mb-8 text-center max-w-md">
                  AutoFlow uses AI agents to research topics, gather data, and
                  generate comprehensive reports.
                </p>

                {/* Example task cards */}
                <div className="grid grid-cols-2 gap-2.5 w-full max-w-lg">
                  {EXAMPLE_TASKS.map((t, i) => (
                    <button
                      key={i}
                      onClick={() => setTask(t)}
                      className={clsx(
                        "text-left text-xs px-4 py-3 rounded-xl",
                        "border border-[var(--border-subtle)] hover:border-[var(--border-default)]",
                        "bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)]",
                        "text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]",
                        "transition-all duration-200 leading-relaxed"
                      )}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* ─── Running state: Pipeline + progress ─── */}
            {isRunning && (
              <div className="space-y-6 animate-fade-in-up">
                {/* Task display */}
                <div className="flex items-start gap-3 p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-subtle)]">
                  <div className="w-7 h-7 rounded-lg bg-[var(--bg-tertiary)] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-medium text-[var(--text-tertiary)]">
                      You
                    </span>
                  </div>
                  <p className="text-sm text-[var(--text-primary)] leading-relaxed pt-1">
                    {state.task}
                  </p>
                </div>

                {/* Agent pipeline */}
                <AgentPipeline
                  statuses={state.agentStatuses}
                  outputs={state.agentOutputs}
                />

                {/* Loading indicator */}
                <div className="flex items-center justify-center py-12">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1">
                      {[0, 1, 2].map((i) => (
                        <div
                          key={i}
                          className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]"
                          style={{
                            animation: `dotPulse 1.4s ease-in-out ${
                              i * 0.2
                            }s infinite`,
                          }}
                        />
                      ))}
                    </div>
                    <span className="text-sm text-[var(--text-tertiary)]">
                      Generating report...
                    </span>
                  </div>
                </div>

                {/* Logs */}
                <LogConsole logs={state.logs} />
              </div>
            )}

            {/* ─── Success state: Report ─── */}
            {isSuccess && state.finalReport && (
              <div className="space-y-6 animate-fade-in-up">
                {/* Task display */}
                <div className="flex items-start gap-3 p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-subtle)]">
                  <div className="w-7 h-7 rounded-lg bg-[var(--bg-tertiary)] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-medium text-[var(--text-tertiary)]">
                      You
                    </span>
                  </div>
                  <p className="text-sm text-[var(--text-primary)] leading-relaxed pt-1">
                    {state.task}
                  </p>
                </div>

                {/* Agent pipeline (completed) */}
                <AgentPipeline
                  statuses={state.agentStatuses}
                  outputs={state.agentOutputs}
                />

                {/* Report */}
                <div
                  ref={reportRef}
                  className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] overflow-hidden"
                >
                  {/* Report header */}
                  <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)]">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-400" />
                      <span className="text-xs font-medium text-[var(--text-secondary)]">
                        Report
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={handleCopy}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition-all"
                      >
                        {copied ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-400" />
                            <span className="text-emerald-400">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            Copy
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Report body */}
                  <div className="px-6 py-5">
                    <MarkdownOutput content={state.finalReport} />
                  </div>
                </div>

                {/* Cost + Logs */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <CostTracker
                    usage={state.tokenUsage}
                    totalCost={state.totalCost}
                  />
                  <LogConsole logs={state.logs} />
                </div>
              </div>
            )}

            {/* ─── Failed state ─── */}
            {isFailed && (
              <div className="space-y-6 animate-fade-in-up">
                {/* Task display */}
                {state.task && (
                  <div className="flex items-start gap-3 p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-subtle)]">
                    <div className="w-7 h-7 rounded-lg bg-[var(--bg-tertiary)] flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-medium text-[var(--text-tertiary)]">
                        You
                      </span>
                    </div>
                    <p className="text-sm text-[var(--text-primary)] leading-relaxed pt-1">
                      {state.task}
                    </p>
                  </div>
                )}

                {/* Error display */}
                <div className="flex items-start gap-3 p-5 rounded-xl border border-red-900/50 bg-red-950/20">
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-sm font-medium text-red-300 mb-1">
                      Task failed
                    </h3>
                    <p className="text-sm text-red-400/80">
                      {state.error || "An unknown error occurred."}
                    </p>
                    <button
                      onClick={() => state.task && runTask(state.task)}
                      className="flex items-center gap-1.5 mt-3 text-xs text-red-300 hover:text-red-200 transition-colors"
                    >
                      <RotateCcw className="w-3 h-3" />
                      Retry
                    </button>
                  </div>
                </div>

                {/* Logs */}
                <LogConsole logs={state.logs} />
              </div>
            )}
          </div>
        </div>

        {/* ─── Bottom input bar ─── */}
        <div className="border-t border-[var(--border-subtle)] bg-[var(--bg-primary)]">
          <div className="max-w-3xl mx-auto px-6 py-4">
            <form onSubmit={handleSubmit} className="relative">
              <div
                className={clsx(
                  "flex items-end rounded-xl border transition-all duration-200",
                  "bg-[var(--bg-secondary)]",
                  task.trim()
                    ? "border-[var(--border-active)]"
                    : "border-[var(--border-default)]",
                  "focus-within:border-[var(--accent)]"
                )}
              >
                <textarea
                  ref={textareaRef}
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Describe what you want to research..."
                  disabled={isRunning}
                  rows={1}
                  className={clsx(
                    "flex-1 bg-transparent px-4 py-3 text-sm text-[var(--text-primary)]",
                    "placeholder-[var(--text-muted)] resize-none outline-none",
                    "disabled:opacity-40 max-h-40"
                  )}
                />
                <button
                  type="submit"
                  disabled={!task.trim() || isRunning}
                  className={clsx(
                    "flex-shrink-0 m-1.5 p-2 rounded-lg transition-all duration-200",
                    "disabled:opacity-30 disabled:cursor-not-allowed",
                    task.trim() && !isRunning
                      ? "bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white"
                      : "bg-[var(--bg-tertiary)] text-[var(--text-muted)]"
                  )}
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
              <p className="text-[10px] text-[var(--text-muted)] mt-2 text-center">
                AutoFlow uses Gemini AI to research and generate reports.
                Results may not always be accurate.
              </p>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}

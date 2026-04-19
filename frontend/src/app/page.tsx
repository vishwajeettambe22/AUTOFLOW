"use client";

import { useState } from "react";
import { useAutoFlow } from "@/hooks/useAutoFlow";
import { AgentDAG } from "@/components/AgentDAG";
import { CostTracker } from "@/components/CostTracker";
import { LogConsole } from "@/components/LogConsole";
import { MarkdownOutput } from "@/components/MarkdownOutput";
import clsx from "clsx";

const EXAMPLE_TASKS = [
  "Research top 3 Python web frameworks and write a comparison report",
  "Explain how transformers work and write a simple self-attention implementation in Python",
  "Compare React, Vue, and Svelte and create a decision guide for a startup",
];

export default function HomePage() {
  const [task, setTask] = useState("");
  const { state, runTask } = useAutoFlow();
  const isRunning = state.status === "running";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!task.trim() || isRunning) return;
    await runTask(task.trim());
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              AF
            </div>
            <div>
              <h1 className="text-base font-semibold">AutoFlow</h1>
              <p className="text-xs text-gray-500">AI Agent Orchestration Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className={clsx(
              "w-2 h-2 rounded-full",
              isRunning ? "bg-blue-400 animate-pulse" : "bg-emerald-500"
            )} />
            {isRunning ? "Running" : "Ready"}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left panel — input + agent graph */}
          <div className="lg:col-span-1 space-y-5">

            {/* Task input */}
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
              <h2 className="text-sm font-medium text-gray-300 mb-3">Task</h2>
              <form onSubmit={handleSubmit} className="space-y-3">
                <textarea
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  placeholder="Describe what you want the agents to do..."
                  rows={4}
                  disabled={isRunning}
                  className={clsx(
                    "w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-200",
                    "placeholder-gray-600 resize-none focus:outline-none focus:border-emerald-600",
                    "transition-colors disabled:opacity-50"
                  )}
                />
                <button
                  type="submit"
                  disabled={!task.trim() || isRunning}
                  className={clsx(
                    "w-full py-2.5 rounded-lg text-sm font-medium transition-all",
                    "disabled:opacity-40 disabled:cursor-not-allowed",
                    isRunning
                      ? "bg-blue-700 text-blue-200 cursor-not-allowed"
                      : "bg-emerald-600 hover:bg-emerald-500 text-white active:scale-[0.98]"
                  )}
                >
                  {isRunning ? "Running agents..." : "Run AutoFlow"}
                </button>
              </form>

              {/* Example tasks */}
              {state.status === "idle" && (
                <div className="mt-4 space-y-1.5">
                  <p className="text-xs text-gray-600 mb-2">Try an example:</p>
                  {EXAMPLE_TASKS.map((t, i) => (
                    <button
                      key={i}
                      onClick={() => setTask(t)}
                      className="w-full text-left text-xs text-gray-500 hover:text-gray-300 py-1.5 px-2 rounded hover:bg-gray-800 transition-colors truncate"
                    >
                      {t}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Agent DAG */}
            {(isRunning || state.status === "success" || state.status === "failed") && (
              <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
                <h2 className="text-sm font-medium text-gray-300 mb-3">Agent Pipeline</h2>
                <AgentDAG
                  statuses={state.agentStatuses}
                  outputs={state.agentOutputs}
                />
              </div>
            )}

            {/* Cost tracker */}
            <CostTracker usage={state.tokenUsage} totalCost={state.totalCost} />
          </div>

          {/* Right panel — output + logs */}
          <div className="lg:col-span-2 space-y-5">

            {/* Final report */}
            {state.finalReport ? (
              <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-medium text-gray-300">Output</h2>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-emerald-400 bg-emerald-950 border border-emerald-800 px-2 py-0.5 rounded-full">
                      Complete
                    </span>
                    <button
                      onClick={() => navigator.clipboard.writeText(state.finalReport)}
                      className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                </div>
                <MarkdownOutput content={state.finalReport} />
              </div>
            ) : isRunning ? (
              <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 flex flex-col items-center justify-center min-h-64 space-y-4">
                <div className="flex gap-2">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
                <p className="text-sm text-gray-500">
                  Agents are working on your task...
                </p>
                {/* Show intermediate outputs */}
                {Object.entries(state.agentOutputs).map(([agent, output]) => (
                  <div key={agent} className="w-full bg-gray-800 rounded-lg p-3">
                    <p className="text-xs text-gray-500 mb-1 capitalize">{agent}</p>
                    <p className="text-xs text-gray-400 line-clamp-2">{output}</p>
                  </div>
                ))}
              </div>
            ) : state.status === "failed" ? (
              <div className="rounded-xl border border-red-900 bg-red-950 p-6">
                <h3 className="text-sm font-medium text-red-400 mb-2">Run failed</h3>
                <p className="text-sm text-red-300">{state.error}</p>
              </div>
            ) : (
              <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 flex items-center justify-center min-h-64">
                <div className="text-center space-y-2">
                  <div className="text-3xl text-gray-800">⬡</div>
                  <p className="text-sm text-gray-600">
                    Enter a task to start the agent pipeline
                  </p>
                </div>
              </div>
            )}

            {/* Live log console */}
            <LogConsole logs={state.logs} />
          </div>
        </div>
      </main>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/* ─── Types ──────────────────────────────────────────────────────── */

export type AgentStatus =
  | "pending"
  | "running"
  | "success"
  | "failed"
  | "skipped";

export interface TokenUsage {
  agent: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface RunState {
  status: "idle" | "running" | "success" | "failed";
  runId: string | null;
  task: string | null;
  agentStatuses: Record<string, AgentStatus>;
  agentOutputs: Record<string, string>;
  tokenUsage: TokenUsage[];
  totalCost: number;
  finalReport: string;
  logs: string[];
  error: string | null;
}

export interface HistoryRun {
  run_id: string;
  user_task: string;
  status: string;
  final_report: string;
  total_cost_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  created_at: string | null;
  completed_at: string | null;
}

/* ─── Constants ──────────────────────────────────────────────────── */

const INITIAL_STATE: RunState = {
  status: "idle",
  runId: null,
  task: null,
  agentStatuses: {},
  agentOutputs: {},
  tokenUsage: [],
  totalCost: 0,
  finalReport: "",
  logs: [],
  error: null,
};

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ─── Hook ───────────────────────────────────────────────────────── */

export function useAutoFlow() {
  const [state, setState] = useState<RunState>(INITIAL_STATE);
  const [history, setHistory] = useState<HistoryRun[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const pingRef = useRef<NodeJS.Timeout | null>(null);
  const finalReceivedRef = useRef(false);

  /* ── Logging helper ─────────────────────────────────────────── */
  const addLog = useCallback((msg: string) => {
    const ts = new Date().toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    setState((s) => ({
      ...s,
      logs: [...s.logs.slice(-199), `${ts}  ${msg}`],
    }));
  }, []);

  /* ── WebSocket message handler ──────────────────────────────── */
  const handleMessage = useCallback(
    (data: Record<string, unknown>, event: string) => {
      if (event === "agent_start") {
        const agent = data.agent as string;
        setState((s) => ({
          ...s,
          agentStatuses: { ...s.agentStatuses, [agent]: "running" },
        }));
        addLog(`▸ ${agent} started`);
      }

      if (event === "agent_done") {
        const agent = data.agent as string;
        const status = data.status as AgentStatus;
        setState((s) => ({
          ...s,
          agentStatuses: { ...s.agentStatuses, [agent]: status },
        }));
        addLog(
          `${status === "success" ? "✓" : "✗"} ${agent} → ${status}`
        );
      }

      if (event === "agent_output") {
        const agent = data.agent as string;
        const output = data.output as string;
        setState((s) => ({
          ...s,
          agentOutputs: { ...s.agentOutputs, [agent]: output },
        }));
      }

      if (event === "agent_log") {
        addLog(`  ${data.agent}: ${data.message}`);
      }

      if (event === "token_usage") {
        setState((s) => ({
          ...s,
          tokenUsage: [...s.tokenUsage, data as unknown as TokenUsage],
          totalCost: s.totalCost + ((data.cost_usd as number) || 0),
        }));
      }

      if (event === "final") {
        finalReceivedRef.current = true;
        setState((s) => ({
          ...s,
          status: "success",
          finalReport: data.report as string,
          totalCost: data.total_cost_usd as number,
        }));
        addLog("✓ Task completed");
      }

      if (event === "error") {
        setState((s) => ({
          ...s,
          status: "failed",
          error: data.error as string,
          agentStatuses: {
            ...s.agentStatuses,
            [data.agent as string]: "failed",
          },
        }));
        addLog(`✗ Error: ${data.error}`);
      }
    },
    [addLog]
  );

  /* ── Connect WebSocket ──────────────────────────────────────── */
  const connectWS = useCallback(
    (runId: string): Promise<void> => {
      return new Promise((resolve, reject) => {
        try {
          const ws = new WebSocket(`${WS_URL}/ws/${runId}`);
          wsRef.current = ws;

          const timeout = setTimeout(() => {
            // Resolve anyway — WS is optional, REST carries the result
            resolve();
          }, 3000);

          ws.onopen = () => {
            clearTimeout(timeout);
            addLog("⚡ Connected to server");
            pingRef.current = setInterval(() => ws.send("ping"), 20_000);
            resolve();
          };

          ws.onmessage = (e) => {
            try {
              const msg = JSON.parse(e.data);
              if (msg.event === "pong") return;
              handleMessage(msg.data, msg.event);
            } catch {
              // ignore parse errors
            }
          };

          ws.onerror = () => {
            clearTimeout(timeout);
            addLog("⚠ WebSocket error — using REST fallback");
            resolve(); // Don't fail — REST will still work
          };

          ws.onclose = () => {
            if (pingRef.current) clearInterval(pingRef.current);
          };
        } catch {
          resolve(); // Don't block on WS failures
        }
      });
    },
    [addLog, handleMessage]
  );

  /* ── Run a task ─────────────────────────────────────────────── */
  const runTask = useCallback(
    async (task: string) => {
      finalReceivedRef.current = false;

      const runId = crypto.randomUUID();

      setState({
        ...INITIAL_STATE,
        status: "running",
        runId,
        task,
        logs: [],
      });

      addLog("Starting task...");

      // Connect WS for live updates
      await connectWS(runId);

      try {
        const res = await fetch(`${API_URL}/api/v1/run-task`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task, run_id: runId }),
        });

        const result = await res.json();

        // If WS already delivered the final event, don't override
        if (!finalReceivedRef.current) {
          if (
            result.status === "success" &&
            result.final_report?.trim()
          ) {
            setState((s) => ({
              ...s,
              status: "success",
              finalReport: result.final_report,
              totalCost: result.total_cost_usd || s.totalCost,
            }));
            addLog("✓ Task completed");
          } else {
            setState((s) => ({
              ...s,
              status: "failed",
              error: result.error || "Task failed — no report generated",
            }));
            addLog(`✗ Task failed: ${result.error || "No report"}`);
          }
        }
      } catch (err) {
        setState((s) => ({
          ...s,
          status: "failed",
          error: err instanceof Error ? err.message : "Network error",
        }));
        addLog("✗ Connection failed");
      } finally {
        // Close WS after REST completes
        setTimeout(() => {
          wsRef.current?.close();
        }, 1000);
      }
    },
    [connectWS, addLog]
  );

  /* ── Reset state ────────────────────────────────────────────── */
  const resetState = useCallback(() => {
    wsRef.current?.close();
    setState(INITIAL_STATE);
  }, []);

  /* ── Load a past run ────────────────────────────────────────── */
  const loadRun = useCallback(async (runId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/run/${runId}/result`);
      if (!res.ok) throw new Error("Run not found");
      const run = await res.json();
      setState({
        ...INITIAL_STATE,
        status: run.status === "success" ? "success" : "failed",
        runId: run.run_id,
        task: run.task,
        finalReport: run.final_report || "",
        totalCost: run.total_cost_usd || 0,
        error: run.status !== "success" ? "This run failed" : null,
      });
    } catch {
      // ignore
    }
  }, []);

  /* ── Fetch history ──────────────────────────────────────────── */
  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/runs`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.runs || []);
      }
    } catch {
      // History endpoint may not exist yet — that's okay
    }
  }, []);

  /* ── Cleanup ────────────────────────────────────────────────── */
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      if (pingRef.current) clearInterval(pingRef.current);
    };
  }, []);

  return { state, history, runTask, resetState, loadRun, fetchHistory };
}

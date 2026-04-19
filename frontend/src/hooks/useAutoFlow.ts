"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type AgentStatus = "pending" | "running" | "success" | "failed" | "skipped";

export interface AgentEvent {
  agent: string;
  status?: AgentStatus;
  output?: string;
  message?: string;
}

export interface TokenUsage {
  agent: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface WSMessage {
  event: string;
  data: Record<string, unknown>;
}

export interface RunState {
  status: "idle" | "running" | "success" | "failed";
  agentStatuses: Record<string, AgentStatus>;
  agentOutputs: Record<string, string>;
  tokenUsage: TokenUsage[];
  totalCost: number;
  finalReport: string;
  logs: string[];
  error: string | null;
}

const INITIAL_STATE: RunState = {
  status: "idle",
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

export function useAutoFlow() {
  const [state, setState] = useState<RunState>(INITIAL_STATE);
  const wsRef = useRef<WebSocket | null>(null);
  const pingRef = useRef<NodeJS.Timeout | null>(null);

  const addLog = useCallback((msg: string) => {
    setState((s) => ({ ...s, logs: [...s.logs.slice(-99), msg] }));
  }, []);

  const connectWS = useCallback((runId: string): Promise<void> => {
    return new Promise((resolve) => {
      const ws = new WebSocket(`${WS_URL}/ws/${runId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        addLog("WebSocket connected");
        // Keepalive ping every 20s
        pingRef.current = setInterval(() => ws.send("ping"), 20_000);
        resolve();
      };

      ws.onmessage = (e) => {
        try {
          const msg: WSMessage = JSON.parse(e.data);
          handleMessage(msg);
        } catch {}
      };

      ws.onerror = () => {
        addLog("WebSocket error");
        setState((s) => ({ ...s, status: "failed", error: "Connection error" }));
      };

      ws.onclose = () => {
        if (pingRef.current) clearInterval(pingRef.current);
        addLog("WebSocket closed");
      };
    });
  }, [addLog]);

  const handleMessage = useCallback((msg: WSMessage) => {
    const { event, data } = msg;

    if (event === "agent_start") {
      const agent = data.agent as string;
      setState((s) => ({
        ...s,
        agentStatuses: { ...s.agentStatuses, [agent]: "running" },
      }));
      addLog(`[${agent}] started`);
    }

    if (event === "agent_done") {
      const agent = data.agent as string;
      const status = data.status as AgentStatus;
      setState((s) => ({
        ...s,
        agentStatuses: { ...s.agentStatuses, [agent]: status },
      }));
      addLog(`[${agent}] ${status}`);
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
      addLog(`[${data.agent}] ${data.message}`);
    }

    if (event === "token_usage") {
      setState((s) => ({
        ...s,
        tokenUsage: [...s.tokenUsage, data as unknown as TokenUsage],
        totalCost: s.totalCost + ((data.cost_usd as number) || 0),
      }));
    }

    if (event === "final") {
      setState((s) => ({
        ...s,
        status: "success",
        finalReport: data.report as string,
        totalCost: data.total_cost_usd as number,
      }));
      addLog("Task completed successfully");
      wsRef.current?.close();
    }

    if (event === "error") {
      setState((s) => ({
        ...s,
        status: "failed",
        error: data.error as string,
        agentStatuses: { ...s.agentStatuses, [data.agent as string]: "failed" },
      }));
      addLog(`[ERROR] ${data.agent}: ${data.error}`);
    }
  }, [addLog]);

  const runTask = useCallback(async (task: string) => {
    setState({ ...INITIAL_STATE, status: "running", logs: ["Starting task..."] });

    const runId = crypto.randomUUID();

    // Connect WS first, then kick off the task
    await connectWS(runId);

    const res = await fetch(`${API_URL}/api/v1/run-task`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task, run_id: runId }),
    });

    if (!res.ok) {
      const err = await res.json();
      setState((s) => ({ ...s, status: "failed", error: err.detail || "API error" }));
    }
  }, [connectWS]);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
      if (pingRef.current) clearInterval(pingRef.current);
    };
  }, []);

  return { state, runTask };
}

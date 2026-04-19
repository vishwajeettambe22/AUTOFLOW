# AutoFlow — AI Agent Orchestration Platform

A production-grade multi-agent AI system. Users describe a task in plain English — AutoFlow decomposes it, dispatches specialist agents, self-heals on failure, and delivers a polished result in real time.

---

## Architecture

```
User Task
    │
    ▼
┌─────────┐     ┌────────────┐     ┌───────┐     ┌──────────┐     ┌──────────┐
│ Planner │────▶│ Researcher │────▶│ Coder │────▶│ Reviewer │────▶│ Reporter │
└─────────┘     └────────────┘     └───────┘     └──────────┘     └──────────┘
                      │                               │
                      └───────────────────────────────┘
                                    │ (on failure)
                                    ▼
                              ┌──────────┐
                              │  Critic  │  ← Self-healing
                              └──────────┘
                                    │ (replan / retry)
                                    └──▶ back to Researcher or Coder
```

**State flows through LangGraph as a typed dict. Every agent reads and writes to a shared `AutoFlowState`.**

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Orchestration | LangGraph (stateful DAG) |
| LLMs | Claude 3.5 Sonnet / GPT-4o |
| Short-term memory | Redis |
| Long-term memory | PostgreSQL + pgvector |
| Real-time | WebSockets |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Deployment | Railway (backend), Vercel (frontend) |

---

## Project Structure

```
autoflow/
├── backend/
│   ├── agents/
│   │   ├── planner.py       # Breaks task into subtasks
│   │   ├── researcher.py    # Web search + info gathering
│   │   ├── coder.py         # Output generation + code exec
│   │   ├── reviewer.py      # Quality validation
│   │   ├── critic.py        # Self-healing failure analysis
│   │   └── reporter.py      # Final synthesis
│   ├── graph/
│   │   └── workflow.py      # LangGraph DAG + conditional edges
│   ├── tools/
│   │   ├── search.py        # DuckDuckGo web search
│   │   └── code_exec.py     # Safe subprocess sandbox
│   ├── memory/
│   │   ├── redis_store.py   # Run state + caching
│   │   └── postgres_store.py# Persistent runs + costs
│   ├── core/
│   │   ├── config.py        # Settings (pydantic)
│   │   ├── state.py         # AutoFlowState TypedDict
│   │   ├── llm.py           # LLM wrapper + cost tracking
│   │   └── events.py        # WebSocket event emitter
│   └── api/
│       └── main.py          # FastAPI app + WS endpoint
├── frontend/
│   └── src/
│       ├── app/
│       │   └── page.tsx     # Main UI
│       ├── components/
│       │   ├── AgentDAG.tsx     # Live agent pipeline visual
│       │   ├── CostTracker.tsx  # Token + cost display
│       │   ├── LogConsole.tsx   # Real-time log stream
│       │   └── MarkdownOutput.tsx # Final report renderer
│       └── hooks/
│           └── useAutoFlow.ts   # WS hook + state management
├── docker-compose.yml       # Local Redis + Postgres
└── README.md
```

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker Desktop

### 1. Start databases

```bash
docker-compose up -d
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY or OPENAI_API_KEY

python main.py
# Runs on http://localhost:8000
```

### 3. Frontend setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
# Runs on http://localhost:3000
```

---

## Test Run

**Example task:**
```
Research top 3 Python web frameworks and write a comparison report
```

**Expected agent flow:**
1. **Planner** → creates 3 subtasks: research frameworks, write comparison, review accuracy
2. **Researcher** → searches DuckDuckGo for "Python web frameworks 2025 comparison", returns results on FastAPI, Django, Flask
3. **Coder** → writes a structured markdown comparison report with a feature table
4. **Reviewer** → scores the report (aims for 7+/10), passes if complete
5. **Reporter** → synthesizes final polished output with summary + key takeaways

If Reviewer fails → **Critic** analyzes why → sends Coder back with specific fix instructions.

---

## API Reference

### POST `/api/v1/run-task`
```json
{
  "task": "Research top 3 Python web frameworks and write a comparison report",
  "run_id": "optional-uuid-for-ws-correlation"
}
```

### WebSocket `/ws/{run_id}`

Connect before calling `/run-task`. Events received:

| Event | Payload |
|---|---|
| `agent_start` | `{agent, status: "running"}` |
| `agent_done` | `{agent, status: "success"\|"failed"}` |
| `agent_output` | `{agent, output: string}` |
| `agent_log` | `{agent, message}` |
| `token_usage` | `{agent, model, input_tokens, output_tokens, cost_usd}` |
| `error` | `{agent, error}` |
| `final` | `{report, total_cost_usd}` |

---

## Deployment on Railway

### Backend

1. Push `backend/` to a GitHub repo
2. Create new Railway project → "Deploy from GitHub"
3. Add services: **PostgreSQL** and **Redis** (from Railway templates)
4. Set environment variables:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   ```
5. Railway auto-detects `railway.toml` and deploys

### Frontend (Vercel)

1. Push `frontend/` to GitHub
2. Import to Vercel
3. Set env vars:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   NEXT_PUBLIC_WS_URL=wss://your-backend.railway.app
   ```

---

## Key Design Decisions

**Why LangGraph over a plain loop?**
LangGraph gives typed state, conditional edges, checkpointing, and visual introspection. A loop has none of these — it breaks silently and can't recover.

**Why does the Critic exist?**
Rather than retrying with identical inputs (which fails identically), the Critic diagnoses *why* something failed and produces modified instructions. This is the difference between a retry and a re-plan.

**Why track cost per agent?**
Production systems need cost visibility. The tracker shows which agents are expensive so you can swap cheaper models (e.g. Haiku for Reviewer) without touching architecture.

**Why connect WebSocket before calling `/run-task`?**
The workflow starts immediately. If you call the endpoint first, the WS connects after agents have already run — you miss events. Always WS-first.

# Anvil 2026 — Ops Alert Triage System
Multi-Agent Autonomous Pipeline for Incident Response

## Quick Start

### 1. Configure your API keys
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### 2. Install dependencies (from project root)
```bash
pip install -r requirements.txt
```

### 3. Run the Web UI (Recommended)
```bash
python web_ui/main.py
```
Then open: http://localhost:8000

### 4. Run Group A only (Reader + Searcher)
```bash
python group-a-agents/main.py
```

### 5. Run Group B only (Decider + Notifier)
```bash
python group-b-agents/main.py
```

### 6. Run full pipeline end-to-end
```bash
python integration/combined_workflow.py
```

---

## Project Structure

```
AnvilFinale/
├── .env                         # Your API keys (create from .env.example)
├── requirements.txt
│
├── database/
│   ├── db_manager.py            # SQLite helpers
│   └── incidents.db             # Auto-created on first run
│
├── group-a-agents/              # Agent 1 (Reader) + Agent 2 (Searcher)
│   ├── main.py
│   └── src/
│       ├── config.py
│       ├── agents/
│       │   ├── agent_1_reader.py
│       │   └── agent_2_searcher.py
│       └── workflow/
│           ├── state.py
│           └── graph.py
│
├── group-b-agents/              # Agent 3 (Decider) + Agent 4 (Notifier)
│   ├── main.py
│   └── src/
│       ├── config.py
│       ├── agents/
│       │   ├── agent_3_decider.py
│       │   └── agent_4_notifier.py
│       └── workflow/
│           ├── state.py
│           └── graph.py
│
├── integration/
│   └── combined_workflow.py     # Full A→B pipeline
│
└── web_ui/
    └── main.py                  # FastAPI UI
```

---

## What Each Agent Does

| Agent | Name | Job |
|-------|------|-----|
| 1 | Alert Reader | Parse raw alert text into structured JSON |
| 2 | Past Searcher | Find similar incidents in SQLite DB, fall back to LLM web-style reasoning |
| 3 | Decision Maker | Choose the right action (restart / rollback / escalate / etc.) |
| 4 | Slack Notifier | Post the result to Slack (or print if no webhook) |

---

## Tech Stack
- **LangGraph** — agent orchestration
- **OpenAI-compatible LLM** via OpenCode/MiniMax (or any OpenAI-compatible endpoint)
- **FastAPI** — web UI
- **SQLite** — local incident history database

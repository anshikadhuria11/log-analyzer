# Log Analyzer — AI-Powered Root Cause Analysis

> Paste any server log. Get back a structured breakdown of what went wrong, which lines prove it, and how to fix it. Powered by Groq AI.

---

## What Is This?

Log Analyzer is a full-stack web application that uses a large language model (LLM) to analyze server and application logs. You paste a log, click a button, and within 10–15 seconds you get:

-  A plain-English **summary** of what happened
-  The identified **root cause** (with category: database, network, memory, etc.)
-  **Evidence** — the specific log lines that prove the root cause
-  A **timeline** of how the problem unfolded
-  Concrete **suggested fixes**
- **Confidence level** (high / medium / low) with reasoning

The app works with any log format: plain text, JSON Lines (JSONL), CloudWatch-style timestamps, Python tracebacks, Nginx access logs, Docker logs — anything.

---

## Screenshots

> Dark mode UI with AI-generated structured analysis report.

```
┌──────────────────────────────────────────────────────────┐
│  Log Analyzer  [AI]                    ● API online   │
│                                                          │
│       Find the root cause of your logs instantly         │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  [🔗 Pipeline]  [⚡ Raw]                           │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │ 2024-01-15 10:23:45 ERROR db timeout         │  │  │
│  │  │ 2024-01-15 10:23:46 FATAL service shutdown   │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  │                   [🔍 Analyze Logs]                │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│   The service crashed due to DB connection exhaustion  │
│   Root Cause: Database connection pool exhausted       │
│   Fix: Increase pool_size, add retry logic             │
└──────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **AI / LLM** | LangChain, Groq (Qwen / other models) |
| **Frontend** | React 18, TypeScript, Vite |
| **Styling** | Vanilla CSS (dark-mode, glassmorphic) |
| **Data validation** | Pydantic v2 |
| **Rate limiting** | In-memory per-IP limiter |
| **Storage** | In-memory (default) or AWS DynamoDB |

---

## How It Works

The analysis pipeline has 7 stages:

```
Log text → Parser → Reducer → Prompt Builder → LLM (Groq) → Validator → Report
```

1. **Parser** — detects format (plain text / JSONL / CloudWatch), extracts log level, timestamps, service names, and groups stack traces
2. **Reducer** — masks variable data (IPs, UUIDs, numbers) to find repeating patterns, identifies first error, detects spikes, selects the most informative lines
3. **Prompt Builder** — constructs a focused, structured prompt for the AI with stats, patterns, suspects, and selected log lines
4. **LLM** — calls Groq (or Google, or the built-in fake model) and requests a structured JSON response matching the `AnalysisReport` schema
5. **Validator** — checks every line number the AI cited actually exists in the original log and that the text matches
6. **Retry** — if citations are wrong, sends a correction request to the AI
7. **Response** — packages the report, metadata, and validation info as JSON for the frontend

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- A free Groq API key from [console.groq.com](https://console.groq.com)

### 2. Clone and set up
```bash
git clone https://github.com/YOUR_USERNAME/log-analyzer.git
cd log-analyzer

# Backend dependencies
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 3. Configure environment
Create a `.env` file in the project root:
```env
LLM_PROVIDER=groq
LLM_MODEL=qwen/qwen3.8-27b
GROQ_API_KEY=gsk_your_key_here
```

> **No API key?** Use `LLM_PROVIDER=fake` to run offline with a deterministic demo response.

### 4. Run the app

**Terminal 1 — Backend:**
```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

**Open:** http://localhost:5173

The header will show a green **"API online"** dot when both services are connected correctly.

---

## Project Structure

```
log-analyzer/
├── backend/
│   └── app/
│       ├── main.py          # FastAPI app factory + CORS middleware
│       ├── routes.py        # /api/health, /api/analyze, /api/history
│       ├── schemas.py       # Pydantic models (LogEvent, AnalysisReport, etc.)
│       ├── config.py        # Settings loaded from .env via pydantic-settings
│       ├── prompts.py       # System prompt + pipeline/raw prompt builders
│       ├── ratelimit.py     # In-memory per-IP rate limiter
│       └── services/
│           ├── parser.py    # Format detection + LogEvent construction
│           ├── reducer.py   # Pattern grouping, spike detection, line selection
│           ├── analyzer.py  # Pipeline mode orchestration
│           ├── baseline.py  # Raw mode orchestration
│           ├── llm.py       # Groq / Google / Fake LLM factory
│           ├── validator.py # Citation line number + text validation
│           └── storage.py   # In-memory or DynamoDB report storage
├── frontend/
│   ├── index.html
│   ├── vite.config.ts       # Dev proxy: /api/* → localhost:8000
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx         # React entry point
│       ├── App.tsx          # Root component, layout, health check
│       ├── styles.css       # Global dark-mode CSS design system
│       ├── types.ts         # TypeScript interfaces matching backend schemas
│       └── components/
│           ├── LogInput.tsx     # Paste area, mode selector, submit button
│           └── ResultPanel.tsx  # Structured report renderer
├── docs/
│   ├── arjun.md         # Project overview (plain English)
│   ├── setup.md         # Installation guide
│   ├── instruction.md   # Usage guide
│   ├── explanation.md   # Technical deep-dive (how it works)
│   └── commit.md        # Git workflow guide
├── .env                 # API keys — never commit this!
├── .gitignore
├── requirements.txt     # Python production dependencies
└── requirements-dev.txt # Python dev/test dependencies
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check — returns `{"status":"ok"}` |
| `/api/config` | GET | Current model, provider, rate limit settings |
| `/api/analyze` | POST | Analyze a log — main endpoint |
| `/api/history` | GET | List saved reports (if storage enabled) |
| `/api/history/{id}` | GET | Get a specific saved report |

**POST `/api/analyze` request body:**
```json
{
  "logs": "ERROR: database connection failed\nFATAL: service down",
  "mode": "pipeline",
  "save": false
}
```

**Interactive docs:** `http://localhost:8000/docs` (FastAPI auto-generates this)

---

## Configuration Reference

All settings can be set in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `groq` | AI provider: `groq`, `google`, or `fake` |
| `LLM_MODEL` | `qwen/qwen3.8-27b` | Model name for the chosen provider |
| `GROQ_API_KEY` | _(empty)_ | Groq API key |
| `GOOGLE_API_KEY` | _(empty)_ | Google AI Studio API key |
| `MAX_ANALYSIS_LINES` | `300` | Max lines sent to LLM after selection |
| `CONTEXT_LINES` | `5` | Lines before/after each suspect to include |
| `TOP_PATTERNS` | `15` | Max error patterns to include in prompt |
| `RATE_LIMIT_PER_10MIN` | `10` | Max requests per IP per 10 minutes |
| `ENABLE_HISTORY` | `false` | Enable DynamoDB storage |
| `DYNAMODB_TABLE` | `log_analyses` | DynamoDB table name (if enabled) |

---

## Two Analysis Modes Explained

### Pipeline Mode (recommended)
Full processing pipeline:
1. Parse every line into structured events
2. Mask variable data and group patterns
3. Find first error, detect spikes, identify suspects
4. Select the most informative ~300 lines
5. Send to LLM with structured context
6. Validate citations, retry if needed

**Best for:** Long logs (50+ lines), structured formats, accurate root cause analysis.

### Raw Mode
Simplified:
1. Number every line (`L1 | ...`, `L2 | ...`)
2. Send everything directly to LLM
3. Validate citations (no retry)

**Best for:** Short logs (<100 lines), unusual formats, quick second opinions.

---

## Supported Log Formats

- **Plain text** — any log with `ERROR`/`WARN`/`INFO` etc. keywords
- **JSON Lines (JSONL)** — `{"level":"error","message":"...","timestamp":"..."}`
- **CloudWatch style** — ISO timestamp followed by log content
- **Stack traces** — Python, Java, Node.js tracebacks (grouped with parent error)
- **Mixed** — the parser does its best with whatever you give it

---


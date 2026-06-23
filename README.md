# TaxCalamity

**Production-Grade Wealth Advisory & Tax Optimization Platform for Thailand**

A multi-agent AI system built for Thai wealth advisors and fund managers.  
Combines natural language processing, deterministic tax calculations, fund recommendation, and SEC compliance auditing in a single workflow.

> **Core Design Principle**:  
> AI does NOT calculate taxes. All tax computations are deterministic Python functions.  
> AI can only extract, explain, recommend, and validate — never invent financial rules.

---

## Tech Stack

**Backend:** FastAPI, LangGraph (SQLite checkpointer), SQLAlchemy, Pydantic v2  
**Frontend:** Next.js 15, React 19, TailwindCSS, ReactFlow, Recharts  
**LLM:** Qwen 3 32B via Groq for reasoning; Typhoon for Thai NLP (auto-falls back to Groq if unavailable). Agents call the providers directly over their OpenAI-compatible APIs.  
**Persistence:** SQLite by default (Postgres optional via `DATABASE_URL`)

---

## Architecture Overview

```
User (Thai text input)
        |
        v
+------------------+     +------------------+     +--------------------+
| Typhoon NLP      | --> | Client Intake    | --> | Suitability        |
| (Thai language   |     | (Extract age,    |     | (Risk profile,     |
|  interpreter)    |     |  income, goals)  |     |  horizon, alloc.)  |
+------------------+     +------------------+     +--------------------+
                                                          |
                                                          v
+------------------+     +------------------+     +--------------------+
| Explanation      | <-- | Fund Selection   | <-- | Tax Engine         |
| (Why / Benefit / |     | (SSF, RMF,       |     | (Progressive       |
|  Risk for each)  |     |  ThaiESG match)  |     |  bracket calc.)    |
+------------------+     +------------------+     +--------------------+
        |
        v
+------------------+     +------------------+     +--------------------+
| Human Review     | --> | SEC Compliance   | --> | Report Generator   |
| (Advisor must    |     | (Violation check,|     | (Final output +    |
|  approve first)  |     |  risk mismatch)  |     |  audit trail)      |
+------------------+     +------------------+     +--------------------+
```

The workflow **pauses at Human Review**. The advisor must explicitly approve the recommendation before compliance and report generation runs.

---

## 9-Agent System

| Agent | Model | What It Does |
|-------|-------|-------------|
| **Typhoon Interpreter** | Typhoon v2 70B | Converts informal Thai financial text into structured JSON |
| **Client Intake** | Qwen 3 32B (Groq) | Extracts demographics and financial figures from normalized text |
| **Suitability Analyst** | Qwen 3 32B (Groq) | Determines risk profile, investment horizon, and asset allocation |
| **Tax Engine** | Pure Python | Calculates Thai personal income tax using progressive brackets |
| **Fund Recommender** | Catalog Lookup | Matches SSF/RMF/ThaiESG funds to available capacity and risk |
| **Explainability** | Qwen 3 32B (Groq) | Generates Why, Benefit, Risk, and Assumptions for each fund |
| **Human Review** | Checkpoint | Pauses the workflow for licensed advisor approval |
| **Compliance Auditor** | Qwen 3 32B (Groq) | Checks for SEC violations, return guarantees, risk mismatches |
| **Report Generator** | Deterministic | Renders final advisory report and persists full audit trail |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose (optional, for PostgreSQL/Redis)

### 1. Clone

```bash
git clone https://github.com/pusanada/taxCalamity.git
cd taxCalamity
git checkout prototype
```

### 2. Environment Variables

Create a `.env` file in the project root:

```env
VERBOSE=false
DATABASE_URL=sqlite:///./wealth_advisor.db
CHECKPOINT_DB_PATH=./langgraph_checkpoints.sqlite

# CORS: comma-separated allowed frontend origins ("*" for local dev)
CORS_ORIGINS=*

# Groq API (powers all reasoning agents — Qwen 3 32B). Free key: console.groq.com
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL=qwen/qwen3-32b

# Typhoon API (Thai NLP). Free tier: opentyphoon.ai
# Optional — if the key is missing/invalid, the Thai interpreter falls back to Groq.
TYPHOON_API_KEY=your_typhoon_api_key_here
TYPHOON_MODEL=typhoon-v2.1-12b-instruct
TYPHOON_API_BASE=https://api.opentyphoon.ai/v1
```

For the frontend, set `NEXT_PUBLIC_API_URL` (in `frontend/.env.local` locally, or in Vercel) to the backend URL. It defaults to `http://localhost:8000`.

**No API keys?** The platform falls back to deterministic mock responses, so you can explore the full workflow without any LLM provider. See `.env.example` for a complete template.

### 3. Start Backend

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

API available at: `http://localhost:8000`  
Swagger docs at: `http://localhost:8000/docs`

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at: `http://localhost:3000`

### 5. Start Infrastructure (Optional)

```bash
cd backend
docker-compose up -d
```

This starts PostgreSQL 15, Redis 7, and Qdrant. Update `DATABASE_URL` in `.env` to the PostgreSQL connection string.

---

## Deployment

Recommended split: **backend on Render** (Docker), **frontend on Vercel**.

### Backend → Render

The repo includes a `Dockerfile` (build context = repo root) and a `render.yaml` Blueprint.

1. Push the repo to GitHub.
2. In Render: **New + → Blueprint**, select the repo. It reads `render.yaml`.
3. Set the secret env vars in the Render dashboard:
   - `GROQ_API_KEY` — your Groq key
   - `TYPHOON_API_KEY` — optional (falls back to Groq if omitted)
   - `CORS_ORIGINS` — your Vercel frontend URL, e.g. `https://your-app.vercel.app` (no trailing slash)
4. Deploy. The health check is `GET /`. Note the service URL.

> On Render's free tier the filesystem is ephemeral, so `DATABASE_URL` and `CHECKPOINT_DB_PATH` point at `/tmp`. State resets when the instance restarts — fine for a demo. For durable state, attach a Render Disk or use a managed Postgres.

### Frontend → Vercel

1. In Vercel: **Add New → Project**, import the repo, set the **Root Directory** to `frontend`.
2. Add env var `NEXT_PUBLIC_API_URL` = your Render backend URL.
3. Deploy. Update the backend's `CORS_ORIGINS` to the resulting Vercel URL.

### Local Docker (backend only)

```bash
docker build -t taxcalamity-backend .
docker run -p 8000:8000 --env-file .env taxcalamity-backend
```

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/api/v1/analyze` | Submit client text, runs pipeline up to Human Review |
| POST | `/api/v1/recommend` | Approve and resume workflow, runs Compliance + Report |
| GET | `/api/v1/report/{session_id}` | Get final advisory report |
| GET | `/api/v1/audit/{session_id}` | Get full audit trail with agent runs and compliance flags |
| GET | `/api/v1/session/{session_id}` | Get session state with ReactFlow graph data |

### Example: Submit for Analysis

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "raw_input_text": "I am 35 years old, monthly salary around 150k THB, 4 months bonus per year, small RMF investment, have life insurance, want to optimize taxes",
    "session_id": "demo-001"
  }'
```

### Example: Approve and Generate Report

```bash
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo-001"}'
```

### Response Shape

```json
{
  "session_id": "demo-001",
  "typhoon_result": {
    "normalized_thai": "...",
    "english_translation": "Salary 150,000 THB, 4 months bonus, small RMF, has life insurance, seeking tax optimization",
    "confidence": 0.95,
    "missing_information": [],
    "entities": { "age": 35, "monthly_income": 150000, "bonus_months": 4 }
  },
  "client_data": {
    "age": 35,
    "monthly_income": 150000.0,
    "bonus_months": 4,
    "existing_rmf": 0.0,
    "existing_ssf": 0.0,
    "life_insurance": 0.0,
    "goal": "Tax Optimization",
    "risk_profile": "Moderate"
  },
  "tax_result": {
    "tax_before": 284500.0,
    "tax_after": 134500.0,
    "saving": 150000.0,
    "detailed_calculations": { "..." : "..." }
  },
  "recommendation": {
    "recommended_funds": [
      {
        "fund_code": "KFLTFDIV-SSF",
        "fund_type": "SSF",
        "amount_thb": 200000.0,
        "risk_level": 6,
        "allocation_percentage": 28.57
      }
    ]
  },
  "status": "awaiting_review",
  "trace": ["[Orchestrator] Initialized...", "..."]
}
```

---

## Deterministic Tax Engine

All tax math is pure Python. No AI involved.

### Thai Personal Income Tax Brackets

| Taxable Income (THB) | Rate |
|----------------------|------|
| 0 - 150,000 | 0% |
| 150,001 - 300,000 | 5% |
| 300,001 - 500,000 | 10% |
| 500,001 - 750,000 | 15% |
| 750,001 - 1,000,000 | 20% |
| 1,000,001 - 2,000,000 | 25% |
| 2,000,001 - 5,000,000 | 30% |
| 5,000,001+ | 35% |

### Fund Deduction Limits

| Fund Type | Individual Cap | Joint Cap |
|-----------|---------------|-----------|
| SSF | 30% of income, max 200,000 THB | SSF + RMF combined max 500,000 THB |
| RMF | 30% of income, max 500,000 THB | SSF + RMF combined max 500,000 THB |
| ThaiESG | 30% of income, max 300,000 THB | Separate cap (not in 500k pool) |
| Life Insurance | Max 100,000 THB | N/A |

### Core Functions

```python
calculate_tax(taxable_income)                # Progressive bracket calculation
calculate_ssf_limit(income)                  # SSF cap: min(30% of income, 200k)
calculate_rmf_limit(income)                  # RMF cap: min(30% of income, 500k)
calculate_remaining_deduction_capacity(...)  # Joint cap-aware capacity optimizer
calculate_tax_savings(...)                   # Before vs after tax comparison
```

---

## Project Structure

```
taxCalamity/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   └── agents.py           # 9 CrewAI agent definitions and crew runners
│   │   ├── db/
│   │   │   ├── database.py         # SQLAlchemy engine, session factory, init
│   │   │   └── models.py           # Client, Profile, Recommendation, Audit models
│   │   ├── graph/
│   │   │   └── workflow.py         # LangGraph StateGraph with 9 nodes + routing
│   │   ├── schemas/
│   │   │   └── schemas.py          # Pydantic v2 request/response schemas
│   │   ├── services/
│   │   │   ├── tax_engine.py       # Deterministic Thai PIT calculator
│   │   │   ├── tax_service.py      # Tax service utilities
│   │   │   ├── fund_catalog.py     # Fund seeder and recommendation engine
│   │   │   └── fund_service.py     # Fund lookup services
│   │   ├── config.py               # Pydantic Settings loaded from .env
│   │   └── main.py                 # FastAPI app with 6 API endpoints
│   ├── tests/
│   │   ├── test_api.py             # Automated API test suite
│   │   ├── test_advisory.py        # Advisory flow tests
│   │   └── run_e2e_flow.py         # End-to-end flow runner script
│   ├── docker-compose.yml          # PostgreSQL + Redis + Qdrant containers
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── app/
│   │   ├── page.tsx                # Main dashboard with ReactFlow workflow graph
│   │   ├── layout.tsx              # Root layout with metadata and fonts
│   │   └── globals.css             # TailwindCSS base + custom styles
│   ├── package.json                # Next.js 15 + React 19 dependencies
│   ├── tailwind.config.js          # Tailwind configuration
│   ├── postcss.config.js           # PostCSS configuration
│   └── tsconfig.json               # TypeScript configuration
├── .env                            # Environment variables (git-ignored)
├── .gitignore
└── README.md
```

---

## Design Decisions

### Why AI Cannot Calculate Taxes

Thai tax law is complex but deterministic. LLMs introduce:
- **Hallucination risk** — LLMs may invent tax brackets or limits that don't exist
- **Non-reproducibility** — Same input may produce different tax amounts on each run
- **Audit failure** — Regulators require deterministic, verifiable calculations

Our approach: AI handles language extraction and explanation. Python functions handle all math.

### Why Two LLMs (Typhoon + Qwen)

- **Typhoon** is trained on Thai text and understands informal financial slang
- **Qwen 3 32B** (via Groq) is fast and accurate for structured reasoning tasks
- Typhoon runs once at intake, Qwen runs for all reasoning steps — cost-efficient split

### Why Human-in-the-Loop

Fund recommendations must be reviewed by a licensed advisor before compliance audit runs. The LangGraph workflow uses `interrupt_after=["human_review"]` to enforce this mandatory checkpoint.

### Why LangGraph Instead of Plain CrewAI

- **State persistence** — Each node saves state to the database, sessions can be resumed later
- **Conditional routing** — Failed nodes route to END, low-confidence inputs route to human review
- **Checkpointing** — MemorySaver enables pause/resume across separate HTTP requests

---

## Testing

```bash
# Run API tests
cd backend
python -m pytest tests/test_api.py -v

# Run end-to-end flow
python -m backend.tests.run_e2e_flow
```

---

## License

This project is for educational and demonstration purposes.

---

Built for Thai Financial Advisors.  
Deterministic calculations. Intelligent explanations. Human oversight.

<![CDATA[<div align="center">

# 🏦 TaxCalamity

### Production-Grade Wealth Advisory & Tax Optimization Platform for Thailand

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-FF6F00?style=for-the-badge)](https://github.com/langchain-ai/langgraph)
[![CrewAI](https://img.shields.io/badge/CrewAI-Multi--Agent-8B5CF6?style=for-the-badge)](https://crewai.com)

---

**AI-powered multi-agent system** for Thai wealth advisors that combines  
**Typhoon NLP** · **Deterministic Tax Engine** · **Human-in-the-Loop Review** · **SEC Compliance Audit**

> ⚠️ **Design Principle**: AI does NOT calculate taxes. All tax computations are deterministic Python services.  
> AI can only **extract**, **explain**, **recommend**, and **validate** — never **invent** financial rules.

</div>

---

## 📋 Table of Contents

- [Architecture](#-architecture)
- [9-Agent System](#-9-agent-system)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [API Reference](#-api-reference)
- [Tax Engine](#-deterministic-tax-engine)
- [Project Structure](#-project-structure)
- [Design Decisions](#-design-decisions)
- [License](#-license)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 15)                        │
│  React 19 · TailwindCSS · ReactFlow · Recharts · Lucide Icons      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ REST API
┌────────────────────────────────▼────────────────────────────────────┐
│                        BACKEND (FastAPI)                            │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   LangGraph Orchestrator                      │   │
│  │                                                               │   │
│  │  Typhoon ─► Intake ─► Suitability ─► Tax Engine ─► Fund Rec  │   │
│  │                                         │                     │   │
│  │  Explanation ◄─────────────────────────┘                     │   │
│  │       │                                                       │   │
│  │  Human Review (PAUSE) ─► Compliance ─► Report                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Tax Engine   │  │ Fund Catalog │  │  Database (SQLAlchemy)   │  │
│  │ (Pure Python) │  │  (Seeded)    │  │  SQLite / PostgreSQL     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 9-Agent System

| # | Agent | Model | Role |
|---|-------|-------|------|
| 1 | **Typhoon Interpreter** | `typhoon-v2-70b-instruct` | Pre-process Thai financial conversations → structured JSON |
| 2 | **Client Intake** | `qwen3-32b` (Groq) | Extract demographics & financial figures from normalized text |
| 3 | **Suitability Analyst** | `qwen3-32b` (Groq) | Evaluate risk profile, investment horizon, asset allocation |
| 4 | **Tax Engine** | *Pure Python* | Deterministic Thai PIT calculation with progressive brackets |
| 5 | **Fund Recommender** | *Catalog Lookup* | Match SSF/RMF/ThaiESG funds to capacity & risk profile |
| 6 | **Explainability** | `qwen3-32b` (Groq) | Generate Why/Benefit/Risk/Assumptions per fund |
| 7 | **Human Review** | *Checkpoint* | Pause workflow for Wealth Advisor approval |
| 8 | **Compliance Auditor** | `qwen3-32b` (Groq) | SEC violation checks: return guarantees, risk mismatches |
| 9 | **Report Generator** | *Deterministic* | Render final advisory report & persist audit trail |

### Workflow Pipeline

```
Thai Input ──► Typhoon NLP ──► Client Intake ──► Suitability
                                                      │
                                                      ▼
Report ◄── Compliance ◄── Human Review ◄── Explanation ◄── Fund Selection ◄── Tax Engine
```

**Key Feature**: The workflow **pauses at Human Review** using LangGraph's `interrupt_after` mechanism. The advisor must explicitly approve the recommendation before the compliance audit runs.

---

## 🛠 Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI 0.110+ |
| Workflow Engine | LangGraph (StateGraph + MemorySaver) |
| Multi-Agent | CrewAI 0.28+ |
| LLM Provider | Groq (`qwen/qwen3-32b`) |
| Thai NLP | Typhoon (`typhoon-v2-70b-instruct`) |
| Database | SQLAlchemy 2.0 (SQLite dev / PostgreSQL prod) |
| Validation | Pydantic v2 |
| Vector DB | Qdrant (optional) |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | Next.js 15 |
| UI Library | React 19 |
| Styling | TailwindCSS 3.4 |
| Visualization | ReactFlow, Recharts |
| Icons | Lucide React |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 15 (Docker) |
| Cache | Redis 7 (Docker) |
| Vector Store | Qdrant (Docker) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional, for PostgreSQL/Redis)

### 1. Clone the Repository

```bash
git clone https://github.com/pusanada/taxCalamity.git
cd taxCalamity
git checkout prototype
```

### 2. Environment Variables

Create a `.env` file in the project root:

```env
# Application
APP_NAME=Chief Wealth Intelligence Platform
VERBOSE=false
DATABASE_URL=sqlite:///wealth_advisor.db

# Groq API (for Qwen reasoning agents)
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL=qwen/qwen3-32b

# Typhoon API (for Thai NLP pre-processing)
TYPHOON_API_KEY=your_typhoon_api_key_here
TYPHOON_MODEL=typhoon-v2-70b-instruct
TYPHOON_API_BASE=https://api.opentyphoon.ai/v1

# Infrastructure (when using Docker)
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/wealth_advisor
REDIS_URL=redis://localhost:6379
```

> 💡 **No API keys?** The platform gracefully falls back to deterministic mock responses for all agents, so you can explore the full workflow without any LLM provider.

### 3. Backend Setup

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Start the API server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000` with Swagger docs at `/docs`.

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000`.

### 5. Infrastructure (Optional)

```bash
# Start PostgreSQL, Redis, and Qdrant
cd backend
docker-compose up -d
```

Then update `DATABASE_URL` in `.env` to:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/wealth_advisor
```

---

## 📡 API Reference

### Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/api/v1/analyze` | Submit Thai financial text → runs full pipeline up to Human Review |
| `POST` | `/api/v1/recommend` | Approve & resume workflow → runs Compliance + Report |
| `GET` | `/api/v1/report/{session_id}` | Retrieve final advisory report |
| `GET` | `/api/v1/audit/{session_id}` | Full audit trail: agent runs, compliance flags, execution logs |
| `GET` | `/api/v1/session/{session_id}` | Session state with ReactFlow graph nodes/edges |

### Example: Analyze a Thai Client

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "raw_input_text": "ผมอายุ 35 ปี เงินเดือนประมาณแสนห้า โบนัสปีละ 4 เดือน ซื้อ RMF ไว้นิดหน่อย มีประกันชีวิตด้วย อยากลดภาษีเพิ่ม",
    "session_id": "demo-001"
  }'
```

### Example: Approve & Generate Report

```bash
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo-001"}'
```

### Response Structure

```json
{
  "session_id": "demo-001",
  "typhoon_result": {
    "normalized_thai": "...",
    "english_translation": "...",
    "confidence": 0.95,
    "missing_information": [],
    "entities": { ... }
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
    "detailed_calculations": { ... }
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

## 🧮 Deterministic Tax Engine

The tax engine is implemented as **pure Python functions** — no AI involvement.

### Thai Personal Income Tax Brackets

| Taxable Income (THB) | Rate |
|----------------------|------|
| 0 – 150,000 | 0% |
| 150,001 – 300,000 | 5% |
| 300,001 – 500,000 | 10% |
| 500,001 – 750,000 | 15% |
| 750,001 – 1,000,000 | 20% |
| 1,000,001 – 2,000,000 | 25% |
| 2,000,001 – 5,000,000 | 30% |
| 5,000,001+ | 35% |

### Deduction Limits

| Fund Type | Individual Cap | Joint Retirement Cap |
|-----------|---------------|---------------------|
| **SSF** | 30% of income, max ฿200,000 | SSF + RMF ≤ ฿500,000 |
| **RMF** | 30% of income, max ฿500,000 | SSF + RMF ≤ ฿500,000 |
| **ThaiESG** | 30% of income, max ฿300,000 | Separate cap |
| **Life Insurance** | Max ฿100,000 | — |

### Key Functions

```python
calculate_tax(taxable_income)              # Progressive bracket calculation
calculate_ssf_limit(income)                # SSF cap: min(30%, 200k)
calculate_rmf_limit(income)                # RMF cap: min(30%, 500k)
calculate_remaining_deduction_capacity()   # Joint cap-aware optimizer
calculate_tax_savings()                    # Before vs. after comparison
```

---

## 📁 Project Structure

```
taxCalamity/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   └── agents.py          # 9 CrewAI agent definitions & crew runners
│   │   ├── db/
│   │   │   ├── database.py        # SQLAlchemy engine, session, init
│   │   │   └── models.py          # Client, Profile, Recommendation, Audit, etc.
│   │   ├── graph/
│   │   │   └── workflow.py        # LangGraph StateGraph with 9 nodes
│   │   ├── schemas/
│   │   │   └── schemas.py         # Pydantic v2 request/response models
│   │   ├── services/
│   │   │   ├── tax_engine.py      # Deterministic Thai PIT calculator
│   │   │   ├── tax_service.py     # Tax service utilities
│   │   │   ├── fund_catalog.py    # Fund seeder & recommendation engine
│   │   │   └── fund_service.py    # Fund lookup services
│   │   ├── config.py              # Pydantic Settings from .env
│   │   └── main.py                # FastAPI app with 6 endpoints
│   ├── tests/
│   │   ├── test_api.py            # Automated API test suite
│   │   ├── test_advisory.py       # Advisory flow tests
│   │   └── run_e2e_flow.py        # End-to-end flow runner
│   ├── docker-compose.yml         # PostgreSQL + Redis + Qdrant
│   └── requirements.txt           # Python dependencies
├── frontend/
│   ├── app/
│   │   ├── page.tsx               # Main dashboard with ReactFlow
│   │   ├── layout.tsx             # Root layout with metadata
│   │   └── globals.css            # TailwindCSS + custom styles
│   ├── package.json               # Next.js 15 + React 19
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── tsconfig.json
├── .env                           # Environment variables (git-ignored)
├── .gitignore
└── README.md
```

---

## 🎯 Design Decisions

### Why AI Cannot Calculate Taxes

Thai tax law is complex but **deterministic**. Using LLMs for tax calculations introduces:
- **Hallucination risk** — LLMs may invent tax brackets or limits
- **Non-reproducibility** — Same input may produce different outputs
- **Audit failure** — Regulators require deterministic, verifiable calculations

**Our approach**: AI handles extraction and explanation; Python functions handle math.

### Why Typhoon + Qwen (Dual-LLM)

| Concern | Solution |
|---------|----------|
| Thai financial slang ("แสนห้า", "โบนัสสามสี่เดือน") | Typhoon — trained on Thai corpus |
| Structured reasoning, compliance logic | Qwen 3 32B via Groq — fast, accurate |
| Cost optimization | Typhoon runs once (intake), Qwen runs for reasoning |

### Why Human-in-the-Loop

Fund recommendations must be **reviewed by a licensed advisor** before compliance. The LangGraph workflow uses `interrupt_after=["human_review"]` to enforce this checkpoint.

### Why LangGraph over Plain CrewAI

- **State persistence** — Each node saves state to DB; sessions can be resumed
- **Conditional routing** — Failed nodes route to `END`, low-confidence inputs route to human review
- **Checkpointing** — `MemorySaver` enables pause/resume across HTTP requests

---

## 🧪 Testing

```bash
# Run API tests
cd backend
python -m pytest tests/test_api.py -v

# Run E2E flow
python -m backend.tests.run_e2e_flow
```

---

## 📄 License

This project is for educational and demonstration purposes.

---

<div align="center">

**Built with ❤️ for Thai Financial Advisors**

*Deterministic calculations. Intelligent explanations. Human oversight.*

</div>
]]>

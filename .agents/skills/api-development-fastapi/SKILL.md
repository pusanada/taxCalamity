---
name: api-development-fastapi
description: Design, implement, test, and document REST APIs using FastAPI for AI-powered financial applications, including async endpoints, authentication, request validation, background tasks, WebSocket support, and OpenAPI documentation. Triggers on requests about API design, FastAPI, REST endpoints, backend development, or API integration.
---

# api-development-fastapi

You have the `api-development-fastapi` skill. Use it when the user needs to build or improve a FastAPI backend for AI-Finance applications.

## Project Structure

```
ai_finance_api/
├── main.py                  # App entry point
├── config.py                # Settings (pydantic-settings)
├── dependencies.py          # Shared dependencies (auth, db)
├── routers/
│   ├── portfolio.py         # Portfolio endpoints
│   ├── signals.py           # Trading signal endpoints
│   ├── risk.py              # Risk metrics endpoints
│   ├── compliance.py        # Compliance/audit endpoints
│   └── models.py            # ML model management endpoints
├── services/
│   ├── portfolio_service.py # Business logic
│   ├── risk_service.py
│   └── model_service.py
├── agents/                  # Agent orchestration
├── schemas/                 # Pydantic request/response models
├── models/                  # DB models (SQLAlchemy/SQLModel)
├── middleware/              # Auth, logging, rate limiting
├── tests/
└── requirements.txt
```

## Application Setup

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from routers import portfolio, signals, risk, compliance

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load models, connect to DB
    await load_ml_models()
    await connect_database()
    yield
    # Shutdown: cleanup
    await disconnect_database()

app = FastAPI(
    title="AI-Finance API",
    description="Quantitative AI-powered financial analysis platform",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.yourfinance.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["Signals"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk"])
app.include_router(compliance.router, prefix="/api/v1/compliance", tags=["Compliance"])
```

## Schema Design (Pydantic)

```python
# schemas/portfolio.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class PortfolioOptimizationRequest(BaseModel):
    assets: list[str] = Field(..., min_items=2, max_items=100)
    risk_tolerance: float = Field(default=0.5, ge=0.0, le=1.0)
    constraints: Optional[dict] = None
    
    @validator('assets')
    def validate_tickers(cls, v):
        # Validate ticker format
        return [ticker.upper() for ticker in v]

class PredictionResponse(BaseModel):
    prediction: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    ci_lower: float
    ci_upper: float
    model_version: str
    computed_at: datetime
    requires_human_review: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "prediction": 0.123,
                "confidence": 0.82,
                "ci_lower": 0.081,
                "ci_upper": 0.165,
                "model_version": "v2.1.0",
                "computed_at": "2026-06-21T11:00:00Z",
                "requires_human_review": False
            }
        }
```

## Endpoint Patterns

### Async Endpoint with Background Task
```python
from fastapi import APIRouter, BackgroundTasks, Depends
from schemas.portfolio import PortfolioOptimizationRequest, OptimizationJobResponse
import uuid

router = APIRouter()

@router.post("/optimize", response_model=OptimizationJobResponse)
async def optimize_portfolio(
    request: PortfolioOptimizationRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(run_optimization, job_id, request, current_user.id)
    return {"job_id": job_id, "status": "queued"}

@router.get("/optimize/{job_id}")
async def get_optimization_result(job_id: str):
    result = await get_job_result(job_id)
    return result
```

### WebSocket for Real-Time Updates
```python
from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/ws/signals")
async def signals_websocket(websocket: WebSocket, token: str):
    await authenticate_ws(websocket, token)
    await websocket.accept()
    try:
        async for signal in signal_stream():
            await websocket.send_json(signal.dict())
    except WebSocketDisconnect:
        pass
```

### Streaming Response (for long-running ML)
```python
from fastapi.responses import StreamingResponse

@router.post("/analyze/stream")
async def stream_analysis(request: AnalysisRequest):
    async def generate():
        async for chunk in run_agent_pipeline(request):
            yield f"data: {chunk.json()}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

## Authentication & Security

```python
# middleware/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return await get_user(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Role-based access
def require_role(role: str):
    async def check_role(user = Depends(get_current_user)):
        if role not in user.roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_role
```

## Error Handling

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

@app.exception_handler(ComplianceViolation)
async def compliance_handler(request: Request, exc: ComplianceViolation):
    # Log to audit trail automatically
    await audit_log("COMPLIANCE_VIOLATION", str(exc), request)
    return JSONResponse(status_code=403, content={
        "detail": str(exc),
        "regulation": exc.regulation,
        "action": "blocked"
    })
```

## Testing

```python
# tests/test_portfolio.py
from fastapi.testclient import TestClient
import pytest
from main import app

client = TestClient(app)

def test_optimize_portfolio():
    response = client.post(
        "/api/v1/portfolio/optimize",
        json={"assets": ["AAPL", "GOOGL", "MSFT"], "risk_tolerance": 0.5},
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
```

## Running & Deployment

```bash
# Development
uvicorn main:app --reload --port 8000

# Production
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Docker
docker build -t ai-finance-api .
docker run -p 8000:8000 ai-finance-api
```

## Verification Checklist

- [ ] All endpoints have Pydantic schemas for request/response
- [ ] Authentication is required on all non-public endpoints
- [ ] Async endpoints use `async def` properly
- [ ] Background tasks used for long-running operations
- [ ] Error handling returns consistent JSON error format
- [ ] OpenAPI docs are accurate and complete
- [ ] All endpoints are tested with TestClient
- [ ] Rate limiting is applied to sensitive endpoints

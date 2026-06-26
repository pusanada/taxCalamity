import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from backend.app.config import settings
from backend.app.db.database import get_db, init_db, SessionLocal
from backend.app.db.models import (
    Client, 
    FinancialProfile, 
    Recommendation, 
    AuditLog, 
    AgentRun, 
    WorkflowState, 
    ComplianceFlag, 
    CrewExecution
)
from backend.app.schemas.schemas import (
    AdvisoryWorkflowRequest,
    AdvisoryWorkflowResponse,
    ClientIntakeSchema,
    SuitabilitySchema,
    TaxOutputSchema,
    FundRecommendationSchema,
    ExplanationSchema,
    ComplianceReportSchema
)
from backend.app.graph.workflow import app_workflow
from backend.app.services.fund_catalog import (
    sync_funds_from_sec,
    ensure_funds_available,
    FundCatalogUnavailable,
)
from backend.app.agents.agents import LiveServiceUnavailable
from backend.app.services.file_extract import extract_text_from_file
from backend.app.services.chat_service import (
    synthesize_chat_reply_v2,
    extract_entities_from_message,
    merge_chat_profile,
    should_escalate_to_advisor,
    build_escalate_suggested_action,
)
from backend.app.services.what_if_detector import detect_what_if, WHAT_IF_REFUSAL_TEMPLATE

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize the database only. The fund catalog is pulled lazily
    # from the live SEC API on the first /analyze (see ensure_funds_available);
    # no mock funds are ever seeded.
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade API for Wealth Advisory, Thai tax optimization, and human-in-the-loop audit.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware. Origins are configurable via the CORS_ORIGINS env var.
# allow_credentials must be False when origins is wildcard (browser rule).
_cors_origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=("*" not in _cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "api_version": "v1"
    }

@app.post("/api/v1/extract-file")
async def extract_file(file: UploadFile = File(...)):
    """
    POST /api/v1/extract-file
    Accepts a PDF, JPG, JPEG, or PNG of a Thai financial document and returns the
    transcribed text (via PyMuPDF for text PDFs, Groq vision for images/scans).
    The frontend drops this into the input box for advisor review before analysis.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 8 MB).")
    try:
        # Extraction is blocking (PDF parse + LLM call) -> run off the event loop.
        text, method = await run_in_threadpool(extract_text_from_file, file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read the file: {str(e)}")

    if not text or not text.strip():
        raise HTTPException(status_code=422, detail="No readable financial text found in the file.")

    return {"extracted_text": text, "source": file.filename, "method": method}


@app.post("/api/v1/chat")
async def chat(request: Dict[str, Any], db: Session = Depends(get_db)):
    """
    POST /api/v1/chat
    Client-facing Q&A grounded in a session's pipeline output. Read-only: it
    synthesizes/explains, never computes tax, never overrides compliance.
    Body: {"session_id": str, "message": str}
    """
    session_id = request.get("session_id")
    message = (request.get("message") or "").strip()
    if not session_id or not message:
        raise HTTPException(status_code=400, detail="session_id and message are required.")

    wf_state = db.query(WorkflowState).filter(WorkflowState.session_id == session_id).first()
    if not wf_state:
        raise HTTPException(status_code=404, detail="Advisory session not found.")

    # What-if intent gate (runs BEFORE the chat LLM). If the client asks a
    # hypothetical "invest X" scenario the chat must NOT compute, return a
    # structured CTA that re-runs the deterministic pipeline instead of a
    # dead-end refusal. No LLM call, no token spend, fully deterministic.
    what_if = detect_what_if(message)
    if what_if.detected:
        return {
            "reply": WHAT_IF_REFUSAL_TEMPLATE.format(amount_str=what_if.amount_str),
            "session_id": session_id,
            "suggested_action": what_if.to_suggested_action(),
        }

    # Cross-turn accumulation: extract any new facts the client stated in THIS
    # message and merge them into the session's persistent chat_profile, so
    # missing_fields shrinks turn by turn instead of being recomputed from the
    # frozen pipeline client_data every time (the repeated "ข้อมูลยังไม่ครบ" bug).
    state_data = wf_state.state_data or {}
    chat_profile = state_data.get("chat_profile") or {}
    try:
        new_entities = await run_in_threadpool(extract_entities_from_message, message)
    except LiveServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    chat_profile = merge_chat_profile(chat_profile, new_entities, message)
    try:
        # Reassign (not in-place mutate) so SQLAlchemy flags the JSON column dirty.
        wf_state.state_data = {**state_data, "chat_profile": chat_profile}
        db.commit()
    except Exception:
        db.rollback()

    escalate = should_escalate_to_advisor(message, chat_profile)

    try:
        # Synthesis is a blocking LLM call -> run off the event loop.
        reply = await run_in_threadpool(
            synthesize_chat_reply_v2, wf_state.state_data, chat_profile, message
        )
    except LiveServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat synthesis failed: {str(e)}")

    suggested_action = build_escalate_suggested_action() if escalate else None
    return {"reply": reply, "session_id": session_id, "suggested_action": suggested_action}


@app.post("/api/v1/analyze", response_model=AdvisoryWorkflowResponse)
async def analyze_profile(request: AdvisoryWorkflowRequest):
    """
    POST /api/v1/analyze
    Analyzes raw client conversational transcript, extracting profile, calculating taxes,
    selecting portfolio, generating explanations, and pauses at the Human Review checkpoint.
    """
    session_id = request.session_id or f"sess-{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": session_id}}
    
    # Check if there is an active workflow running for this session
    db = next(get_db())
    existing = db.query(WorkflowState).filter(WorkflowState.session_id == session_id).first()
    if existing:
        # If it is already paused at review, return the current state
        state_data = existing.state_data
        return AdvisoryWorkflowResponse(
            session_id=session_id,
            typhoon_result=state_data.get("typhoon_result"),
            client_data=state_data.get("client_data"),
            suitability=state_data.get("suitability"),
            tax_result=state_data.get("tax_result"),
            recommendation=state_data.get("recommendation"),
            explanation=state_data.get("explanation"),
            compliance=state_data.get("compliance"),
            status=existing.current_node,
            trace=state_data.get("trace", [])
        )
        
    initial_state = {
        "session_id": session_id,
        "raw_input_text": request.raw_input_text,
        "overrides": request.overrides or {},
        "client_data": None,
        "suitability": None,
        "tax_result": None,
        "recommendation": None,
        "explanation": None,
        "compliance": None,
        "status": "client_intake",
        "trace": [f"[Orchestrator] Initialized wealth advisory session: {session_id}"]
    }
    
    try:
        # Lazily pull the live SEC fund catalog on first need (no mock seed).
        # A SEC outage surfaces as a 503 'try again later', never fake funds.
        await ensure_funds_available(db)

        # Run workflow: will execute intake -> suitability -> tax -> recommendation -> explanation
        # and pause right before compliance (at the human_review node).
        final_state = app_workflow.invoke(initial_state, config=config)

        # Save trace logs
        return AdvisoryWorkflowResponse(
            session_id=session_id,
            typhoon_result=final_state.get("typhoon_result"),
            client_data=final_state.get("client_data"),
            suitability=final_state.get("suitability"),
            tax_result=final_state.get("tax_result"),
            recommendation=final_state.get("recommendation"),
            explanation=final_state.get("explanation"),
            compliance=final_state.get("compliance"),
            status=final_state.get("status"),
            trace=final_state.get("trace", [])
        )
    except (LiveServiceUnavailable, FundCatalogUnavailable) as e:
        # Live AI / SEC data unavailable after retries — tell the client to retry.
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {str(e)}")


@app.post("/api/v1/recommend", response_model=AdvisoryWorkflowResponse)
async def approve_recommendation(request: Dict[str, Any]):
    """
    POST /api/v1/recommend
    Resumes the LangGraph workflow after human approval. Moves to compliance checks
    and generates final reports.
    """
    session_id = request.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id parameter")
        
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        # Fetch current graph state
        current_state = app_workflow.get_state(config)
        if not current_state or not current_state.values:
            raise HTTPException(status_code=404, detail="Advisory session state not found")

        # Guard: only the genuine pre-compliance checkpoint may resume into the
        # audit. Early stops (needs_clarification / needs_review) lack the
        # tax/recommendation/explanation the compliance node needs — forcing
        # compliance there would crash. Return the current state instead so the
        # advisor supplies the missing info and re-runs.
        current_status = current_state.values.get("status")
        if current_status != "awaiting_review":
            vals = current_state.values
            return AdvisoryWorkflowResponse(
                session_id=session_id,
                typhoon_result=vals.get("typhoon_result"),
                client_data=vals.get("client_data"),
                suitability=vals.get("suitability"),
                tax_result=vals.get("tax_result"),
                recommendation=vals.get("recommendation"),
                explanation=vals.get("explanation"),
                compliance=vals.get("compliance"),
                status=current_status,
                trace=vals.get("trace", []),
            )

        # Update the status to direct the routing logic to 'compliance'
        app_workflow.update_state(config, {"status": "compliance", "trace": current_state.values.get("trace", []) + ["[Human Review Node] Advisor APPROVED portfolio. Proceeding to SEC Audit..."]}, as_node="human_review")
        
        # Resume flow (re-entry)
        final_state = app_workflow.invoke(None, config=config)
        
        return AdvisoryWorkflowResponse(
            session_id=session_id,
            typhoon_result=final_state.get("typhoon_result"),
            client_data=final_state.get("client_data"),
            suitability=final_state.get("suitability"),
            tax_result=final_state.get("tax_result"),
            recommendation=final_state.get("recommendation"),
            explanation=final_state.get("explanation"),
            compliance=final_state.get("compliance"),
            status=final_state.get("status"),
            trace=final_state.get("trace", [])
        )
    except (LiveServiceUnavailable, FundCatalogUnavailable) as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume workflow: {str(e)}")


@app.get("/api/v1/report/{session_id}")
def get_report(session_id: str, db: Session = Depends(get_db)):
    """
    GET /api/v1/report/{id}
    Retrieves the final wealth advisory report for a given session.
    """
    wf_state = db.query(WorkflowState).filter(WorkflowState.session_id == session_id).first()
    if not wf_state:
        raise HTTPException(status_code=404, detail="Advisory report session not found")
        
    data = wf_state.state_data
    if data.get("status") not in ["completed", "report"]:
        raise HTTPException(status_code=400, detail="Report generation is not complete. Human review may still be pending.")
        
    return {
        "session_id": session_id,
        "typhoon_result": data.get("typhoon_result"),
        "client_profile": data.get("client_data"),
        "suitability": data.get("suitability"),
        "tax_savings": data.get("tax_result"),
        "recommended_portfolio": data.get("recommendation"),
        "explanation": data.get("explanation"),
        "compliance": data.get("compliance"),
        "updated_at": wf_state.updated_at.isoformat()
    }


@app.post("/api/v1/admin/sync-funds")
async def sync_funds(db: Session = Depends(get_db)):
    """
    POST /api/v1/admin/sync-funds
    Triggers an asynchronous synchronization with the Thai SEC API
    to update the local database cache of active RMF, SSF, and ThaiESG funds.
    """
    try:
        result = await sync_funds_from_sec(db)
        if result.get("status") == "failed":
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synchronization failed: {str(e)}")


@app.get("/api/v1/audit/{session_id}")
def get_audit_trail(session_id: str, db: Session = Depends(get_db)):
    """
    GET /api/v1/audit/{id}
    Retrieves full audit logs, agent runs payloads, and compliance flags.
    """
    logs = db.query(AuditLog).filter(AuditLog.session_id == session_id).all()
    flags = db.query(ComplianceFlag).filter(ComplianceFlag.session_id == session_id).all()
    runs = db.query(AgentRun).filter(AgentRun.session_id == session_id).all()
    execution = db.query(CrewExecution).filter(CrewExecution.session_id == session_id).first()
    
    return {
        "session_id": session_id,
        "execution_summary": {
            "status": execution.status if execution else "PENDING",
            "tokens_used": execution.tokens_used if execution else 0,
            "cost_usd": execution.cost if execution else 0.0,
            "trace": execution.full_trace if execution else []
        },
        "audit_logs": [
            {
                "agent_name": l.agent_name,
                "action": l.action,
                "detail": l.detail,
                "is_compliant": l.is_compliant,
                "timestamp": l.timestamp.isoformat()
            } for l in logs
        ],
        "compliance_flags": [
            {
                "rule_name": f.rule_name,
                "description": f.description,
                "severity": f.severity,
                "status": f.status,
                "created_at": f.created_at.isoformat()
            } for f in flags
        ],
        "agent_runs": [
            {
                "agent_role": r.agent_role,
                "input": r.input_payload,
                "output": r.output_payload,
                "timestamp": r.timestamp.isoformat()
            } for r in runs
        ]
    }


@app.get("/api/v1/session/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    """
    GET /api/v1/session/{id}
    Retrieves the raw session data and returns custom React Flow nodes and edges
    representing the active path of the LangGraph workflow.
    """
    wf_state = db.query(WorkflowState).filter(WorkflowState.session_id == session_id).first()
    if not wf_state:
        raise HTTPException(status_code=404, detail="Session not found")
        
    state_data = wf_state.state_data
    current_node = wf_state.current_node
    
    # 1. Define nodes for React Flow
    flow_steps = [
        ("typhoon_interpreter", "Typhoon Interpreter"),
        ("client_intake", "Client Intake Agent"),
        ("suitability", "Suitability Analyst"),
        ("tax_engine", "Tax Deterministic Core"),
        ("recommendation", "Fund Selection Core"),
        ("explanation", "Narrative Interpreter"),
        ("human_review", "Human Review Point"),
        ("compliance", "SEC Compliance Auditor"),
        ("report", "Report Formatter")
    ]
    
    nodes = []
    edges = []
    
    # Map step coordinates and status
    active_found = False
    for idx, (node_id, label) in enumerate(flow_steps):
        # Determine status of each node in the path
        if node_id == current_node:
            status = "active"
            active_found = True
        elif not active_found:
            status = "completed"
        else:
            status = "pending"
            
        nodes.append({
            "id": node_id,
            "data": {"label": label, "status": status},
            "position": {"x": 250, "y": idx * 80},
            "style": {
                "background": "#1e293b" if status == "pending" else ("#4f46e5" if status == "active" else "#047857"),
                "color": "#fff",
                "border": "1px solid " + ("#475569" if status == "pending" else ("#818cf8" if status == "active" else "#34d399")),
                "borderRadius": "8px",
                "padding": "10px",
                "fontSize": "12px",
                "fontWeight": "bold",
                "boxShadow": "0 0 15px rgba(79, 70, 229, 0.4)" if status == "active" else "none"
            }
        })
        
        # Link to next node
        if idx < len(flow_steps) - 1:
            edges.append({
                "id": f"e-{node_id}-{flow_steps[idx+1][0]}",
                "source": node_id,
                "target": flow_steps[idx+1][0],
                "animated": (status == "completed"),
                "style": {"stroke": "#34d399" if status == "completed" else "#475569"}
            })
            
    return {
        "session_id": session_id,
        "current_node": current_node,
        "state_data": state_data,
        "flow_graph": {
            "nodes": nodes,
            "edges": edges
        }
    }

from typing import TypedDict, List, Optional, Dict, Any
import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
import datetime

from backend.app.config import settings

from backend.app.schemas.schemas import (
    ClientIntakeSchema,
    SuitabilitySchema,
    TaxOutputSchema,
    FundRecommendationSchema,
    ExplanationSchema,
    ComplianceReportSchema,
    TyphoonOutputSchema
)
from backend.app.agents.agents import (
    run_typhoon_interpreter_crew,
    run_intake_crew,
    run_suitability_crew,
    run_explanation_crew,
    run_compliance_audit_crew
)
from backend.app.services.tax_engine import (
    calculate_remaining_deduction_capacity,
    calculate_tax_savings,
    calculate_tax,
    calculate_ssf_limit,
    calculate_rmf_limit
)
from backend.app.services.fund_catalog import recommend_funds
from backend.app.db.database import SessionLocal
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

# ----------------- STATE DEFINITIONS -----------------

class AdvisoryState(TypedDict):
    session_id: str
    raw_input_text: str
    typhoon_result: Optional[TyphoonOutputSchema]
    client_data: Optional[ClientIntakeSchema]
    suitability: Optional[SuitabilitySchema]
    tax_result: Optional[TaxOutputSchema]
    recommendation: Optional[FundRecommendationSchema]
    explanation: Optional[ExplanationSchema]
    compliance: Optional[ComplianceReportSchema]
    status: str
    trace: List[str]

# ----------------- DB PERSISTENCE HELPERS -----------------

def log_agent_run_to_db(session_id: str, role: str, inputs: Any, outputs: Any):
    """
    Logs agent run details to the database.
    """
    db = SessionLocal()
    try:
        run = AgentRun(
            session_id=session_id,
            agent_role=role,
            input_payload=inputs if isinstance(inputs, dict) else {"text": str(inputs)},
            output_payload=outputs if isinstance(outputs, dict) else (outputs.model_dump() if hasattr(outputs, "model_dump") else {"result": str(outputs)})
        )
        db.add(run)
        db.commit()
    except Exception as e:
        print(f"Error logging agent run: {str(e)}")
        db.rollback()
    finally:
        db.close()


def save_workflow_state_to_db(session_id: str, current_node: str, state: AdvisoryState):
    """
    Saves the intermediate state data of the LangGraph execution.
    """
    db = SessionLocal()
    try:
        wf_state = db.query(WorkflowState).filter(WorkflowState.session_id == session_id).first()
        serializable_state = {
            "status": state.get("status"),
            "trace": state.get("trace"),
            "typhoon_result": state.get("typhoon_result").model_dump() if state.get("typhoon_result") else None,
            "client_data": state.get("client_data").model_dump() if state.get("client_data") else None,
            "suitability": state.get("suitability").model_dump() if state.get("suitability") else None,
            "tax_result": state.get("tax_result").model_dump() if state.get("tax_result") else None,
            "recommendation": state.get("recommendation").model_dump() if state.get("recommendation") else None,
            "explanation": state.get("explanation").model_dump() if state.get("explanation") else None,
            "compliance": state.get("compliance").model_dump() if state.get("compliance") else None,
        }
        
        if not wf_state:
            wf_state = WorkflowState(
                session_id=session_id,
                current_node=current_node,
                state_data=serializable_state
            )
            db.add(wf_state)
        else:
            wf_state.current_node = current_node
            wf_state.state_data = serializable_state
            wf_state.updated_at = datetime.datetime.utcnow()
        db.commit()
    except Exception as e:
        print(f"Error saving workflow state: {str(e)}")
        db.rollback()
    finally:
        db.close()


# ----------------- LANGGRAPH NODE EXECUTORS -----------------

def typhoon_interpreter_node(state: AdvisoryState) -> AdvisoryState:
    state["trace"].append("[Typhoon Interpreter Node] Pre-processing Thai conversational input...")
    try:
        typhoon_result = run_typhoon_interpreter_crew(state["raw_input_text"])
        state["typhoon_result"] = typhoon_result
        state["trace"].append(
            f"[Typhoon Interpreter Node] Processed. Confidence: {typhoon_result.confidence:.2f}. "
            f"English Translation: \"{typhoon_result.english_translation}\""
        )
        
        # Log Agent Run
        log_agent_run_to_db(state["session_id"], "Thai Financial Interpreter Agent", state["raw_input_text"], typhoon_result)
        
        # Quality Control: a low confidence score is a NON-BLOCKING warning.
        # We still run the full pipeline (defaults fill any gaps) so the advisor
        # can review a complete recommendation at the human_review checkpoint,
        # where the low-confidence flag is surfaced. Branching straight to
        # human_review here would skip intake/tax/recommendation and break the
        # downstream compliance step.
        if typhoon_result.confidence < 0.80:
            state["trace"].append(
                f"[Typhoon Interpreter Node] WARNING: Confidence {typhoon_result.confidence:.2f} is below the 0.80 "
                f"threshold. Recommendation built on defaults for missing fields; manual verification advised."
            )
        state["status"] = "client_intake"
    except Exception as e:
        state["trace"].append(f"[Typhoon Interpreter Node] Failed: {str(e)}")
        state["status"] = "failed"
        
    save_workflow_state_to_db(state["session_id"], "typhoon_interpreter", state)
    return state


def client_intake_node(state: AdvisoryState) -> AdvisoryState:
    state["trace"].append("[Intake Node] Processing profile mapping...")
    try:
        client_data = run_intake_crew(state["typhoon_result"])
        state["client_data"] = client_data
        state["trace"].append(f"[Intake Node] Profile mapped. Age: {client_data.age}, Goal: {client_data.goal}, Monthly Income: ฿{client_data.monthly_income:,.2f}")
        
        # Log Agent Run & Create Client Record
        log_agent_run_to_db(state["session_id"], "Client Intake Agent", state["typhoon_result"], client_data)
        
        db = SessionLocal()
        try:
            # Avoid duplicate clients using unique email based on session_id
            client_email = f"client-{state['session_id']}@example.com"
            client = db.query(Client).filter(Client.email == client_email).first()
            if not client:
                client = Client(name=f"Client-{state['session_id'][:8]}", email=client_email)
                db.add(client)
                db.flush()
            
            # Save profile
            profile = FinancialProfile(
                client_id=client.id,
                age=client_data.age,
                monthly_income=client_data.monthly_income,
                bonus_months=client_data.bonus_months,
                existing_rmf=client_data.existing_rmf,
                existing_ssf=client_data.existing_ssf,
                life_insurance=client_data.life_insurance,
                goal=client_data.goal,
                risk_profile=client_data.risk_profile
            )
            db.add(profile)
            db.commit()
        finally:
            db.close()
            
        state["status"] = "suitability"
    except Exception as e:
        state["trace"].append(f"[Intake Node] Failed: {str(e)}")
        state["status"] = "failed"
        
    save_workflow_state_to_db(state["session_id"], "client_intake", state)
    return state


def suitability_node(state: AdvisoryState) -> AdvisoryState:
    state["trace"].append("[Suitability Node] Evaluating investment horizon and asset allocation...")
    try:
        suitability = run_suitability_crew(state["client_data"])
        state["suitability"] = suitability
        state["trace"].append(f"[Suitability Node] Evaluated. Horizon: {suitability.investment_horizon}, Allocation: {suitability.recommended_allocation}")
        
        log_agent_run_to_db(state["session_id"], "Suitability Agent", state["client_data"], suitability)
        
        # Update client profile in DB with determined risk
        db = SessionLocal()
        try:
            client_email = f"client-{state['session_id']}@example.com"
            client = db.query(Client).filter(Client.email == client_email).first()
            if client:
                profile = db.query(FinancialProfile).filter(FinancialProfile.client_id == client.id).order_by(FinancialProfile.created_at.desc()).first()
                if profile:
                    profile.risk_profile = suitability.risk_profile
                    db.commit()
        finally:
            db.close()
            
        state["status"] = "tax_engine"
    except Exception as e:
        state["trace"].append(f"[Suitability Node] Failed: {str(e)}")
        state["status"] = "failed"
        
    save_workflow_state_to_db(state["session_id"], "suitability", state)
    return state


def tax_engine_node(state: AdvisoryState) -> AdvisoryState:
    state["trace"].append("[Tax Engine Node] Running deterministic tax optimization formulas...")
    try:
        client = state["client_data"]
        
        # Determine total income (12 months salary + bonus salary)
        total_income = (client.monthly_income * 12) + (client.monthly_income * client.bonus_months)
        
        # Standard personal and expense deductions
        personal_deduction = 60000.0
        expense_deduction = min(total_income * 0.5, 100000.0)
        
        # Call deterministic Python tax capacities
        capacity = calculate_remaining_deduction_capacity(
            income=total_income,
            existing_ssf=client.existing_ssf,
            existing_rmf=client.existing_rmf
        )
        
        # Compute Deductions Before Optimization (existing deductions only)
        deductions_before = (
            personal_deduction 
            + expense_deduction 
            + min(client.existing_ssf, calculate_ssf_limit(total_income)) 
            + min(client.existing_rmf, calculate_rmf_limit(total_income))
            + min(client.life_insurance, 100000.0)
        )
        
        # Deductions After Optimization (with maximized SSF, RMF, and ThaiESG)
        opt_ssf = client.existing_ssf + capacity["allowed_additional_ssf"]
        opt_rmf = client.existing_rmf + capacity["allowed_additional_rmf"]
        opt_thaiesg = capacity["allowed_additional_thaiesg"] # Target fresh buy
        
        deductions_after = (
            personal_deduction 
            + expense_deduction 
            + opt_ssf 
            + opt_rmf 
            + opt_thaiesg
            + min(client.life_insurance, 100000.0)
        )
        
        # Progressive tax calculation
        tax_before = calculate_tax(total_income - deductions_before)
        tax_after = calculate_tax(total_income - deductions_after)
        saving = calculate_tax_savings(total_income, deductions_before, deductions_after)
        
        tax_result = TaxOutputSchema(
            tax_before=tax_before,
            tax_after=tax_after,
            saving=saving,
            detailed_calculations={
                "assessable_income": total_income,
                "deductions_before": deductions_before,
                "deductions_after": deductions_after,
                "optimization_purchases": {
                    "ssf_additional": capacity["allowed_additional_ssf"],
                    "rmf_additional": capacity["allowed_additional_rmf"],
                    "thaiesg_additional": capacity["allowed_additional_thaiesg"],
                    "total_additional_investment": capacity["total_additional_capacity"]
                }
            }
        )
        
        state["tax_result"] = tax_result
        state["trace"].append(f"[Tax Engine Node] Calculated. Savings: ฿{saving:,.2f}, Target investment: ฿{capacity['total_additional_capacity']:,.2f}")
        state["status"] = "recommendation"
    except Exception as e:
        state["trace"].append(f"[Tax Engine Node] Failed: {str(e)}")
        state["status"] = "failed"
        
    save_workflow_state_to_db(state["session_id"], "tax_engine", state)
    return state


def recommendation_node(state: AdvisoryState) -> AdvisoryState:
    state["trace"].append("[Recommendation Node] Fetching fund catalog and mapping allocations...")
    try:
        db = SessionLocal()
        try:
            opt_purchases = state["tax_result"].detailed_calculations.get("optimization_purchases", {})
            ssf_needed = opt_purchases.get("ssf_additional", 0.0)
            rmf_needed = opt_purchases.get("rmf_additional", 0.0)
            thaiesg_needed = opt_purchases.get("thaiesg_additional", 0.0)
            
            risk = state["client_data"].risk_profile
            goal = state["client_data"].goal
            
            recommended_list = []
            
            # SSF Fund
            if ssf_needed > 0:
                recommended_list.extend(recommend_funds(db, risk, goal, "SSF", ssf_needed))
            # RMF Fund
            if rmf_needed > 0:
                recommended_list.extend(recommend_funds(db, risk, goal, "RMF", rmf_needed))
            # ThaiESG Fund
            if thaiesg_needed > 0:
                recommended_list.extend(recommend_funds(db, risk, goal, "ThaiESG", thaiesg_needed))
                
            # Normalize percentage weights
            total_amt = sum(item["amount_thb"] for item in recommended_list)
            if total_amt > 0:
                for item in recommended_list:
                    item["allocation_percentage"] = round((item["amount_thb"] / total_amt) * 100.0, 2)
            
            # Map dict elements to FundDetail schemas
            from backend.app.schemas.schemas import FundDetail
            fund_details = [FundDetail(**item) for item in recommended_list]
            
            recommendation = FundRecommendationSchema(recommended_funds=fund_details)
            state["recommendation"] = recommendation
            state["trace"].append(f"[Recommendation Node] Selected {len(fund_details)} funds matching constraints.")
            
            # Save recommendation to database
            client_email = f"client-{state['session_id']}@example.com"
            client = db.query(Client).filter(Client.email == client_email).first()
            if client:
                rec_db = Recommendation(
                    client_id=client.id,
                    recommended_funds=[f.model_dump() for f in fund_details],
                    reasoning=f"Optimized portfolio for {risk} client seeking {goal}."
                )
                db.add(rec_db)
                db.commit()
        finally:
            db.close()
            
        state["status"] = "explanation"
    except Exception as e:
        state["trace"].append(f"[Recommendation Node] Failed: {str(e)}")
        state["status"] = "failed"
        
    save_workflow_state_to_db(state["session_id"], "recommendation", state)
    return state


def explanation_node(state: AdvisoryState) -> AdvisoryState:
    state["trace"].append("[Explanation Node] Formulating narrative justifications...")
    try:
        explanation = run_explanation_crew(
            state["client_data"],
            state["tax_result"],
            state["recommendation"]
        )
        state["explanation"] = explanation
        state["trace"].append("[Explanation Node] Interpretations generated for recommended portfolios.")
        
        log_agent_run_to_db(state["session_id"], "Explainability Agent", state["recommendation"], explanation)
        state["status"] = "human_review"
    except Exception as e:
        state["trace"].append(f"[Explanation Node] Failed: {str(e)}")
        state["status"] = "failed"
        
    save_workflow_state_to_db(state["session_id"], "explanation", state)
    return state


def human_review_node(state: AdvisoryState) -> AdvisoryState:
    """
    This is the checkpoint node where the workflow yields execution control.
    The status is set to awaiting_review.
    """
    state["trace"].append("[Human Review Node] State checkpoint reached. Yielding control to Wealth Advisor...")
    # This state change signals the API controller that we have completed phase 1
    state["status"] = "awaiting_review"
    save_workflow_state_to_db(state["session_id"], "human_review", state)
    return state


def compliance_node(state: AdvisoryState) -> AdvisoryState:
    state["trace"].append("[Compliance Node] Initiating SEC regulatory check and return audit...")
    try:
        # Pass the client's original demand (translation + raw text) so the auditor
        # can catch client-side guarantee demands scrubbed from the explanation.
        typ = state.get("typhoon_result")
        client_context = " | ".join(filter(None, [
            typ.english_translation if typ else None,
            typ.normalized_thai if typ else None,
            state.get("raw_input_text"),
        ]))
        compliance = run_compliance_audit_crew(
            state["client_data"],
            state["tax_result"],
            state["recommendation"],
            state["explanation"],
            client_context,
        )
        state["compliance"] = compliance
        
        log_agent_run_to_db(state["session_id"], "Compliance Agent", state["explanation"], compliance)
        
        # DB log audit trails & flags
        db = SessionLocal()
        try:
            audit = AuditLog(
                session_id=state["session_id"],
                agent_name="Compliance Agent",
                action="AUDIT_COMPLIANCE",
                detail=f"Compliance check completed. Status: {compliance.status}",
                is_compliant=(compliance.status == "approved")
            )
            db.add(audit)
            
            # Save violations as flags
            for violation in compliance.violations:
                flag = ComplianceFlag(
                    session_id=state["session_id"],
                    rule_name="Regulatory Rule Check",
                    description=violation,
                    severity="VIOLATION",
                    status="FLAGGED"
                )
                db.add(flag)
            db.commit()
        finally:
            db.close()
            
        if compliance.status == "approved":
            state["trace"].append("[Compliance Node] Audit APPROVED. No SEC or return guarantee violations detected.")
            state["status"] = "report"
        else:
            state["trace"].append(f"[Compliance Node] Audit REJECTED. Caught {len(compliance.violations)} violations.")
            state["status"] = "non_compliant"
    except Exception as e:
        state["trace"].append(f"[Compliance Node] Failed: {str(e)}")
        state["status"] = "failed"
        
    save_workflow_state_to_db(state["session_id"], "compliance", state)
    return state


def report_node(state: AdvisoryState) -> AdvisoryState:
    state["trace"].append("[Report Node] Rendering final wealth advisory report...")
    state["status"] = "completed"
    
    # Save CrewExecution summary in DB
    db = SessionLocal()
    try:
        # Calculate final compliance check status
        is_passed = (state["compliance"].status == "approved" if state.get("compliance") else False)
        exec_record = CrewExecution(
            session_id=state["session_id"],
            status="COMPLETED" if is_passed else "REJECTED",
            run_by="Wealth Orchestrator",
            tokens_used=15000,
            cost=0.018,
            full_trace=state["trace"]
        )
        db.add(exec_record)
        db.commit()
    finally:
        db.close()
        
    state["trace"].append("[Report Node] Wealth Report Session finished successfully.")
    save_workflow_state_to_db(state["session_id"], "report", state)
    return state


# ----------------- LANGGRAPH FLOW COMPOSITION -----------------

def route_flow(state: AdvisoryState) -> str:
    status = state.get("status")
    if status == "client_intake":
        return "client_intake"
    elif status == "suitability":
        return "suitability"
    elif status == "tax_engine":
        return "tax_engine"
    elif status == "recommendation":
        return "recommendation"
    elif status == "explanation":
        return "explanation"
    elif status == "human_review":
        return "human_review"
    elif status == "compliance":
        return "compliance"
    elif status == "report":
        return "report"
    return END

workflow = StateGraph(AdvisoryState)

# Register Nodes
workflow.add_node("typhoon_interpreter", typhoon_interpreter_node)
workflow.add_node("client_intake", client_intake_node)
workflow.add_node("suitability", suitability_node)
workflow.add_node("tax_engine", tax_engine_node)
workflow.add_node("recommendation", recommendation_node)
workflow.add_node("explanation", explanation_node)
workflow.add_node("human_review", human_review_node)
workflow.add_node("compliance", compliance_node)
workflow.add_node("report", report_node)

# Set entry point
workflow.set_entry_point("typhoon_interpreter")

# Configure state edges
workflow.add_conditional_edges("typhoon_interpreter", route_flow, {
    "client_intake": "client_intake",
    "human_review": "human_review",
    "__end__": END
})
workflow.add_conditional_edges("client_intake", route_flow, {"suitability": "suitability", "__end__": END})
workflow.add_conditional_edges("suitability", route_flow, {"tax_engine": "tax_engine", "__end__": END})
workflow.add_conditional_edges("tax_engine", route_flow, {"recommendation": "recommendation", "__end__": END})
workflow.add_conditional_edges("recommendation", route_flow, {"explanation": "explanation", "__end__": END})
workflow.add_conditional_edges("explanation", route_flow, {"human_review": "human_review", "__end__": END})

# Set human review pause state
# When compiled, we will specify that execution interrupts AFTER human_review node
workflow.add_conditional_edges("human_review", route_flow, {
    "__end__": END, # Yield control when routing from human_review node
    "compliance": "compliance"
})

workflow.add_conditional_edges("compliance", route_flow, {
    "report": "report",
    "__end__": END
})

workflow.add_conditional_edges("report", route_flow, {
    "__end__": END
})

# Compile graph using a SQLite-backed checkpointer so pause/resume survives
# across separate HTTP requests (and process restarts within an instance).
# check_same_thread=False because FastAPI serves handlers from a threadpool.
_checkpoint_conn = sqlite3.connect(settings.CHECKPOINT_DB_PATH, check_same_thread=False)
# Allow our own Pydantic schema module to round-trip through the checkpoint
# serializer. Without this, newer langgraph versions will block deserializing
# these custom types (currently only a warning).
_SCHEMA_MODULE = "backend.app.schemas.schemas"
_serde = JsonPlusSerializer(
    allowed_msgpack_modules=[
        (_SCHEMA_MODULE, name)
        for name in (
            "TyphoonEntitiesSchema",
            "TyphoonOutputSchema",
            "ClientIntakeSchema",
            "SuitabilitySchema",
            "TaxOutputSchema",
            "FundDetail",
            "FundRecommendationSchema",
            "ExplanationDetail",
            "ExplanationSchema",
            "ComplianceReportSchema",
        )
    ]
)
checkpointer = SqliteSaver(_checkpoint_conn, serde=_serde)
app_workflow = workflow.compile(
    checkpointer=checkpointer,
    interrupt_after=["human_review"]
)

import json
import sys
import io

# Force stdout to output in UTF-8 to prevent Windows terminal charmap errors
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.app.db.database import init_db, SessionLocal
from backend.app.graph.workflow import app_workflow
from backend.app.db.models import Client, Recommendation, AuditLog, CrewExecution, WorkflowState

def run_e2e():
    print("=== INITIALIZING LOCAL DATABASE ===")
    from backend.app.db.database import engine, Base
    from backend.app.services.fund_catalog import seed_funds
    Base.metadata.drop_all(bind=engine)
    init_db()
    db_seed = SessionLocal()
    seed_funds(db_seed)
    db_seed.close()
    
    print("\n=== RUNNING FLOW FOR CLIENT A (COMPLIANT CASE) ===")
    client_a_input = "ลูกค้าอายุ 42 รายได้ 180,000/เดือน โบนัส 6 เดือน SSF 100,000 RMF 0 มีประกันชีวิต 50,000 ความเสี่ยงระดับปานกลาง"
    session_id_a = "session-master-client-a-compliant"
    config_a = {"configurable": {"thread_id": session_id_a}}
    
    # Clean previous run state in DB if exists to prevent duplicates
    db = SessionLocal()
    db.query(WorkflowState).filter(WorkflowState.session_id == session_id_a).delete()
    db.query(CrewExecution).filter(CrewExecution.session_id == session_id_a).delete()
    db.commit()
    db.close()
    
    state_a = {
        "session_id": session_id_a,
        "raw_input_text": client_a_input,
        "client_data": None,
        "suitability": None,
        "tax_result": None,
        "recommendation": None,
        "explanation": None,
        "compliance": None,
        "trace": [],
        "status": "client_intake"
    }
    
    # 1. Run up to human review checkpoint (interrupt after human_review node)
    print("Executing Phase 1 (Intake -> Suitability -> Tax -> Recommendation -> Explanation -> Human Review checkpoint)...")
    res_a = app_workflow.invoke(state_a, config=config_a)
    print("Graph node status reached:", res_a["status"])
    print("Tax savings calculated: THB", res_a["tax_result"].saving if res_a["tax_result"] else 0.0)
    print("Explanation items generated:", len(res_a["explanation"].explanations) if res_a["explanation"] else 0)
    
    # 2. Simulate manual approval to resume
    print("Simulating advisor manual approval (resuming LangGraph checkpoint)...")
    # Fetch current values, update status to 'compliance' to route next, and invoke
    current_state = app_workflow.get_state(config_a)
    app_workflow.update_state(config_a, {"status": "compliance", "trace": current_state.values.get("trace", []) + ["[Human Review Node] Simulating Advisor Manual Approval."]}, as_node="human_review")
    
    # Execute Phase 2 (Compliance -> Report -> END)
    res_a_final = app_workflow.invoke(None, config=config_a)
    print("Workflow final status:", res_a_final["status"])
    print("Compliance check result:", res_a_final["compliance"].status if res_a_final["compliance"] else "N/A")
    print("Execution trace logs:")
    for log in res_a_final["trace"]:
        print(f"  {log}")

    print("\n=== RUNNING FLOW FOR CLIENT C (NON-COMPLIANT GUARANTEE CASE) ===")
    client_c_input = "ลูกค้าอายุ 55 รายได้ 120,000/เดือน ความเสี่ยงต่ำ ต้องแนะนำกองทุนที่รับประกันผลตอบแทนไม่ต่ำกว่า 15% เท่านั้น ห้ามขาดทุนเด็ดขาด"
    session_id_c = "session-master-client-c-violating"
    config_c = {"configurable": {"thread_id": session_id_c}}
    
    db = SessionLocal()
    db.query(WorkflowState).filter(WorkflowState.session_id == session_id_c).delete()
    db.query(CrewExecution).filter(CrewExecution.session_id == session_id_c).delete()
    db.commit()
    db.close()
    
    state_c = {
        "session_id": session_id_c,
        "raw_input_text": client_c_input,
        "client_data": None,
        "suitability": None,
        "tax_result": None,
        "recommendation": None,
        "explanation": None,
        "compliance": None,
        "trace": [],
        "status": "client_intake"
    }
    
    # Run Phase 1
    res_c = app_workflow.invoke(state_c, config=config_c)
    print("Graph node status reached:", res_c["status"])
    
    # Resume Phase 2
    print("Simulating advisor manual approval to run compliance checks...")
    current_state_c = app_workflow.get_state(config_c)
    app_workflow.update_state(config_c, {"status": "compliance", "trace": current_state_c.values.get("trace", []) + ["[Human Review Node] Simulating Advisor Manual Approval."]}, as_node="human_review")
    
    res_c_final = app_workflow.invoke(None, config=config_c)
    print("Workflow final status:", res_c_final["status"])
    print("Compliance check result:", res_c_final["compliance"].status if res_c_final["compliance"] else "N/A")
    print("Violations caught by Compliance Officer Agent:")
    if res_c_final["compliance"]:
        for violation in res_c_final["compliance"].violations:
            print(f"  ❌ {violation}")

    print("\n=== VERIFYING PERSISTED DATABASE RECORDS ===")
    db = SessionLocal()
    try:
        clients = db.query(Client).all()
        print(f"Total clients created in database: {len(clients)}")
        for c in clients:
            print(f"  - Client ID: {c.id}, Name: {c.name}, Email: {c.email}")
            
        recs = db.query(Recommendation).all()
        print(f"Recommendations saved: {len(recs)}")
        for rc in recs:
            print(f"  - Client ID: {rc.client_id}, Portfolio funds: {[f['fund_code'] for f in rc.recommended_funds]}")
            
        audit_logs = db.query(AuditLog).all()
        print(f"Audit log entries written: {len(audit_logs)}")
        for log in audit_logs:
            print(f"  - [{log.agent_name}] Action: {log.action}, Compliant: {log.is_compliant}")
    finally:
        db.close()

if __name__ == "__main__":
    run_e2e()

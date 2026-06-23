import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import SessionLocal, init_db, engine, Base

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # Reset database structure
    Base.metadata.drop_all(bind=engine)
    init_db()
    # Seed database
    from backend.app.services.fund_catalog import seed_funds
    db = SessionLocal()
    seed_funds(db)
    db.close()
    yield

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "api_version" in data

def test_analyze_and_recommend_compliant_flow():
    session_id = "api-test-compliant-session"
    payload = {
        "raw_input_text": "ลูกค้าอายุ 42 รายได้ 180,000/เดือน โบนัส 6 เดือน SSF 100,000 RMF 0 มีประกันชีวิต 50,000 ความเสี่ยงระดับปานกลาง",
        "session_id": session_id
    }
    
    # 1. Initial intake and processing pause
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    if data.get("status") == "failed":
        print("TRACE ON FAILURE FOR test_analyze_and_recommend_compliant_flow:")
        for t in data.get("trace", []):
            print("  ", t)
    assert data["session_id"] == session_id
    assert data["status"] == "awaiting_review"
    assert data["client_data"]["age"] == 42
    assert data["client_data"]["monthly_income"] == 180000.0
    assert data["tax_result"]["saving"] == 210000.0
    assert len(data["recommendation"]["recommended_funds"]) > 0
    assert data["explanation"] is not None

    # 2. Get active workflow graph nodes and links
    response = client.get(f"/api/v1/session/{session_id}")
    assert response.status_code == 200
    graph_data = response.json()
    assert graph_data["session_id"] == session_id
    assert graph_data["current_node"] == "human_review"
    assert "flow_graph" in graph_data
    assert len(graph_data["flow_graph"]["nodes"]) > 0

    # 3. Submit advisor approval to proceed to compliance check
    app_payload = {"session_id": session_id}
    response = client.post("/api/v1/recommend", json=app_payload)
    assert response.status_code == 200
    rec_data = response.json()
    assert rec_data["status"] == "completed"
    assert rec_data["compliance"]["status"] == "approved"
    assert len(rec_data["compliance"]["violations"]) == 0

    # 4. Fetch finalized advisory report
    response = client.get(f"/api/v1/report/{session_id}")
    assert response.status_code == 200
    report_data = response.json()
    assert report_data["session_id"] == session_id
    assert report_data["compliance"]["status"] == "approved"

    # 5. Fetch audit compliance logs
    response = client.get(f"/api/v1/audit/{session_id}")
    assert response.status_code == 200
    audit_data = response.json()
    assert audit_data["session_id"] == session_id
    assert audit_data["execution_summary"]["status"] == "COMPLETED"
    assert len(audit_data["audit_logs"]) > 0

def test_analyze_low_confidence_flow():
    session_id = "api-test-low-confidence-session"
    payload = {
        "raw_input_text": "อยากรวย",
        "session_id": session_id
    }
    
    # Ambiguous input should route straight to human_review node
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    if data.get("status") == "failed":
        print("TRACE ON FAILURE FOR test_analyze_low_confidence_flow:")
        for t in data.get("trace", []):
            print("  ", t)
    assert data["status"] == "awaiting_review"
    assert data["typhoon_result"]["confidence"] < 0.80
    assert any("WARNING: Confidence" in trace for trace in data["trace"])

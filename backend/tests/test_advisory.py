import pytest
from backend.app.services.tax_engine import (
    calculate_tax,
    calculate_ssf_limit,
    calculate_rmf_limit,
    calculate_tax_savings,
    calculate_remaining_deduction_capacity
)
from backend.app.services.fund_catalog import recommend_funds
from backend.app.db.database import SessionLocal, init_db
from backend.app.db.models import Fund

def test_tax_calculation_progressive():
    # Test standard income brackets
    assert calculate_tax(150000) == 0.0
    assert calculate_tax(300000) == 7500.0
    assert calculate_tax(500000) == 27500.0
    assert calculate_tax(750000) == 65000.0

def test_ssf_and_rmf_limits():
    # Capped at 30% of income, up to 200k/500k respectively
    assert calculate_ssf_limit(1000000.0) == 200000.0 # 30% of 1m is 300k, capped at 200k
    assert calculate_ssf_limit(500000.0) == 150000.0  # 30% of 500k is 150k
    
    assert calculate_rmf_limit(2000000.0) == 500000.0 # 30% of 2m is 600k, capped at 500k
    assert calculate_rmf_limit(1000000.0) == 300000.0  # 30% of 1m is 300k

def test_remaining_deduction_capacity():
    # Client A: 3.24M income, existing SSF 100k, existing RMF 0
    income = 3240000.0
    cap = calculate_remaining_deduction_capacity(
        income=income,
        existing_ssf=100000.0,
        existing_rmf=0.0
    )
    
    assert cap["max_ssf_allowed"] == 200000.0
    assert cap["max_rmf_allowed"] == 500000.0
    assert cap["max_thaiesg_allowed"] == 300000.0
    
    # Existing SSF = 100k, so allowed additional SSF = 100k
    # Joint cap is 500k. Capped existing = 100k. Capped headroom = 400k.
    # Allowed additional SSF = min(100k headroom, 400k joint headroom) = 100k.
    # Allowed additional RMF = min(500k headroom, max(400k - 100k, 0)) = 300k.
    assert cap["allowed_additional_ssf"] == 100000.0
    assert cap["allowed_additional_rmf"] == 300000.0
    assert cap["allowed_additional_thaiesg"] == 300000.0
    assert cap["total_additional_capacity"] == 700000.0

def test_tax_savings():
    # Compute savings comparing standard deductions pre-opt and post-opt
    income = 3240000.0
    
    # deductions: Personal (60k) + Expense (100k) + existing SSF (100k) + existing Insurance (50k) = 310k
    deductions_before = 310000.0
    # deductions: Personal (60k) + Expense (100k) + maximized SSF/RMF (500k) + Insurance (50k) + ThaiESG (300k) = 1.01M
    deductions_after = 1010000.0
    
    savings = calculate_tax_savings(income, deductions_before, deductions_after)
    
    tax_before = calculate_tax(income - deductions_before) # 2.93M taxable -> 644,000 tax
    tax_after = calculate_tax(income - deductions_after)   # 2.23M taxable -> 434,000 tax
    
    assert tax_before == 644000.0
    assert tax_after == 434000.0
    assert savings == 210000.0

def test_typhoon_normalization():
    from backend.app.agents.agents import run_typhoon_interpreter_crew
    
    # Example 1
    input_text_1 = "เงินเดือนประมาณแสนห้า โบนัสปีละ 4 เดือน ซื้อ RMF บ้างนิดหน่อย มีประกันชีวิตอยู่แล้ว อยากลดภาษีเพิ่ม"
    result_1 = run_typhoon_interpreter_crew(input_text_1)
    
    assert result_1.entities.monthly_income == 150000.0
    assert result_1.entities.bonus_months == 4.0
    assert result_1.entities.rmf is None  # "RMF บ้างนิดหน่อย" -> rmf = null
    assert result_1.confidence >= 0.80
    assert "Seeking tax optimization" in result_1.entities.goal or "tax optimization" in result_1.english_translation
    
    # Example 2
    input_text_2 = "รายได้ไม่แน่นอน ฟรีแลนซ์ ปีที่แล้วเสียภาษีเยอะมาก กำลังมองหา SSF"
    result_2 = run_typhoon_interpreter_crew(input_text_2)
    assert result_2.entities.employment_type == "freelance"
    assert result_2.entities.monthly_income is None
    assert result_2.entities.annual_income is None
    assert result_2.confidence >= 0.80

def test_typhoon_low_confidence_routing():
    from backend.app.graph.workflow import app_workflow
    
    # Very short, ambiguous input
    input_text = "อยากรวย"
    session_id = "test-session-low-confidence"
    config = {"configurable": {"thread_id": session_id}}
    
    state = {
        "session_id": session_id,
        "raw_input_text": input_text,
        "client_data": None,
        "suitability": None,
        "tax_result": None,
        "recommendation": None,
        "explanation": None,
        "compliance": None,
        "trace": [],
        "status": "client_intake"
    }
    
    # Invoke workflow. Because input is "อยากรวย", confidence is 0.50 (below 0.80 threshold)
    # It should route directly from typhoon_interpreter to human_review, and pause.
    final_state = app_workflow.invoke(state, config=config)
    
    assert final_state["typhoon_result"].confidence < 0.80
    assert final_state["status"] == "awaiting_review"
    assert any("WARNING: Confidence" in trace for trace in final_state["trace"])


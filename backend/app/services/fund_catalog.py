from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from backend.app.db.models import Fund

# Pre-populated active Thai mutual funds
INITIAL_FUNDS = [
    {
        "name": "SCB Thai Mixed Sustainable Equity Fund",
        "asset_class": "Equity",
        "risk_level": 5,
        "tax_type": "ThaiESG",
        "expense_ratio": 0.95,
        "aum": 1200000000.0,
        "objective": "Invests in high-quality Thai equities rated highly for ESG practices with a balanced risk-return profile."
    },
    {
        "name": "Land and Houses Green Development Fund",
        "asset_class": "Equity",
        "risk_level": 6,
        "tax_type": "ThaiESG",
        "expense_ratio": 1.25,
        "aum": 850000000.0,
        "objective": "Focuses on Thai companies involved in clean energy, waste reduction, and carbon neutrality."
    },
    {
        "name": "Kasikorn Thai ESG Treasury Bond Fund",
        "asset_class": "Fixed Income",
        "risk_level": 2,
        "tax_type": "ThaiESG",
        "expense_ratio": 0.45,
        "aum": 2100000000.0,
        "objective": "Ultra low-risk Thai government treasury bonds certified under green/sustainability finance framework."
    },
    {
        "name": "Kasikorn Selected Equity Super Savings Fund",
        "asset_class": "Equity",
        "risk_level": 6,
        "tax_type": "SSF",
        "expense_ratio": 1.10,
        "aum": 3400000000.0,
        "objective": "High-growth equity fund focusing on top 20 structural growth companies in Thailand."
    },
    {
        "name": "SCB Global Equity Super Savings Fund",
        "asset_class": "Equity",
        "risk_level": 7,
        "tax_type": "SSF",
        "expense_ratio": 1.45,
        "aum": 4200000000.0,
        "objective": "Feeder fund into international global equities aiming for long-term capital appreciation."
    },
    {
        "name": "Thanachart Low Risk Fixed Income SSF",
        "asset_class": "Fixed Income",
        "risk_level": 3,
        "tax_type": "SSF",
        "expense_ratio": 0.55,
        "aum": 1800000000.0,
        "objective": "Invests primarily in highly rated corporate bonds and bank deposits. Ideal for capital preservation."
    },
    {
        "name": "Bualuang Active Equity Retirement Mutual Fund",
        "asset_class": "Equity",
        "risk_level": 6,
        "tax_type": "RMF",
        "expense_ratio": 1.20,
        "aum": 5500000000.0,
        "objective": "Actively managed equity retirement fund focusing on dividend-paying blue-chip Thai stocks."
    },
    {
        "name": "Asset Plus World Equity Retirement Mutual Fund",
        "asset_class": "Equity",
        "risk_level": 7,
        "tax_type": "RMF",
        "expense_ratio": 1.55,
        "aum": 2800000000.0,
        "objective": "Invests in global technology and consumer franchises for aggressive retirement growth."
    },
    {
        "name": "SCB Treasury Money Market RMF",
        "asset_class": "Fixed Income",
        "risk_level": 1,
        "tax_type": "RMF",
        "expense_ratio": 0.25,
        "aum": 9500000000.0,
        "objective": "Invests in short-term government bonds. Suited for clients seeking absolute capital safety."
    }
]

def seed_funds(db: Session):
    """
    Seeds initial fund list if the funds table is empty.
    """
    if db.query(Fund).count() == 0:
        for f_data in INITIAL_FUNDS:
            fund = Fund(**f_data)
            db.add(fund)
        db.commit()

def search_funds(
    db: Session,
    asset_class: Optional[str] = None,
    risk_level: Optional[int] = None,
    tax_type: Optional[str] = None
) -> List[Fund]:
    """
    Retrieves funds from the database based on filters.
    """
    query = db.query(Fund)
    if asset_class:
        query = query.filter(Fund.asset_class == asset_class)
    if risk_level:
        query = query.filter(Fund.risk_level == risk_level)
    if tax_type:
        query = query.filter(Fund.tax_type == tax_type)
    return query.all()

def recommend_funds(
    db: Session,
    risk_profile: str,
    goal: str,
    tax_type: str,
    budget: float
) -> List[Dict[str, Any]]:
    """
    Selects suitable funds matching risk profile, goal, and tax type,
    and returns allocation structures.
    """
    # 1. Define allowed risk ratings
    risk_map = {
        "Conservative": [1, 2, 3],
        "Moderate": [3, 4, 5, 6],
        "Aggressive": [5, 6, 7]
    }
    allowed_risks = risk_map.get(risk_profile, [3, 4, 5, 6])
    
    # Query database candidates
    candidates = db.query(Fund).filter(
        Fund.tax_type == tax_type,
        Fund.risk_level.in_(allowed_risks)
    ).all()
    
    # Fallback if no matching risk is found: query all of that tax type
    if not candidates:
        candidates = db.query(Fund).filter(Fund.tax_type == tax_type).all()
        
    if not candidates:
        return []
        
    # Sort candidates (for Growth prioritize higher risk, for Conservative prioritize lower risk)
    if goal.lower() == "growth":
        candidates = sorted(candidates, key=lambda x: x.risk_level, reverse=True)
    else:
        candidates = sorted(candidates, key=lambda x: x.risk_level)
        
    # Pick the top candidate
    selected_fund = candidates[0]
    
    return [{
        "fund_code": selected_fund.name.split(" ")[0] if " " in selected_fund.name else selected_fund.name, # Use first word as ticker
        "fund_name": selected_fund.name,
        "fund_type": selected_fund.tax_type,
        "amount_thb": budget,
        "allocation_percentage": 100.0,
        "risk_level": selected_fund.risk_level,
        "expense_ratio": selected_fund.expense_ratio,
        "reason": f"Recommended because it matches your risk profile ({risk_profile}) and provides {tax_type} tax shelter."
    }]

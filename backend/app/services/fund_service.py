from typing import List, Dict, Any

MOCK_FUNDS = [
    # ThaiESG Funds
    {
        "fund_code": "SCB-ESG-ThaiESG",
        "fund_name": "SCB Thai Mixed Sustainable Equity Fund",
        "fund_type": "ThaiESG",
        "risk_level": 5,
        "esg_rating": "AAA",
        "description": "Invests in high-quality Thai equities rated highly for ESG practices with a balanced risk-return profile."
    },
    {
        "fund_code": "LH-GREEN-ThaiESG",
        "fund_name": "Land and Houses Green Development Fund",
        "fund_type": "ThaiESG",
        "risk_level": 6,
        "esg_rating": "AA",
        "description": "Focuses on Thai companies involved in clean energy, waste reduction, and carbon neutrality."
    },
    {
        "fund_code": "K-TREASURY-ThaiESG",
        "fund_name": "Kasikorn Thai ESG Treasury Bond Fund",
        "fund_type": "ThaiESG",
        "risk_level": 2,
        "esg_rating": "AAA",
        "description": "Ultra low-risk Thai government treasury bonds certified under green/sustainability finance framework."
    },
    
    # SSF Funds
    {
        "fund_code": "K-SELECT-SSF",
        "fund_name": "Kasikorn Selected Equity Super Savings Fund",
        "fund_type": "SSF",
        "risk_level": 6,
        "esg_rating": "A",
        "description": "High-growth equity fund focusing on top 20 structural growth companies in Thailand."
    },
    {
        "fund_code": "SCB-GLOB-SSF",
        "fund_name": "SCB Global Equity Super Savings Fund",
        "fund_type": "SSF",
        "risk_level": 7,
        "esg_rating": "AA",
        "description": "Feeder fund into international global equities aiming for long-term capital appreciation."
    },
    {
        "fund_code": "T-LOWRISK-SSF",
        "fund_name": "Thanachart Low Risk Fixed Income SSF",
        "fund_type": "SSF",
        "risk_level": 3,
        "esg_rating": "N/A",
        "description": "Invests primarily in highly rated corporate bonds and bank deposits. Ideal for capital preservation."
    },
    
    # RMF Funds
    {
        "fund_code": "B-ACTIVE-RMF",
        "fund_name": "Bualuang Active Equity Retirement Mutual Fund",
        "fund_type": "RMF",
        "risk_level": 6,
        "esg_rating": "A",
        "description": "Actively managed equity retirement fund focusing on dividend-paying blue-chip Thai stocks."
    },
    {
        "fund_code": "ASP-WORLD-RMF",
        "fund_name": "Asset Plus World Equity Retirement Mutual Fund",
        "fund_type": "RMF",
        "risk_level": 7,
        "esg_rating": "AA",
        "description": "Invests in global technology and consumer franchises for aggressive retirement growth."
    },
    {
        "fund_code": "SCB-TREASURY-RMF",
        "fund_name": "SCB Treasury Money Market RMF",
        "fund_type": "RMF",
        "risk_level": 1,
        "esg_rating": "N/A",
        "description": "Invests in short-term government bonds. Lowest possible risk, suited for clients nearing retirement age."
    }
]

def get_fund_catalog() -> List[Dict[str, Any]]:
    return MOCK_FUNDS

def recommend_funds_for_client(
    risk_profile: str,
    age: int,
    investments_needed: Dict[str, float]
) -> List[Dict[str, Any]]:
    """
    Selects funds based on risk tolerance, age, and required optimization amounts.
    For each investment type needed (e.g. ssf_additional, rmf_additional, thaiesg_additional),
    allocates to appropriate funds.
    """
    recommended = []
    risk_level_map = {
        "Conservative": [1, 2, 3],
        "Moderate": [3, 4, 5, 6],
        "Aggressive": [5, 6, 7, 8]
    }
    
    allowed_risks = risk_level_map.get(risk_profile, [3, 4, 5, 6])
    
    for inv_type, amount in investments_needed.items():
        if amount <= 0:
            continue
            
        fund_type = None
        if inv_type == "ssf_additional":
            fund_type = "SSF"
        elif inv_type == "rmf_additional":
            fund_type = "RMF"
        elif inv_type == "thaiesg_additional":
            fund_type = "ThaiESG"
            
        if not fund_type:
            continue
            
        # Filter candidate funds matching type
        candidates = [f for f in MOCK_FUNDS if f["fund_type"] == fund_type]
        
        # Filter candidates matching risk if possible, fallback to any of the type
        matching_risk_candidates = [c for c in candidates if c["risk_level"] in allowed_risks]
        
        if not matching_risk_candidates:
            # Fallback: Sort by proximity of risk level
            matching_risk_candidates = sorted(candidates, key=lambda c: min(abs(c["risk_level"] - r) for r in allowed_risks))
            
        # Select the best matching fund (or divide if amount is large, here we just select the top candidate)
        selected_fund = matching_risk_candidates[0]
        
        # Determine specific reason
        reason = f"Selected because it is a {fund_type} fund with risk level {selected_fund['risk_level']} which matches your '{risk_profile}' profile."
        if selected_fund["esg_rating"] != "N/A":
            reason += f" Backed by a strong ESG rating of {selected_fund['esg_rating']}."
            
        recommended.append({
            "fund_code": selected_fund["fund_code"],
            "fund_name": selected_fund["fund_name"],
            "fund_type": selected_fund["fund_type"],
            "amount_thb": amount,
            "allocation_percentage": 100.0, # Will normalize percentages at portfolio level later
            "risk_level": selected_fund["risk_level"],
            "esg_rating": selected_fund["esg_rating"],
            "reason": reason
        })
        
    # Re-normalize allocation percentages
    total_amt = sum(r["amount_thb"] for r in recommended)
    if total_amt > 0:
        for r in recommended:
            r["allocation_percentage"] = round((r["amount_thb"] / total_amt) * 100.0, 2)
            
    return recommended

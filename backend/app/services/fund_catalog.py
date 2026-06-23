from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import base64
import re
import logging
from backend.app.db.models import Fund
from backend.app.services.sec_client import SECClient
from backend.app.config import settings

logger = logging.getLogger(__name__)

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

def decode_base64_safe(s: str) -> str:
    s_orig = s
    try:
        # Base64 strings must be padded to a multiple of 4
        s = s.strip()
        missing_padding = len(s) % 4
        if missing_padding:
            s += '=' * (4 - missing_padding)
        return base64.b64decode(s).decode("utf-8")
    except Exception:
        return s_orig

async def sync_funds_from_sec(db: Session) -> Dict[str, Any]:
    """
    Queries the SEC API, filters for popular active SSF, RMF, and ThaiESG funds,
    fetches factsheet details, and caches them in the local database.
    """
    logger.info("Starting SEC fund catalog synchronization...")
    client = SECClient()
    
    # 1. Fetch AMCs
    try:
        amcs = await client.get_amcs()
    except Exception as e:
        logger.error(f"Failed to fetch AMCs from SEC API: {str(e)}")
        return {"status": "failed", "error": f"Failed to fetch AMCs: {str(e)}"}
        
    # We focus on major Thai AMCs to optimize request limits and performance
    major_amc_keywords = ["KASIKORN", "SCB", "BUALUANG", "BBL", "THANACHART", "LH", "KRUNGSRI", "TMB", "UOB", "ONE", "ASSET PLUS"]
    selected_amcs = []
    for amc in amcs:
        name_en = (amc.get("name_en") or "").upper()
        name_th = (amc.get("name_th") or "").upper()
        if any(kw in name_en or kw in name_th for kw in major_amc_keywords):
            selected_amcs.append(amc)
            
    if not selected_amcs:
        # Fallback to first few if none match keywords
        selected_amcs = amcs[:5]
        
    logger.info(f"Selected {len(selected_amcs)} major AMCs for synchronization.")
    
    synced_count = 0
    errors_count = 0
    
    # Limit total funds processed to stay within a reasonable duration (e.g. max 50 funds)
    max_funds_limit = 50
    
    for amc in selected_amcs:
        if synced_count >= max_funds_limit:
            break
            
        amc_id = amc.get("unique_id")
        amc_name = amc.get("name_en") or amc.get("name_th")
        logger.info(f"Fetching funds for AMC: {amc_name} (ID: {amc_id})")
        
        try:
            funds = await client.get_funds_by_amc(amc_id)
        except Exception as e:
            logger.warning(f"Failed to fetch funds for AMC {amc_name}: {str(e)}")
            errors_count += 1
            continue
            
        # Filter for tax-saving funds (SSF, RMF, ESG)
        tax_funds = []
        for f in funds:
            abbr = (f.get("proj_abbr_name") or "").upper()
            name_en = (f.get("proj_name_en") or "").upper()
            if any(kw in abbr or kw in name_en for kw in ["SSF", "RMF", "ESG", "THAIESG"]):
                tax_funds.append(f)
                
        logger.info(f"Found {len(tax_funds)} potential tax-saving funds under {amc_name}.")
        
        for f in tax_funds:
            if synced_count >= max_funds_limit:
                break
                
            proj_id = f.get("proj_id")
            abbr = (f.get("proj_abbr_name") or "").strip()
            proj_name = (f.get("proj_name_en") or f.get("proj_name_th") or "").strip()
            name = f"{abbr} ({proj_name})" if abbr else proj_name
            
            # Determine tax type
            abbr_upper = abbr.upper()
            name_upper = name.upper()
            if "SSF" in abbr_upper or "SSF" in name_upper:
                tax_type = "SSF"
            elif "RMF" in abbr_upper or "RMF" in name_upper:
                tax_type = "RMF"
            elif "ESG" in abbr_upper or "ESG" in name_upper or "THAIESG" in abbr_upper or "THAIESG" in name_upper:
                tax_type = "ThaiESG"
            else:
                continue # Skip general funds
                
            logger.info(f"Syncing fund: {abbr} (ID: {proj_id}, Type: {tax_type})")
            
            try:
                # Fetch detailed suitability, fee, and policy info
                suitability = await client.get_fund_suitability(proj_id)
                fees = await client.get_fund_fee(proj_id)
                policy = await client.get_fund_policy(proj_id)
                
                # 1. Parse Risk Level
                risk_spectrum = suitability.get("risk_spectrum", "")
                match = re.search(r'\d+', risk_spectrum)
                risk_level = int(match.group()) if match else 5
                
                # 2. Parse Expense Ratio
                expense_ratio = 1.0  # default fallback
                if isinstance(fees, list):
                    # Try to find total expense ratio
                    total_fee_item = None
                    for fee in fees:
                        desc = fee.get("fee_type_desc") or ""
                        if "รวมทั้งหมด" in desc or "รวมค่าใช้จ่าย" in desc or "Total Expense" in desc or "Total Fee" in desc:
                            total_fee_item = fee
                            break
                    if not total_fee_item:
                        # Fallback to management fee
                        for fee in fees:
                            desc = fee.get("fee_type_desc") or ""
                            if "การจัดการ" in desc or "Management" in desc:
                                total_fee_item = fee
                                break
                    if total_fee_item:
                        val = total_fee_item.get("actual_value")
                        if val is None or float(val) == 0.0:
                            val = total_fee_item.get("rate")
                        if val is not None:
                            expense_ratio = float(val)
                            
                # 3. Parse Asset Class
                policy_desc = policy.get("policy_desc") or ""
                policy_text_decoded = decode_base64_safe(policy.get("investment_policy_desc") or "").upper()
                
                combined_policy = (policy_desc + " " + policy_text_decoded + " " + name).upper()
                if any(kw in combined_policy for kw in ["EQUITY", "STOCK", "หุ้น", "ตราสารทุน"]):
                    asset_class = "Equity"
                elif any(kw in combined_policy for kw in ["BOND", "FIXED", "TREASURY", "DEBENTURE", "ตราสารหนี้", "เงินฝาก"]):
                    asset_class = "Fixed Income"
                elif any(kw in combined_policy for kw in ["MIXED", "BALANCED", "ผสม", "ตราสารผสม"]):
                    asset_class = "Mixed"
                else:
                    asset_class = "Equity" # Default fallback
                    
                # 4. Parse Objective
                objective = decode_base64_safe(policy.get("investment_policy_desc") or "")
                if not objective:
                    objective = f"Investment objective for {name} ({abbr}). Class: {asset_class}."
                if len(objective) > 500:
                    objective = objective[:497] + "..."
                    
                # Save or update in database
                existing_fund = db.query(Fund).filter(Fund.proj_id == proj_id).first()
                if existing_fund:
                    existing_fund.name = name
                    existing_fund.asset_class = asset_class
                    existing_fund.risk_level = risk_level
                    existing_fund.tax_type = tax_type
                    existing_fund.expense_ratio = expense_ratio
                    existing_fund.objective = objective
                else:
                    new_fund = Fund(
                        proj_id=proj_id,
                        name=name,
                        asset_class=asset_class,
                        risk_level=risk_level,
                        tax_type=tax_type,
                        expense_ratio=expense_ratio,
                        aum=1200000000.0, # Default value
                        objective=objective
                    )
                    db.add(new_fund)
                    
                synced_count += 1
                logger.info(f"Successfully synced {abbr}: Risk={risk_level}, Fee={expense_ratio}%, Class={asset_class}")
                
            except Exception as ex:
                logger.warning(f"Error processing fund {abbr} ({proj_id}): {str(ex)}")
                errors_count += 1
                
    db.commit()
    logger.info(f"Catalog sync completed. Synced funds: {synced_count}, Errors: {errors_count}")
    return {"status": "success", "synced_count": synced_count, "errors_count": errors_count}

def seed_funds(db: Session):
    """
    Seeds initial fund list if the funds table is empty (fallback mock data).
    """
    if db.query(Fund).count() == 0:
        for idx, f_data in enumerate(INITIAL_FUNDS):
            # Create a mock proj_id for each mock fund (e.g. MOCK_0, MOCK_1)
            mock_proj_id = f"MOCK_{idx}"
            fund = Fund(proj_id=mock_proj_id, **f_data)
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

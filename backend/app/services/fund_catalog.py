from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import asyncio
import base64
import re
import logging
from backend.app.db.models import Fund
from backend.app.services.sec_client import SECClient
from backend.app.config import settings

logger = logging.getLogger(__name__)


class FundCatalogUnavailable(RuntimeError):
    """Raised when the live SEC fund catalog cannot be loaded after retries.
    The API layer maps this to HTTP 503 'try again later'. No mock funds are
    ever served in its place."""


def _real_fund_count(db: Session) -> int:
    """Funds that came from the live SEC sync (mock seeds use MOCK_* proj_ids
    and must never count as a usable catalog)."""
    return db.query(Fund).filter(~Fund.proj_id.like("MOCK_%")).count()


async def ensure_funds_available(db: Session, retries: int = 2) -> int:
    """Guarantee the catalog holds live SEC-sourced funds before a recommendation
    runs. Pulls lazily on first need; retries on transient SEC failures, then
    raises FundCatalogUnavailable. Never falls back to mock data."""
    have = _real_fund_count(db)
    if have > 0:
        return have

    last_err: Optional[str] = None
    for attempt in range(retries + 1):
        try:
            result = await sync_funds_from_sec(db)
            if result.get("status") == "success" and _real_fund_count(db) > 0:
                return _real_fund_count(db)
            last_err = result.get("error") or "SEC sync returned no funds"
        except Exception as e:  # network blip, timeout, etc.
            last_err = str(e)
        logger.warning(f"SEC fund sync attempt {attempt + 1} failed: {last_err}")
        if attempt < retries:
            await asyncio.sleep(1.5 * (attempt + 1))

    raise FundCatalogUnavailable(
        "ไม่สามารถโหลดข้อมูลกองทุนจาก SEC ได้ กรุณาลองใหม่อีกครั้ง / "
        "Could not load fund data from the SEC. Please try again later."
    )

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

# ---- SEC v2 classification / enrichment helpers -------------------------------

def _classify_tax_type(tax_incentive, abbr, name):
    """Hybrid classifier. RMF is NOT flagged by fund_class_tax_incentive_type, so
    it is detected by the 'RMF' naming convention; SSF and ThaiESG come from the
    authoritative tax-incentive field (their names rarely contain SSF/ESG, and a
    plain 'ESG' in a name is not necessarily the tax-deductible Thai ESG fund)."""
    tf = (tax_incentive or "").upper()
    label = ((abbr or "") + " " + (name or "")).upper()
    if "RMF" in label or "RETIREMENT MUTUAL" in tf:
        return "RMF"
    if "SUPER SAVINGS" in tf or "SAVINGS FUND" in tf or " SSF" in (" " + tf):
        return "SSF"
    if "THAILAND ESG" in tf or "THAI ESG" in tf:
        return "ThaiESG"
    return None


def _asset_class_from_policy(policy_desc):
    p = policy_desc or ""
    if "ตราสารทุน" in p:
        return "Equity"
    if "ตราสารหนี้" in p:
        return "Fixed Income"
    if "ผสม" in p:
        return "Mixed"
    return "Alternative"


async def _latest_risk_level(client, proj_id):
    items = await client.get_risk_spectrum(proj_id)
    if not items:
        return 5
    latest = sorted(items, key=lambda x: (x.get("end_date") or ""))[-1]
    m = re.search(r"\d+", latest.get("risk_spectrum") or "")
    return int(m.group()) if m else 5


async def _representative_fee(client, proj_id):
    """Pick a meaningful expense figure: prefer total expense / management fee."""
    items = await client.get_fees(proj_id)
    for kw in ["รวมค่าใช้จ่าย", "รวมทั้งหมด", "total expense", "การจัดการ", "management"]:
        for it in items:
            if kw.lower() in (it.get("fee_type_desc") or "").lower():
                v = it.get("actual_value") or it.get("rate")
                if v:
                    try:
                        return round(float(v), 4)
                    except (TypeError, ValueError):
                        pass
    return None


async def sync_funds_from_sec(db: Session) -> Dict[str, Any]:
    """Pull SSF / RMF / ThaiESG mutual funds from the SEC Thailand Open API **v2**
    and cache them in the local Fund table. Pages /v2/fund/general-info/profiles,
    classifies by tax type, derives asset class from policy_desc, and enriches each
    fund with risk level (/factsheet/risk-spectrum) and expense ratio
    (/factsheet/fees). No mock fallback — failures bubble up to a 503."""
    logger.info("Starting SEC v2 fund catalog synchronization...")
    client = SECClient()

    # Caps keep the first (lazy) load bounded on free-tier hosting.
    MAX_PROFILE_PAGES = 25
    PER_TYPE_CAP = 6

    selected = {"SSF": [], "RMF": [], "ThaiESG": []}
    seen_proj = set()
    cursor = ""
    try:
        for _ in range(MAX_PROFILE_PAGES):
            items, cursor = await client.fetch_profiles_page(cursor)
            for it in items:
                tax_type = _classify_tax_type(
                    it.get("fund_class_tax_incentive_type"),
                    it.get("proj_abbr_name"),
                    it.get("proj_name_en") or it.get("proj_name_th"),
                )
                proj_id = it.get("proj_id")
                if not tax_type or not proj_id or proj_id in seen_proj:
                    continue
                if len(selected[tax_type]) >= PER_TYPE_CAP:
                    continue
                seen_proj.add(proj_id)
                objective = decode_base64_safe(it.get("investment_policy_desc") or "")
                objective = (objective or it.get("policy_desc") or "").strip()
                selected[tax_type].append({
                    "proj_id": proj_id,
                    "name": (it.get("proj_name_en") or it.get("proj_name_th") or it.get("proj_abbr_name") or proj_id).strip(),
                    "abbr": (it.get("proj_abbr_name") or "").strip(),
                    "tax_type": tax_type,
                    "asset_class": _asset_class_from_policy(it.get("policy_desc")),
                    "objective": objective[:497],
                })
            if not cursor or all(len(v) >= PER_TYPE_CAP for v in selected.values()):
                break
    except Exception as e:
        logger.error(f"Failed to page SEC fund profiles: {str(e)}")
        return {"status": "failed", "error": f"Failed to fetch fund profiles: {str(e)}"}

    candidates = [f for funds in selected.values() for f in funds]
    if not candidates:
        return {"status": "failed", "error": "No SSF/RMF/ThaiESG funds returned by the SEC API."}

    synced_count = 0
    errors_count = 0
    for f in candidates:
        try:
            risk_level = await _latest_risk_level(client, f["proj_id"])
            expense_ratio = await _representative_fee(client, f["proj_id"])
            objective = f["objective"] or f"{f['tax_type']} fund. Asset class: {f['asset_class']}."

            fields = dict(
                name=f["name"],
                asset_class=f["asset_class"],
                risk_level=risk_level,
                tax_type=f["tax_type"],
                expense_ratio=expense_ratio if expense_ratio is not None else 1.0,
                objective=objective,
            )
            existing = db.query(Fund).filter(Fund.proj_id == f["proj_id"]).first()
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                db.add(Fund(proj_id=f["proj_id"], aum=0.0, **fields))
            synced_count += 1
        except Exception as ex:
            logger.warning(f"Error enriching fund {f.get('abbr')} ({f.get('proj_id')}): {str(ex)}")
            errors_count += 1

    db.commit()
    by_type = {k: len(v) for k, v in selected.items()}
    logger.info(f"SEC v2 catalog sync done. Synced: {synced_count}, Errors: {errors_count}, by type: {by_type}")
    if synced_count == 0:
        return {"status": "failed", "error": "Fund enrichment failed for all candidates."}
    return {"status": "success", "synced_count": synced_count, "errors_count": errors_count, "by_type": by_type}


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
    # Only ever recommend real SEC-sourced funds — exclude any stale MOCK_* rows.
    candidates = db.query(Fund).filter(
        Fund.tax_type == tax_type,
        Fund.risk_level.in_(allowed_risks),
        ~Fund.proj_id.like("MOCK_%"),
    ).all()

    # Fallback if no matching risk is found: query all of that tax type
    if not candidates:
        candidates = db.query(Fund).filter(
            Fund.tax_type == tax_type,
            ~Fund.proj_id.like("MOCK_%"),
        ).all()
        
    if not candidates:
        return []
        
    # Sort candidates by best fit: goal sets the risk preference, then prefer the
    # cheaper fund (lower expense ratio) to break ties.
    if goal and goal.lower() == "growth":
        candidates = sorted(candidates, key=lambda x: (-x.risk_level, x.expense_ratio))
    else:
        candidates = sorted(candidates, key=lambda x: (x.risk_level, x.expense_ratio))

    # Recommend the top 3 best-fit funds for this tax type (or fewer if the SEC
    # catalog has fewer). The per-type budget is split so the best-fit fund gets
    # the largest share. allocation_percentage here is within-type; the
    # recommendation node renormalizes it portfolio-wide.
    selected_funds = candidates[:3]
    weights = [0.5, 0.3, 0.2][: len(selected_funds)]
    weight_sum = sum(weights)
    weights = [w / weight_sum for w in weights]

    results: List[Dict[str, Any]] = []
    for rank, (fund, weight) in enumerate(zip(selected_funds, weights), start=1):
        results.append({
            "fund_code": fund.name.split(" ")[0] if " " in fund.name else fund.name,  # first word as ticker
            "fund_name": fund.name,
            "fund_type": fund.tax_type,
            "amount_thb": round(budget * weight, 2),
            "allocation_percentage": round(weight * 100.0, 2),
            "risk_level": fund.risk_level,
            "expense_ratio": fund.expense_ratio,
            "reason": (
                f"Top {rank} {tax_type} pick for your {risk_profile or 'selected'} risk profile "
                f"(fund risk {fund.risk_level}, expense ratio {fund.expense_ratio}%), "
                f"providing {tax_type} tax-deductible benefit."
            ),
        })
    return results

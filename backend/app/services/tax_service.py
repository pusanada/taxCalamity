from typing import Dict, Any

def compute_thai_income_tax(taxable_income: float) -> float:
    """
    Calculates personal income tax in Thailand based on progressive brackets:
    0 - 150k: 0% (exempt)
    150k - 300k: 5%
    300k - 500k: 10%
    500k - 750k: 15%
    750k - 1m: 20%
    1m - 2m: 25%
    2m - 5m: 30%
    5m+: 35%
    """
    brackets = [
        (150000, 0.00),
        (300000, 0.05),
        (500000, 0.10),
        (750000, 0.15),
        (1000000, 0.20),
        (2000000, 0.25),
        (5000000, 0.30),
        (float('inf'), 0.35)
    ]
    
    tax = 0.0
    previous_limit = 0.0
    remaining = taxable_income
    
    for limit, rate in brackets:
        bracket_width = limit - previous_limit
        if remaining > bracket_width:
            tax += bracket_width * rate
            remaining -= bracket_width
            previous_limit = limit
        else:
            tax += remaining * rate
            break
            
    return tax

def calculate_tax_optimization(
    age: int,
    income_monthly: float,
    bonus_months: float,
    existing_rmf: float = 0,
    existing_ssf: float = 0,
    existing_life_insurance: float = 0
) -> Dict[str, Any]:
    """
    Main calculator logic that computes pre-optimized tax and fully optimized tax.
    Optimization tries to maximize ThaiESG, SSF, and RMF up to their respective limits.
    """
    # 1. Total Assessable Income (Salary + Bonus)
    annual_salary = income_monthly * 12
    annual_bonus = income_monthly * bonus_months
    total_income = annual_salary + annual_bonus
    
    # 2. Standard Deductions
    personal_deduction = 60000.0
    expense_deduction = min(total_income * 0.5, 100000.0) # 50% max 100,000 THB
    
    # 3. Standard Deductions limits
    max_ssf_allowed = min(total_income * 0.30, 200000.0)
    max_rmf_allowed = min(total_income * 0.30, 500000.0)
    max_thaiesg_allowed = min(total_income * 0.30, 300000.0)
    max_life_insurance_allowed = min(existing_life_insurance, 100000.0)
    
    # Total retirement cap (SSF + RMF <= 500k)
    # Note: ThaiESG is outside of this 500k cap.
    
    # --- BEFORE OPTIMIZATION ---
    # Apply existing investments, making sure they comply with individual and joint caps
    current_ssf = min(existing_ssf, max_ssf_allowed)
    current_rmf = min(existing_rmf, max_rmf_allowed)
    if (current_ssf + current_rmf) > 500000.0:
        # Scale down to meet joint cap
        ratio = 500000.0 / (current_ssf + current_rmf)
        current_ssf *= ratio
        current_rmf *= ratio
        
    current_retirement_deductions = current_ssf + current_rmf
    total_deductions_before = (
        personal_deduction 
        + expense_deduction 
        + current_retirement_deductions 
        + max_life_insurance_allowed
    )
    
    taxable_before = max(total_income - total_deductions_before, 0.0)
    tax_before = compute_thai_income_tax(taxable_before)
    
    # --- AFTER OPTIMIZATION ---
    # Maximize SSF, RMF, and ThaiESG
    opt_ssf = max_ssf_allowed
    opt_rmf = max_rmf_allowed
    
    # Apply 500k retirement joint cap
    if (opt_ssf + opt_rmf) > 500000.0:
        # Prioritize SSF (or RMF depending on age, here we split or fill up to 500k total)
        # Let's say we maximize SSF first (up to 200k), then RMF up to remaining (300k)
        opt_ssf = min(max_ssf_allowed, 200000.0)
        opt_rmf = min(max_rmf_allowed, 500000.0 - opt_ssf)
        
    opt_retirement_deductions = opt_ssf + opt_rmf
    
    # Maximize ThaiESG (outside 500k cap)
    opt_thaiesg = max_thaiesg_allowed
    
    total_deductions_after = (
        personal_deduction 
        + expense_deduction 
        + opt_retirement_deductions 
        + opt_thaiesg 
        + max_life_insurance_allowed
    )
    
    taxable_after = max(total_income - total_deductions_after, 0.0)
    tax_after = compute_thai_income_tax(taxable_after)
    
    # --- REQUIRED PURCHASES FOR OPTIMIZATION ---
    new_ssf_needed = max(opt_ssf - existing_ssf, 0.0)
    new_rmf_needed = max(opt_rmf - existing_rmf, 0.0)
    new_thaiesg_needed = opt_thaiesg
    
    saving = max(tax_before - tax_after, 0.0)
    
    return {
        "assessable_income": total_income,
        "tax_before": tax_before,
        "tax_after": tax_after,
        "saving": saving,
        "deductions_before": total_deductions_before,
        "deductions_after": total_deductions_after,
        "taxable_before": taxable_before,
        "taxable_after": taxable_after,
        "optimization_purchases": {
            "ssf_additional": new_ssf_needed,
            "rmf_additional": new_rmf_needed,
            "thaiesg_additional": new_thaiesg_needed,
            "total_additional_investment": new_ssf_needed + new_rmf_needed + new_thaiesg_needed
        },
        "limits": {
            "max_ssf": max_ssf_allowed,
            "max_rmf": max_rmf_allowed,
            "max_thaiesg": max_thaiesg_allowed,
            "retirement_cap_used": opt_retirement_deductions
        }
    }

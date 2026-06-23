from typing import Dict, Any

def calculate_rmf_limit(income: float) -> float:
    """
    RMF deduction limit: 30% of assessable income, capped at 500,000 THB.
    """
    return min(income * 0.30, 500000.0)

def calculate_ssf_limit(income: float) -> float:
    """
    SSF deduction limit: 30% of assessable income, capped at 200,000 THB.
    """
    return min(income * 0.30, 200000.0)

def calculate_tax(taxable_income: float) -> float:
    """
    Calculates Thai Personal Income Tax based on progressive brackets:
    0 - 150k: 0%
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

def calculate_tax_savings(income: float, deductions_before: float, deductions_after: float) -> float:
    """
    Calculates tax savings comparing pre-deductions and post-deductions tax liabilities.
    """
    taxable_before = max(income - deductions_before, 0.0)
    taxable_after = max(income - deductions_after, 0.0)
    
    tax_before = calculate_tax(taxable_before)
    tax_after = calculate_tax(taxable_after)
    
    return max(tax_before - tax_after, 0.0)

def calculate_remaining_deduction_capacity(
    income: float,
    existing_ssf: float,
    existing_rmf: float
) -> Dict[str, float]:
    """
    Calculates remaining deduction capacities for SSF, RMF, and ThaiESG.
    Incorporates the joint retirement fund cap of 500,000 THB (SSF + RMF <= 500k).
    Note: ThaiESG is treated outside the 500k retirement cap (deductible up to 300k).
    """
    max_ssf = calculate_ssf_limit(income)
    max_rmf = calculate_rmf_limit(income)
    max_thaiesg = min(income * 0.30, 300000.0) # ThaiESG 30% of income up to 300k
    
    # Calculate capped existing investments
    curr_ssf = min(existing_ssf, max_ssf)
    curr_rmf = min(existing_rmf, max_rmf)
    
    # Apply joint cap of 500k
    joint_retirement_cap = 500000.0
    if (curr_ssf + curr_rmf) > joint_retirement_cap:
        ratio = joint_retirement_cap / (curr_ssf + curr_rmf)
        curr_ssf *= ratio
        curr_rmf *= ratio
        
    current_retirement_total = curr_ssf + curr_rmf
    
    # Available headroom for retirement under the 500k joint cap
    remaining_retirement_headroom = max(joint_retirement_cap - current_retirement_total, 0.0)
    
    # Headroom under individual caps
    ssf_individual_headroom = max(max_ssf - curr_ssf, 0.0)
    rmf_individual_headroom = max(max_rmf - curr_rmf, 0.0)
    
    # Final capacities
    allowed_additional_ssf = min(ssf_individual_headroom, remaining_retirement_headroom)
    # Remaining retirement headroom decreases if we maximize SSF first
    allowed_additional_rmf = min(rmf_individual_headroom, max(remaining_retirement_headroom - allowed_additional_ssf, 0.0))
    
    allowed_additional_thaiesg = max_thaiesg # ThaiESG has no existing input in this tool (treated as fresh buy)
    
    return {
        "max_ssf_allowed": max_ssf,
        "max_rmf_allowed": max_rmf,
        "max_thaiesg_allowed": max_thaiesg,
        "allowed_additional_ssf": allowed_additional_ssf,
        "allowed_additional_rmf": allowed_additional_rmf,
        "allowed_additional_thaiesg": allowed_additional_thaiesg,
        "total_additional_capacity": allowed_additional_ssf + allowed_additional_rmf + allowed_additional_thaiesg
    }

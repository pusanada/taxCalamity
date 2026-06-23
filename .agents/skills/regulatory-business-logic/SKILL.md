---
name: regulatory-business-logic
description: Map, implement, and validate financial regulatory requirements and business rules including SEC/FINRA compliance, MiFID II, Basel III/IV, AML/KYC, audit trails, and business logic constraints. Triggers on requests about compliance, regulations, business rules, audit, risk limits, reporting requirements, or policy enforcement.
---

# regulatory-business-logic

You have the `regulatory-business-logic` skill. Use it when the user needs to implement, validate, or map financial regulations and business rules into system logic.

## Key Regulatory Frameworks

### Securities & Markets
| Regulation | Jurisdiction | Key Requirements |
|-----------|-------------|-----------------|
| SEC Rule 15c3-5 | US | Market access, pre-trade risk controls |
| FINRA Rule 4370 | US | Business continuity planning |
| MiFID II | EU | Best execution, transparency, reporting |
| EMIR | EU | Derivatives reporting, clearing |
| Dodd-Frank | US | Systemic risk, OTC derivatives |

### Banking & Capital
| Regulation | Jurisdiction | Key Requirements |
|-----------|-------------|-----------------|
| Basel III/IV | Global | Capital adequacy, liquidity ratios |
| DFAST/CCAR | US | Stress testing, capital planning |
| IFRS 9 | International | Expected credit loss (ECL) |
| CECL | US | Current expected credit losses |

### AML/KYC
| Requirement | Description |
|------------|-------------|
| Customer Due Diligence (CDD) | Identity verification |
| Enhanced Due Diligence (EDD) | High-risk customer screening |
| Suspicious Activity Reports (SAR) | Anomaly detection + reporting |
| Transaction Monitoring | Rule-based and ML-based flagging |

## Business Logic Mapping

### Process: Regulatory Rule → Code

1. **Identify the rule** — cite exact regulation, section, and requirement
2. **Extract conditions** — what triggers the rule?
3. **Define the constraint** — what must hold true?
4. **Implement as code** — functions, validators, or middleware
5. **Write compliance tests** — verify edge cases
6. **Document the mapping** — link code to regulation

### Example: Position Limit Rule

**Rule**: No single position can exceed 10% of total portfolio NAV.

```python
class PositionLimitValidator:
    MAX_POSITION_PCT = 0.10  # SEC-compliant limit

    def validate(self, position_value: float, portfolio_nav: float) -> dict:
        pct = position_value / portfolio_nav
        return {
            "compliant": pct <= self.MAX_POSITION_PCT,
            "position_pct": pct,
            "limit": self.MAX_POSITION_PCT,
            "breach_amount": max(0, position_value - portfolio_nav * self.MAX_POSITION_PCT),
            "regulation": "Internal Policy / SEC Risk Controls"
        }
```

### Example: AML Transaction Monitoring

```python
AML_RULES = [
    {"rule": "large_cash", "threshold": 10000, "currency": "USD",
     "description": "FinCEN CTR requirement - cash transactions > $10,000"},
    {"rule": "structuring", "window_days": 5, "threshold": 10000,
     "description": "Multiple transactions designed to evade CTR"},
    {"rule": "high_risk_country", "countries": ["IR", "KP", "SY"],
     "description": "OFAC sanctions screening"}
]

def screen_transaction(transaction, rules):
    alerts = []
    for rule in rules:
        if triggers_rule(transaction, rule):
            alerts.append({"rule": rule["rule"], "regulation": rule["description"]})
    return alerts
```

## Audit Trail Implementation

Every compliance-related action must be logged:

```python
import datetime
import json

def audit_log(action: str, entity: str, details: dict, user: str):
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "action": action,
        "entity": entity,
        "user": user,
        "details": details,
        "immutable": True  # Flag for tamper-evident storage
    }
    # Write to append-only audit store
    with open("audit_trail.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
```

## Risk Limit Framework

```python
RISK_LIMITS = {
    "var_95_daily": 0.02,        # Max 2% daily VaR at 95% confidence
    "max_drawdown": 0.15,        # Max 15% portfolio drawdown
    "leverage_ratio": 2.0,       # Max 2x leverage
    "concentration_limit": 0.10, # Max 10% in single asset
    "sector_limit": 0.30,        # Max 30% in single sector
}

def check_risk_limits(portfolio_metrics: dict) -> list:
    breaches = []
    for limit_name, limit_value in RISK_LIMITS.items():
        actual = portfolio_metrics.get(limit_name)
        if actual and actual > limit_value:
            breaches.append({
                "limit": limit_name,
                "actual": actual,
                "allowed": limit_value,
                "severity": "HIGH" if actual > limit_value * 1.5 else "MEDIUM"
            })
    return breaches
```

## Regulatory Reporting

### MiFID II Transaction Report Fields
- LEI (Legal Entity Identifier)
- ISIN of instrument
- Execution timestamp (UTC)
- Price and quantity
- Venue of execution
- Counterparty LEI

### Automated Report Generation
Always structure reports as:
1. **Summary** — key metrics and compliance status
2. **Breaches** — any limit or rule violations
3. **Actions taken** — remediation steps
4. **Attestation** — who reviewed and approved

## For AI-Finance Context

- Every AI model output used in a trading decision must be logged
- Model risk (SR 11-7) requires documentation, validation, and ongoing monitoring
- Explainability: AI decisions affecting customers must be explainable
- Human oversight required for high-stakes automated decisions

## Verification Checklist

- [ ] Every rule is cited with exact regulatory reference
- [ ] All validations are tested with edge cases
- [ ] Audit trail captures who, what, when, why
- [ ] Breaches trigger alerts and escalation workflows
- [ ] Reports meet regulatory format requirements
- [ ] Human review gates are implemented for high-risk decisions

---
name: ux-ui-human-in-the-loop
description: Design and implement UX/UI for AI-powered financial applications with a focus on human-in-the-loop workflows, explainability dashboards, confidence displays, override mechanisms, and trust-building interfaces. Triggers on requests about UI design, dashboards, HITL, explainable AI interfaces, user feedback loops, or financial UX.
---

# ux-ui-human-in-the-loop

You have the `ux-ui-human-in-the-loop` skill. Use it when designing user interfaces for AI systems that require human oversight, trust, and interpretability.

## Core HITL Design Principles

1. **Transparency**: Show the AI reasoning, not just the answer
2. **Uncertainty Communication**: Display confidence levels visibly
3. **Actionable Overrides**: Always allow humans to intervene
4. **Audit Visibility**: Show what the AI did and why
5. **Progressive Disclosure**: Show summary first, details on demand

## UI Design Patterns for AI-Finance

### 1. Confidence Display
Never show AI output without uncertainty indication.

```html
<!-- Confidence Badge Component -->
<div class="prediction-card">
  <div class="prediction-value">+12.3% expected return</div>
  <div class="confidence-bar">
    <div class="confidence-fill" style="width: 78%"></div>
    <span class="confidence-label">78% confidence</span>
  </div>
  <div class="ci-range">90% CI: [+8.1%, +16.5%]</div>
</div>
```

**Color coding**:
- 🟢 >85% confidence → green
- 🟡 60–85% confidence → amber
- 🔴 <60% confidence → red + require human approval

### 2. Human Override UI
Every AI recommendation must have a visible override:

```
┌─────────────────────────────────────────────┐
│  🤖 AI Recommendation                        │
│  Buy 500 shares AAPL @ $189.50               │
│  Confidence: 82% │ Expected Alpha: +1.8%      │
├─────────────────────────────────────────────┤
│  [✅ Approve]  [✏️ Modify]  [❌ Reject]       │
│  Reason for override: ________________       │
└─────────────────────────────────────────────┘
```

### 3. Explainability Panel
Show top factors driving the AI decision:

```
Why did the AI recommend this?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
● Momentum signal      +0.42 ████████░░
● Earnings beat        +0.31 ██████░░░░
● Low volatility       +0.18 ████░░░░░░
● Macro headwinds      -0.15 ███░░░░░░░ (negative)
● Valuation stretch    -0.09 ██░░░░░░░░ (negative)
```

### 4. Risk Alert System

```
┌────────────────────────────────────────────┐
│  ⚠️  HIGH UNCERTAINTY DETECTED              │
│  This prediction has unusually wide        │
│  confidence intervals (+/-8.2%).           │
│                                            │
│  Suggested Action: Reduce position size    │
│  or wait for more data before acting.      │
│                                            │
│  [Proceed Anyway]  [Defer to Tomorrow]     │
└────────────────────────────────────────────┘
```

## Dashboard Design Guidelines

### Financial AI Dashboard Layout
```
┌──────────────────────────────────────────────────────┐
│  HEADER: Portfolio Overview | Status | Alerts (3)    │
├───────────────┬──────────────────────────────────────┤
│               │                                      │
│  NAVIGATION   │   MAIN CONTENT AREA                  │
│  ─ Dashboard  │   ┌──────────┐ ┌──────────┐         │
│  ─ Signals    │   │ Returns  │ │  Risk    │         │
│  ─ Risk       │   │ Chart    │ │ Metrics  │         │
│  ─ Compliance │   └──────────┘ └──────────┘         │
│  ─ Reports    │   ┌──────────────────────────┐       │
│  ─ Audit Log  │   │  AI Recommendations +    │       │
│               │   │  HITL Approval Queue     │       │
│               │   └──────────────────────────┘       │
└───────────────┴──────────────────────────────────────┘
```

### Color System for Finance
```css
:root {
  --profit-green: #00C087;
  --loss-red: #FF4757;
  --warning-amber: #FFB300;
  --neutral-blue: #2196F3;
  --background-dark: #0A0E1A;
  --surface: #141828;
  --surface-elevated: #1E2340;
  --text-primary: #FFFFFF;
  --text-secondary: #8B9BB4;
  --border: #2A3150;
}
```

## HITL Workflow Design

### Approval Queue
```
Priority Queue Items:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[HIGH]  Portfolio rebalance — $2.3M impact  → [Review]
[MED]   Anomaly detected in TSLA position   → [Review]
[LOW]   Routine risk report generated       → [View]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Avg review time: 2.3 min | SLA: 15 min
```

### Feedback Loop
After every human decision:
1. Capture the decision (approve/modify/reject)
2. Capture the reason (dropdown + free text)
3. Store for model retraining / RLHF
4. Show the human how often AI was right on similar decisions

## Accessibility & Trust

- **Audit Log Page**: Every AI action visible to compliance officers
- **Model Card**: Show model version, training date, performance metrics
- **Confidence Calibration**: Show historical accuracy vs stated confidence
- **Mobile-Responsive**: Approval workflows must work on mobile

## Verification Checklist

- [ ] Confidence/uncertainty is always visible alongside predictions
- [ ] Human override is always one click away
- [ ] Explainability factors are shown for high-stakes decisions
- [ ] Risk alerts use appropriate severity levels and colors
- [ ] Approval queue has SLA timers and escalation
- [ ] All decisions are logged for audit
- [ ] Interface is accessible (WCAG 2.1 AA)

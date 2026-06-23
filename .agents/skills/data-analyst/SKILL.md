---
name: data-analyst
description: Use when analyzing data for business decisions, designing statistical or ML algorithms, creating data visualizations, or presenting insights to stakeholders. For trend detection, attribution modeling, A/B testing, user segmentation, and executive reporting.
---

# Data Analyst

Transform data into actionable insights and compelling narratives that drive business decisions.

## Overview

This skill combines rigorous statistical methodology with effective data storytelling. It helps you:
1. **Analyze**: Choose and apply the right statistical/ML methods
2. **Design**: Create thresholds, metrics, and decision logic
3. **Communicate**: Present insights that inspire action

## When to Use This Skill

- **Algorithm Design**: Designing data analysis algorithms or judgment logic
- **Method Selection**: Choosing between statistical tests, regression, or ML methods
- **Threshold Design**: Setting decision boundaries or classification criteria
- **Trend Analysis**: Detecting changes, growth patterns, or anomalies
- **Attribution**: Understanding what drives conversion or outcomes
- **Executive Reporting**: Presenting analytics to stakeholders
- **A/B Testing**: Designing and interpreting experiments

### Example Triggers

- "How should I detect if a keyword is trending up?"
- "What statistical test should I use to compare these groups?"
- "How do I present these findings to executives?"
- "What attribution model should I use?"
- "How do I design thresholds for user segmentation?"

## Workflow

```
Problem → Classify → Select Method → Design Metrics → Set Thresholds → Tell Story
```

### Step 1: Problem Classification

| Type | Description | Methods |
|------|-------------|---------|
| **Trend** | Time series changes, growth detection | Stationarity tests, change point detection |
| **Comparison** | A/B tests, group differences | t-test, ANOVA, effect sizes |
| **Attribution** | What drives outcomes | Regression, attribution models |
| **Segmentation** | User/item grouping | Clustering, classification |
| **Anomaly** | Outlier detection | Z-scores, IQR, thresholds |

### Step 2: Method Selection

Consult reference files for detailed guidance:

| Problem | Reference | Key Methods |
|---------|-----------|-------------|
| Trend analysis | `references/time_series.md` | Stationarity, decomposition, change points |
| Comparisons | `references/statistical_inference.md` | t-tests, ANOVA, effect sizes |
| Prediction | `references/regression_attribution.md` | Linear/logistic regression |
| Segmentation | `references/ml_methods.md` | K-means, hierarchical clustering |
| Thresholds | `references/threshold_design.md` | Percentiles, multipliers, ROC |
| Quick decision | `references/method_selection.md` | Decision tree for all types |

### Step 3: Design Metrics

1. **Choose the right metric** for what you measure
2. **Define calculation** clearly
3. **Handle edge cases** (zeros, missing data)
4. **Establish baseline** for comparison

### Step 4: Set Thresholds

| Approach | Method | Example |
|----------|--------|---------|
| **Statistical** | Mean ± Nσ, percentiles | Top 10% = 90th percentile |
| **Business** | Multipliers, minimums | Growth = 2x baseline |
| **Data-driven** | Distribution breaks, ROC | Optimal F1 threshold |

### Step 5: Tell the Story

Transform analysis into narrative using the storytelling framework below.

---

## Core Methodology

### Trend Detection

**Growth Detection**:
```
growth_ratio = current_mean / baseline_mean

if growth_ratio >= 2.0: "GROWING"
elif growth_ratio >= 1.5: "MODERATE_GROWTH"  
elif growth_ratio <= 0.5: "DECLINING"
else: "STABLE"
```

**Stability (Coefficient of Variation)**:
```
CV = std_dev / mean

CV < 0.3: Stable
CV 0.3-0.5: Moderate
CV > 0.5: Volatile
```

### Statistical Comparison

| Scenario | Normal Data | Non-Normal |
|----------|-------------|------------|
| 2 groups | t-test | Mann-Whitney |
| 3+ groups | ANOVA | Kruskal-Wallis |
| Paired | Paired t-test | Wilcoxon |

**Always report**: Test statistic, p-value, effect size (Cohen's d), confidence interval.

### Attribution Models

| Model | Credit Distribution | Best For |
|-------|---------------------|----------|
| First-touch | 100% to first | Awareness |
| Last-touch | 100% to last | Conversion |
| Linear | Equal split | Balanced view |
| Position-based | 40/20/40 | Default choice |
| Data-driven | ML-based | Large datasets |

### ML vs Statistics

| Use Statistics | Use ML |
|----------------|--------|
| Testing hypotheses | Discovering patterns |
| Understanding "why" | Predicting "what" |
| Small samples | Large datasets |
| Need interpretability | Need accuracy |

---

## Storytelling Framework

### Narrative Arc

```
1. Hook: Surprising insight that grabs attention
2. Context: Baseline and benchmarks
3. Rising Action: Build through data points
4. Climax: The key insight
5. Resolution: Recommendations
6. Call to Action: Specific next steps
```

### Story Structures

**Problem-Solution**:
```markdown
## The Hook
"We're losing $2.4M annually to preventable churn."

## The Problem
Analysis reveals 73% churn within first 90 days.
Common factor: < 3 support interactions.

## The Insight
Customers who don't engage in first 14 days
are 4x more likely to churn.

## The Solution
1. Implement 14-day onboarding sequence
2. Proactive outreach at day 7

## Expected Impact
- Reduce early churn by 40%
- Save $960K annually
```

**Comparison Story**:
Use weighted scoring matrices for strategic decisions.

| Factor | Weight | Option A | Option B |
|--------|--------|----------|----------|
| Size | 25% | 5 | 4 |
| Growth | 30% | 3 | 5 |
| Risk | 20% | 2 | 4 |
| **Total** | | **3.2** | **4.4** |

### Visualization Techniques

**Progressive Reveal**:
- Slide 1: "Revenue is growing" [line chart]
- Slide 2: "But growth is slowing" [add trend line]
- Slide 3: "Driven by one segment" [add breakdown]
- Slide 4: "Which is saturating" [add forecast]

**Headline Formula**:
```
[Specific Number] + [Business Impact] + [Actionable Context]

BAD: "Q4 Sales Analysis"
GOOD: "Q4 Sales Beat Target by 23% - Here's Why"
```

### Handling Uncertainty

- "With 95% confidence, we can say..."
- "Impact estimate: $400K-$600K"
- "Correlation is strong, but causation requires..."

---

## Reference Files

Detailed methodology in `references/`:

| File | Content |
|------|---------|
| `method_selection.md` | Quick decision tree for all analysis types |
| `time_series.md` | Stationarity, trends, forecasting |
| `statistical_inference.md` | Hypothesis testing, effect sizes |
| `regression_attribution.md` | Regression, attribution models |
| `ml_methods.md` | Clustering, classification, PCA |
| `threshold_design.md` | Threshold setting methodologies |

---

## Best Practices

### Analysis
- Start with the decision: What action will this inform?
- Choose appropriate complexity: Match method to data quality
- Document assumptions: State what must hold
- Design for edge cases: Handle zeros, nulls, outliers
- Validate: Test on holdout data or A/B test

### Communication
- Lead with the "so what": Front-load insights
- Use the rule of three: Three points, three comparisons
- Show, don't tell: Let data speak with visuals
- End with action: Clear, specific next steps
- Match vocabulary: Avoid jargon for non-technical audiences

### Common Mistakes
- Data dumping without narrative
- Burying the key insight
- Ignoring statistical significance vs practical significance
- Not reporting effect sizes alongside p-values
- Overcomplicating when simple methods suffice

# Method Selection Guide

Quick reference for choosing the right analysis method based on your problem type.

## Decision Tree: What Method Do I Need?

```
START
│
├─ What are you trying to do?
│
├─ UNDERSTAND CHANGE OVER TIME
│  └─ Is it a time series?
│     ├─ YES → See "Time Series Methods"
│     └─ NO → Compare groups (before/after) → See "Comparison Methods"
│
├─ COMPARE GROUPS
│  └─ How many groups?
│     ├─ 2 groups → t-test or Mann-Whitney
│     └─ 3+ groups → ANOVA or Kruskal-Wallis
│
├─ FIND RELATIONSHIPS
│  └─ What's the outcome type?
│     ├─ Continuous → Linear regression
│     ├─ Binary (yes/no) → Logistic regression
│     └─ Count → Poisson regression
│
├─ SEGMENT/GROUP DATA
│  └─ Do you have labels?
│     ├─ YES → Classification (supervised)
│     └─ NO → Clustering (unsupervised)
│
├─ ATTRIBUTE CREDIT
│  └─ See "Attribution Methods"
│
└─ DETECT ANOMALIES
   └─ See "Threshold Design"
```

---

## Time Series Methods

### When to Use Each

| Problem | Method | Reference |
|---------|--------|-----------|
| Is the series stable or changing? | Stationarity tests (ADF, KPSS) | time_series.md |
| What's the underlying trend? | Trend decomposition (STL) | time_series.md |
| When did a significant change occur? | Change point detection | time_series.md |
| What will happen next? | Forecasting (ARIMA, exponential smoothing) | time_series.md |
| Is there a seasonal pattern? | Seasonal decomposition | time_series.md |

### Quick Recommendations

**For trend detection (e.g., Google Trends data)**:
1. Check stationarity first
2. Use STL decomposition to separate trend from noise
3. Apply change point detection for inflection points
4. Compare pre/post means for growth quantification

---

## Comparison Methods

### Continuous Outcome

| Scenario | Normal Data | Non-Normal Data |
|----------|-------------|-----------------|
| 2 independent groups | Independent t-test | Mann-Whitney U |
| 2 paired groups | Paired t-test | Wilcoxon signed-rank |
| 3+ independent groups | One-way ANOVA | Kruskal-Wallis |
| 3+ paired groups | Repeated measures ANOVA | Friedman test |

### Categorical Outcome

| Scenario | Method |
|----------|--------|
| 2x2 table | Chi-square or Fisher's exact |
| Larger table | Chi-square |
| Before/after same subjects | McNemar's test |

### Key Considerations

- **Check normality**: Use Shapiro-Wilk test if n < 50
- **Check variance equality**: Use Levene's test
- **Always report effect size**: Cohen's d, eta-squared, etc.

---

## Relationship Methods (Regression)

### Linear Regression
- **Use when**: Predicting continuous outcome
- **Assumptions**: Linearity, normality of residuals, homoscedasticity
- **Output**: Coefficients show effect of each predictor

### Logistic Regression
- **Use when**: Predicting binary outcome (yes/no, convert/not)
- **Output**: Odds ratios, probability predictions
- **Example**: Conversion rate modeling

### When to Use Multiple Predictors
- Control for confounding variables
- Understand relative importance
- Build prediction models

---

## Segmentation Methods

### Clustering (Unsupervised)

| Method | Best For | Key Parameter |
|--------|----------|---------------|
| K-means | Spherical clusters, known K | Number of clusters (k) |
| Hierarchical | Unknown K, need dendrogram | Distance metric, linkage |
| DBSCAN | Arbitrary shapes, outliers | Epsilon, min_samples |

### Classification (Supervised)

| Method | Interpretability | Accuracy | Best For |
|--------|------------------|----------|----------|
| Logistic regression | High | Moderate | Binary outcomes, interpretability needed |
| Decision tree | High | Moderate | Rule extraction |
| Random forest | Low | High | Accuracy priority |

### Choosing Between Clustering and Classification

- **Have labeled examples?** → Classification
- **Discovering natural groups?** → Clustering
- **Need to explain rules?** → Decision tree or logistic

---

## Attribution Methods

### Models Comparison

| Model | Calculation | Pros | Cons |
|-------|-------------|------|------|
| First-touch | 100% to first interaction | Simple | Ignores journey |
| Last-touch | 100% to last interaction | Simple | Ignores awareness |
| Linear | Equal split | Fair | May not reflect reality |
| Time-decay | Recent gets more | Reflects recency | Arbitrary decay rate |
| Position-based | 40/20/40 | Balanced | Arbitrary weights |
| Data-driven | ML-based | Accurate | Needs lots of data |

### When to Use Each

- **Awareness campaigns**: First-touch
- **Conversion optimization**: Last-touch
- **Holistic view**: Linear or position-based
- **Sufficient data**: Data-driven

---

## Quick Reference: Common Scenarios

### "Is this keyword trending up?"
1. Get time series data (90 days)
2. Apply change point detection
3. Compare post-change mean vs pre-change mean
4. If ratio >= 2x → Significant growth

### "Are these two groups different?"
1. Check normality of both groups
2. If normal → t-test; else → Mann-Whitney
3. Calculate effect size (Cohen's d)
4. Report: test statistic, p-value, effect size, CI

### "What drives conversion?"
1. Collect predictor variables
2. Fit logistic regression
3. Check odds ratios
4. Top predictors = largest absolute coefficients

### "How do I segment users?"
1. Define features for segmentation
2. Standardize features
3. Use elbow method to choose k
4. Apply K-means clustering
5. Profile each cluster

### "What threshold should I use?"
1. See `threshold_design.md`
2. Consider: statistical (percentile), business (multiplier), or data-driven

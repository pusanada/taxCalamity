# Threshold Design Guide

Methods for setting decision boundaries, classification criteria, and detection thresholds.

## Why Thresholds Matter

Thresholds turn continuous data into actionable decisions:
- "Is this keyword trending?" → growth_ratio > threshold
- "Is this user high-value?" → lifetime_value > threshold
- "Is this metric anomalous?" → value > upper_threshold OR value < lower_threshold

**Bad thresholds** lead to:
- Too many false positives (alert fatigue)
- Too many false negatives (missed opportunities)
- Inconsistent decisions

## Threshold Selection Methods

### 1. Statistical Approaches

#### Percentile-Based

Use when you want to identify "top X%" or "bottom X%".

| Percentile | Use Case |
|------------|----------|
| Top 1% (99th percentile) | Extreme outliers, rare events |
| Top 5% (95th percentile) | Significant outliers |
| Top 10% (90th percentile) | High performers |
| Top 25% (75th percentile) | Above average |

**Formula**: `threshold = np.percentile(data, percentile)`

**Example**: "Flag keywords in the top 10% of growth"
```
threshold = percentile(all_growth_ratios, 90)
is_high_growth = growth_ratio >= threshold
```

#### Standard Deviation-Based

Use when data is approximately normal.

| Threshold | Interpretation | % Outside (Normal) |
|-----------|----------------|-------------------|
| Mean ± 1σ | Slightly unusual | 32% |
| Mean ± 2σ | Unusual | 5% |
| Mean ± 3σ | Highly unusual | 0.3% |

**Formula**: `threshold = mean ± (n × std_dev)`

**Example**: "Flag metrics more than 2 standard deviations above normal"
```
upper_threshold = mean + 2 * std_dev
is_anomaly = value > upper_threshold
```

#### IQR-Based (Robust to Outliers)

Use when data has outliers that would distort mean/std.

```
Q1 = 25th percentile
Q3 = 75th percentile
IQR = Q3 - Q1

Lower bound = Q1 - 1.5 × IQR
Upper bound = Q3 + 1.5 × IQR
```

**Advantage**: Not affected by extreme values

---

### 2. Business-Driven Approaches

#### Multiplier-Based

Use when you care about relative change.

| Multiplier | Meaning | Use Case |
|------------|---------|----------|
| 1.5x | 50% increase | Moderate growth |
| 2x | 100% increase | Significant growth |
| 3x | 200% increase | Strong growth |
| 5x | 400% increase | Explosive growth |
| 10x | 900% increase | Viral growth |

**Example**: "A keyword is 'growing' if current period is 2x the baseline"
```
is_growing = current_mean / baseline_mean >= 2.0
```

#### Absolute Minimums

Use when there's a baseline requirement regardless of relative change.

**Examples**:
- Minimum search volume: `volume >= 1000`
- Minimum conversion rate: `cvr >= 0.01`
- Minimum sample size: `n >= 30`

#### ROI/Cost-Based

Use when there's a business breakeven point.

**Example**: "Only target keywords where expected revenue > cost"
```
threshold_traffic = cost / (conversion_rate × avg_order_value)
```

---

### 3. Data-Driven Approaches

#### Distribution Breaks

Use when data naturally clusters.

**Method**:
1. Plot histogram of the metric
2. Look for natural gaps or modes
3. Set threshold at the gap

**Tools**:
- Kernel density estimation (KDE)
- Gaussian mixture models (for formal break detection)

#### Precision-Recall Tradeoff

Use when you have labeled examples (ground truth).

**Method**:
1. Calculate precision and recall at various thresholds
2. Choose threshold based on priority:
   - High precision: fewer false positives
   - High recall: fewer false negatives
   - F1 optimal: balance both

**Visualization**: Precision-recall curve with threshold annotations

#### ROC Curve

Use for binary classification with known labels.

**Method**:
1. Plot true positive rate vs false positive rate
2. Choose threshold based on:
   - Youden's J: Maximize (TPR - FPR)
   - Cost-sensitive: Weight FP and FN costs

---

## Designing Multi-Threshold Classification

### MECE Categories

Categories should be:
- **Mutually Exclusive**: Each item in exactly one category
- **Collectively Exhaustive**: All items covered

**Good example**:
```
if growth_ratio >= 3.0 and days_since_start <= 14:
    category = "RISING"
elif level >= high_threshold and cv < 0.3:
    category = "STABLE_HIGH"
elif was_high and current_momentum < 0:
    category = "COOLING"
elif cv > 0.5:
    category = "VOLATILE"
else:
    category = "STABLE_LOW"
```

### Priority Ordering

When conditions might overlap, order matters.

**Principle**: Check most important/specific conditions first.

```
# Good: Specific to general
if is_explosive_growth():     # Very rare, high priority
    return "EXPLOSIVE"
elif is_growing():            # Less rare
    return "GROWING"
elif is_stable():             # Common
    return "STABLE"
else:                         # Default
    return "LOW"
```

### Decision Matrix

For complex multi-factor decisions:

| Growth | Stability | Recency | → Category |
|--------|-----------|---------|------------|
| High (≥2x) | Any | Recent (≤14d) | RISING |
| High | High (CV<0.3) | Old | STABLE_HIGH |
| Declining | Any | Any | COOLING |
| Low | High | Any | STABLE_LOW |
| Any | Low (CV>0.5) | Any | VOLATILE |

---

## Threshold Validation

### Historical Backtesting

1. Apply thresholds to historical data
2. Calculate metrics:
   - How many items flagged?
   - Of those flagged, how many were actually [outcome]?
   - Of actual [outcomes], how many were flagged?

### A/B Testing

1. Randomly split traffic/keywords
2. Apply different thresholds to each group
3. Measure downstream business metric
4. Choose threshold with better outcome

### Sensitivity Analysis

1. Vary threshold ±10%, ±20%, ±50%
2. See how many items change category
3. If very sensitive: consider using soft boundaries

---

## Common Patterns

### Growth Detection

```
# Baseline: first 30 days
baseline_mean = mean(first_30_days)

# Current: last 7 days
current_mean = mean(last_7_days)

# Growth ratio
growth_ratio = current_mean / baseline_mean

# Classification
if growth_ratio >= 2.0:
    status = "GROWING"
elif growth_ratio >= 1.5:
    status = "MODERATE_GROWTH"
elif growth_ratio <= 0.5:
    status = "DECLINING"
else:
    status = "STABLE"
```

### Stability Detection

```
# Coefficient of variation
cv = std_dev / mean

# Classification
if cv < 0.2:
    stability = "VERY_STABLE"
elif cv < 0.3:
    stability = "STABLE"
elif cv < 0.5:
    stability = "MODERATE"
else:
    stability = "VOLATILE"
```

### Anomaly Detection

```
# Z-score method
z_score = (value - mean) / std_dev

if abs(z_score) > 3:
    status = "ANOMALY"
elif abs(z_score) > 2:
    status = "WARNING"
else:
    status = "NORMAL"
```

### Recency Weighting

```
# Days since event
days_since = (today - event_date).days

# Recency score (1 = today, 0 = very old)
recency_score = exp(-days_since / half_life)

# With half_life = 14 days:
#   0 days ago: 1.00
#   7 days ago: 0.61
#   14 days ago: 0.37
#   30 days ago: 0.12
```

---

## Best Practices

### Documentation

For each threshold, document:
1. **What it measures**: The metric and its meaning
2. **Why this value**: Statistical or business justification
3. **Expected behavior**: How many items should trigger
4. **Review schedule**: When to re-evaluate

### Dynamic Thresholds

Consider thresholds that adapt:
- **Seasonal**: Different thresholds for holidays
- **Rolling**: Recalculate based on recent data
- **Segmented**: Different thresholds per category

### Avoiding Common Mistakes

1. **Round numbers without justification**: "2x" should have data backing
2. **Too many thresholds**: Keep classification simple (3-5 categories max)
3. **Never revisiting**: Thresholds should be reviewed periodically
4. **Ignoring edge cases**: What happens at exactly the threshold?
5. **Threshold = cliff**: Consider gradual scoring near boundaries

### Threshold Hygiene

- Start simple, add complexity only if needed
- Prefer fewer categories over many
- Use clear, descriptive category names
- Build in a review cycle (quarterly, etc.)
- Monitor threshold effectiveness over time

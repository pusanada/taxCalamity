# Regression and Attribution Analysis

Methods for understanding relationships, modeling outcomes, and attributing credit across touchpoints.

## Linear Regression

### When to Use

- Predicting a continuous outcome from one or more predictors
- Understanding how variables relate to each other
- Controlling for confounding variables

### Key Concepts

#### The Model

```
Y = β₀ + β₁X₁ + β₂X₂ + ... + ε
```

- **Y**: Outcome variable (continuous)
- **β₀**: Intercept (value when all X = 0)
- **β₁, β₂...**: Coefficients (effect of each predictor)
- **ε**: Error term

#### Interpreting Coefficients

- **Coefficient value**: For each 1-unit increase in X, Y changes by β units
- **Sign**: Positive = direct relationship, Negative = inverse relationship
- **Statistical significance**: p < 0.05 means coefficient is reliably different from zero

#### Model Fit

| Metric | Meaning | Good Value |
|--------|---------|------------|
| R² | Variance explained | Depends on domain, 0.7+ is often good |
| Adjusted R² | R² penalized for extra predictors | Close to R² |
| RMSE | Average prediction error | Lower is better |
| F-statistic | Overall model significance | p < 0.05 |

### Assumptions

1. **Linearity**: Relationship between X and Y is linear
2. **Independence**: Observations are independent
3. **Homoscedasticity**: Constant variance of residuals
4. **Normality**: Residuals are normally distributed
5. **No multicollinearity**: Predictors aren't highly correlated

### When Assumptions Fail

| Problem | Detection | Solution |
|---------|-----------|----------|
| Non-linear relationship | Residual plots | Transform variables, use polynomial terms |
| Heteroscedasticity | Residual plots | Use robust standard errors, transform Y |
| Multicollinearity | VIF > 5-10 | Remove or combine correlated predictors |
| Non-normal residuals | Q-Q plot | Often OK with large samples, or transform Y |

---

## Logistic Regression

### When to Use

- Predicting binary outcomes (yes/no, convert/not convert, click/no click)
- Understanding what drives conversion
- Calculating probability of an outcome

### Key Concepts

#### The Model

```
log(p / (1-p)) = β₀ + β₁X₁ + β₂X₂ + ...
```

- **p**: Probability of the outcome
- **log(p / (1-p))**: Log-odds (logit)

#### Interpreting Results

**Odds Ratio (OR)** = exp(β)

| OR Value | Interpretation |
|----------|----------------|
| OR = 1 | No effect |
| OR > 1 | Increases odds of outcome |
| OR < 1 | Decreases odds of outcome |

**Example**: OR = 2.5 means the odds of conversion are 2.5x higher for each unit increase in X.

#### Model Evaluation

| Metric | Purpose |
|--------|---------|
| AUC-ROC | Discrimination ability (0.5 = random, 1.0 = perfect) |
| Accuracy | Overall correct predictions |
| Precision | Of predicted positives, how many are correct |
| Recall | Of actual positives, how many were found |

### For Conversion Modeling

Common predictors for conversion:
- Traffic source/channel
- Device type
- Time on site
- Pages viewed
- Previous visits
- Cart value

**Practical interpretation**:
- Identify top predictors by coefficient magnitude
- Focus optimization on modifiable factors
- Use probability scores for segmentation

---

## Attribution Models

### The Attribution Problem

When a customer interacts with multiple touchpoints before converting, how do you credit each touchpoint?

### Model Comparison

| Model | Credit Distribution | Pros | Cons |
|-------|---------------------|------|------|
| **First-touch** | 100% to first interaction | Simple, emphasizes awareness | Ignores conversion drivers |
| **Last-touch** | 100% to last interaction | Simple, emphasizes conversion | Ignores awareness building |
| **Linear** | Equal split across all | Fair, considers full journey | May not reflect reality |
| **Time-decay** | More to recent touches | Reflects recency effect | Arbitrary decay rate |
| **Position-based** | 40% first, 40% last, 20% middle | Balanced approach | Arbitrary weights |
| **Data-driven** | ML-based on actual paths | Most accurate | Needs lots of data |

### When to Use Each

| Model | Best For |
|-------|----------|
| First-touch | Measuring awareness campaigns, top-of-funnel |
| Last-touch | Optimizing conversion, bottom-of-funnel |
| Linear | When all touchpoints seem equally important |
| Time-decay | Short purchase cycles, impulse buys |
| Position-based | Default choice when unsure |
| Data-driven | When you have >10,000 conversions |

### Implementing Attribution

**Basic approach**:
1. Collect user journey data (all touchpoints before conversion)
2. Choose an attribution model
3. Distribute conversion credit according to model
4. Aggregate credit by channel/campaign

**Time-decay formula**:
```
weight[i] = decay_rate ^ (days_from_conversion[i])
normalized_weight[i] = weight[i] / sum(all_weights)
```

**Position-based formula** (40-20-40):
```
if only_one_touch: credit = 100%
if two_touches: credit = 50% each
if three+:
  first_touch: 40%
  last_touch: 40%
  middle_touches: 20% / (n - 2) each
```

---

## Causal Inference Basics

### Correlation vs Causation

**Correlation**: X and Y move together
**Causation**: X actually causes Y to change

### Common Confounds

| Confound | Example |
|----------|---------|
| **Spurious correlation** | Ice cream sales and drowning (both caused by summer) |
| **Reverse causation** | Does exercise cause happiness, or do happy people exercise? |
| **Selection bias** | Users who see ads are already more likely to convert |
| **Omitted variables** | Leaving out a variable that affects both X and Y |

### Establishing Causality

| Method | How It Works | When to Use |
|--------|--------------|-------------|
| **Randomized experiment** | Randomly assign treatment | Gold standard, if feasible |
| **A/B testing** | Random split of users | Web experiments |
| **Difference-in-differences** | Compare changes over time | Natural experiments |
| **Regression discontinuity** | Threshold-based treatment | When there's a cutoff |
| **Propensity score matching** | Match treated to similar untreated | Observational data |
| **Instrumental variables** | Find a variable that only affects X | When you have a valid instrument |

### For Business Decisions

**Questions to ask**:
1. Is this just correlation, or can we establish causation?
2. Are there confounding variables we haven't controlled for?
3. Would an A/B test be feasible to verify the effect?

**When to trust regression results for causal claims**:
- Important confounders are controlled for
- No obvious reverse causation
- Results replicate across different samples
- Effect size is plausible

---

## Practical Applications

### Conversion Rate Analysis

1. Define conversion event clearly
2. Collect predictor variables
3. Fit logistic regression
4. Identify top predictors (largest |coefficients|)
5. Focus optimization on actionable predictors

### Channel Attribution

1. Collect user journey data
2. Choose model based on business goals:
   - Optimizing awareness? → First-touch
   - Optimizing conversion? → Last-touch
   - Balanced view? → Position-based or linear
3. Calculate attributed conversions per channel
4. Compare to spend for ROI analysis

### What Drives [Metric]?

1. List potential drivers (hypotheses)
2. Collect data on each potential driver
3. Fit regression model
4. Examine:
   - Which coefficients are significant?
   - Which have the largest effect size?
   - Are there interaction effects?
5. Validate findings with holdout data or A/B test

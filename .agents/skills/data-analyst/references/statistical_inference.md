# Statistical Inference

Methods for drawing conclusions from data, testing hypotheses, and quantifying uncertainty.

## Hypothesis Testing Framework

### The Logic

1. **State hypotheses**:
   - Null (H₀): No effect, no difference
   - Alternative (H₁): There is an effect or difference

2. **Choose significance level (α)**: Usually 0.05

3. **Calculate test statistic**: Depends on the test

4. **Get p-value**: Probability of seeing this result if H₀ is true

5. **Make decision**:
   - p < α: Reject H₀ (evidence for effect)
   - p ≥ α: Fail to reject H₀ (insufficient evidence)

### Interpreting P-values

| P-value | Evidence Against H₀ |
|---------|---------------------|
| p > 0.10 | Weak or no evidence |
| 0.05 < p < 0.10 | Marginal |
| 0.01 < p < 0.05 | Moderate |
| 0.001 < p < 0.01 | Strong |
| p < 0.001 | Very strong |

**Caution**: A small p-value does NOT mean:
- The effect is large (could be tiny effect with big sample)
- The null is false (could be false positive)
- The result is practically important

---

## Test Selection Guide

### Comparing Two Groups

#### Continuous Outcome

| Scenario | Normal Data | Non-Normal Data |
|----------|-------------|-----------------|
| Independent groups | Independent t-test | Mann-Whitney U |
| Paired/matched | Paired t-test | Wilcoxon signed-rank |

**How to check normality**:
- Sample size < 50: Shapiro-Wilk test
- Sample size ≥ 50: Visual inspection (histogram, Q-Q plot)
- If p-value of normality test > 0.05: Approximately normal

#### Categorical Outcome

| Scenario | Method |
|----------|--------|
| 2x2 table, expected counts ≥ 5 | Chi-square test |
| 2x2 table, small expected counts | Fisher's exact test |
| Paired categories | McNemar's test |

### Comparing Three or More Groups

| Scenario | Normal Data | Non-Normal Data |
|----------|-------------|-----------------|
| Independent groups | One-way ANOVA | Kruskal-Wallis |
| Repeated measures | Repeated measures ANOVA | Friedman test |

**Post-hoc tests** (if overall test is significant):
- Tukey's HSD: All pairwise comparisons
- Bonferroni: Conservative, controls Type I error
- Dunnett: Compare all to control group

### Checking Assumptions

#### Normality
- **Test**: Shapiro-Wilk (n < 50), Kolmogorov-Smirnov (n ≥ 50)
- **Violated?**: Use non-parametric alternative or transform data

#### Homogeneity of Variance
- **Test**: Levene's test
- **Violated?**: Use Welch's t-test (robust to unequal variances)

#### Independence
- Check study design: Are observations truly independent?
- **Violated?**: Use paired tests or mixed models

---

## Effect Sizes

**Effect size** tells you the magnitude of an effect, independent of sample size.

### Always Report Effect Sizes

P-values tell you if an effect exists; effect sizes tell you if it matters.

### Common Effect Sizes

#### Cohen's d (Mean Differences)
```
d = (mean₁ - mean₂) / pooled_std_dev
```

| d | Interpretation |
|---|----------------|
| 0.2 | Small |
| 0.5 | Medium |
| 0.8 | Large |

#### Pearson's r (Correlation)

| r | Interpretation |
|---|----------------|
| 0.1 | Small |
| 0.3 | Medium |
| 0.5 | Large |

#### Eta-squared (η²) for ANOVA
```
η² = SS_between / SS_total
```

| η² | Interpretation |
|----|----------------|
| 0.01 | Small |
| 0.06 | Medium |
| 0.14 | Large |

#### Odds Ratio (Categorical)
- OR = 1: No association
- OR > 1: Increased odds
- OR < 1: Decreased odds

| OR | Interpretation |
|----|----------------|
| 1.5 | Small |
| 2.5 | Medium |
| 4.0 | Large |

### Confidence Intervals

Always report confidence intervals (usually 95%) for effect sizes:
- Gives range of plausible values
- Shows precision of estimate
- If CI excludes 0: Effect is significant at α = 0.05

---

## Sample Size and Power

### Power
Probability of detecting an effect that actually exists.
- Standard target: 80% power
- Higher stakes: 90% power

### Factors Affecting Power

| Factor | Increase Power By |
|--------|-------------------|
| Sample size | Increase n |
| Effect size | Larger true effect |
| Significance level | Use α = 0.10 instead of 0.05 |
| Variance | Reduce measurement error |

### Minimum Sample Size Guidelines

| Analysis | Rule of Thumb |
|----------|---------------|
| T-test | 30+ per group for robustness |
| Correlation | 30+ pairs for stability |
| Regression | 10-20 per predictor |
| Chi-square | Expected count ≥ 5 per cell |
| ANOVA | 20+ per group |

### When Sample Size Is Small

1. Use non-parametric tests (fewer assumptions)
2. Report exact p-values, not just < 0.05
3. Emphasize effect sizes over significance
4. Consider Bayesian methods
5. Be honest about uncertainty

---

## Multiple Comparisons

When testing multiple hypotheses, the chance of at least one false positive increases.

### The Problem

- 1 test at α = 0.05: 5% false positive chance
- 20 tests at α = 0.05: 64% chance of at least one false positive!

### Corrections

#### Bonferroni
```
adjusted_α = α / number_of_tests
```
- Most conservative
- Use when: Low number of tests, need strict control

#### Holm-Bonferroni
- Less conservative than Bonferroni
- Step-down procedure

#### False Discovery Rate (FDR)
- Controls proportion of false discoveries
- Use when: Many tests, discovery-oriented research

### When to Apply Corrections

- **Apply**: Pre-planned comparisons, confirmatory research
- **Don't apply**: Exploratory analysis (but be transparent)
- **Alternative**: Pre-register specific hypotheses

---

## Practical Recommendations

### Reporting Results

Include:
1. Test name and statistic
2. Degrees of freedom
3. P-value (exact, not just < 0.05)
4. Effect size with confidence interval
5. Sample sizes per group

Example:
> "The treatment group (M = 75.2, SD = 8.5, n = 48) scored significantly higher than control (M = 68.3, SD = 9.2, n = 52), t(98) = 3.82, p < .001, Cohen's d = 0.77, 95% CI [0.36, 1.18]."

### Common Mistakes to Avoid

1. **P-hacking**: Testing until you find p < 0.05
2. **Ignoring effect size**: Statistical ≠ practical significance
3. **Confusing p > 0.05 with "no effect"**: It means "not enough evidence"
4. **Not checking assumptions**: Leads to invalid results
5. **Multiple testing without correction**: Inflated false positives

### Decision Framework

```
1. Define question clearly
2. Choose test BEFORE seeing data
3. Check assumptions
4. Run test
5. Report: test stat, df, p-value, effect size, CI
6. Interpret in context
7. Acknowledge limitations
```

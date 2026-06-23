---
name: uncertainty-quantification
description: Apply Uncertainty Quantification (UQ) methods to AI/ML models and financial systems, including confidence intervals, Monte Carlo simulation, Bayesian inference, ensemble methods, and calibration. Triggers on requests about UQ, model confidence, prediction intervals, probabilistic forecasting, or risk-aware AI.
---

# uncertainty-quantification

You have the `uncertainty-quantification` skill. Use it when the user needs to quantify, communicate, or reduce uncertainty in model outputs or data.

## Types of Uncertainty

### 1. Aleatoric Uncertainty (Irreducible)
- Inherent randomness in data (e.g., market noise)
- Cannot be reduced with more data
- Quantified via predictive distributions

### 2. Epistemic Uncertainty (Reducible)
- Uncertainty due to lack of knowledge or data
- Can be reduced with more/better data or models
- Quantified via model ensembles, Bayesian methods

## Core UQ Methods

### Monte Carlo Simulation
```python
import numpy as np

def monte_carlo_forecast(model, X, n_simulations=10000):
    predictions = []
    for _ in range(n_simulations):
        noise = np.random.normal(0, 1, X.shape)
        pred = model.predict(X + noise)
        predictions.append(pred)
    return np.array(predictions)

results = monte_carlo_forecast(model, X)
mean = results.mean(axis=0)
ci_lower = np.percentile(results, 2.5, axis=0)
ci_upper = np.percentile(results, 97.5, axis=0)
```

### Conformal Prediction
- Distribution-free prediction intervals
- Guaranteed coverage with finite samples
- Works with any base model

### Bayesian Neural Networks
- Place priors over model weights
- Posterior approximation via variational inference or MCMC
- Libraries: `pyro`, `tensorflow-probability`, `numpyro`

### Deep Ensembles
```python
# Train N independent models
ensemble = [train_model(X_train, y_train, seed=i) for i in range(10)]

# Aggregate predictions
preds = np.array([m.predict(X_test) for m in ensemble])
mean_pred = preds.mean(axis=0)
epistemic_uncertainty = preds.var(axis=0)
```

### Quantile Regression
- Directly models conditional quantiles
- No distributional assumptions
- Useful for asymmetric risks

## Calibration

A model is well-calibrated if its stated confidence matches empirical frequency.

```python
from sklearn.calibration import calibration_curve

# Check calibration
fraction_positive, mean_predicted = calibration_curve(y_true, y_prob, n_bins=10)
```

**Calibration tools**: Platt scaling, isotonic regression, temperature scaling

## For AI-Finance Context

### Portfolio Risk UQ
- Confidence intervals on expected returns
- VaR/CVaR with uncertainty bands
- Scenario-based stress testing with probability weights

### Model Risk
- Quantify uncertainty from model misspecification
- Compare multiple models and report disagreement
- Flag high-uncertainty predictions for human review

### Reporting UQ to Users
Always report:
1. **Point estimate** — the best single prediction
2. **Confidence interval** — e.g., 90% CI
3. **Uncertainty source** — aleatoric vs epistemic
4. **Action threshold** — when uncertainty is too high to act

## Libraries

| Library | Use Case |
|---------|----------|
| `scipy.stats` | Distributions, confidence intervals |
| `sklearn.calibration` | Calibration curves |
| `mapie` | Conformal prediction |
| `pyro` | Bayesian deep learning |
| `numpyro` | Fast Bayesian inference |
| `uncertainty-toolbox` | UQ metrics and visualization |

## Verification Checklist

- [ ] Uncertainty type (aleatoric/epistemic) is identified
- [ ] Appropriate UQ method is chosen for the model type
- [ ] Calibration is verified empirically
- [ ] Confidence intervals are reported alongside predictions
- [ ] High-uncertainty outputs are flagged for human review

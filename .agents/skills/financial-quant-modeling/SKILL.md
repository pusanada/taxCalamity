---
name: financial-quant-modeling
description: Build, implement, and validate quantitative financial models including factor models, pricing models, portfolio optimization, risk metrics (VaR, CVaR, Sharpe), backtesting, and time-series forecasting. Triggers on requests about quant finance, asset pricing, portfolio construction, backtesting, alpha signals, or financial modeling.
---

# financial-quant-modeling

You have the `financial-quant-modeling` skill. Use it when the user needs quantitative financial analysis, modeling, or strategy development.

## Core Financial Modeling Areas

### 1. Portfolio Optimization

#### Mean-Variance Optimization (Markowitz)
```python
import numpy as np
import cvxpy as cp

def mean_variance_optimize(expected_returns, cov_matrix, risk_aversion=1.0):
    n = len(expected_returns)
    w = cp.Variable(n)
    
    portfolio_return = expected_returns @ w
    portfolio_risk = cp.quad_form(w, cov_matrix)
    
    objective = cp.Maximize(portfolio_return - risk_aversion * portfolio_risk)
    constraints = [cp.sum(w) == 1, w >= 0]
    
    problem = cp.Problem(objective, constraints)
    problem.solve()
    return w.value
```

#### Black-Litterman Model
- Combines market equilibrium with investor views
- Produces more stable, diversified portfolios
- Libraries: `PyPortfolioOpt`

### 2. Risk Metrics

```python
import numpy as np

def compute_var(returns, confidence=0.95):
    """Historical VaR"""
    return np.percentile(returns, (1 - confidence) * 100)

def compute_cvar(returns, confidence=0.95):
    """Conditional VaR (Expected Shortfall)"""
    var = compute_var(returns, confidence)
    return returns[returns <= var].mean()

def sharpe_ratio(returns, risk_free_rate=0.0):
    excess = returns - risk_free_rate / 252
    return np.sqrt(252) * excess.mean() / excess.std()

def max_drawdown(cumulative_returns):
    rolling_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - rolling_max) / rolling_max
    return drawdown.min()
```

### 3. Factor Models

#### Fama-French 3-Factor Model
```
R_i - R_f = alpha + beta_mkt*(R_m - R_f) + beta_smb*SMB + beta_hml*HML + epsilon
```

#### Common Factors
- **Momentum**: 12-1 month return
- **Value**: Book-to-market ratio
- **Quality**: ROE, earnings stability
- **Low Volatility**: Historical realized vol

### 4. Time-Series Forecasting

```python
# ARIMA for returns forecasting
from statsmodels.tsa.arima.model import ARIMA

model = ARIMA(returns, order=(1, 0, 1))
result = model.fit()
forecast = result.forecast(steps=10)

# Use ML for non-linear patterns
from sklearn.ensemble import GradientBoostingRegressor
# Features: lagged returns, volume, macro indicators
```

### 5. Backtesting Framework

```python
def backtest(signals, prices, transaction_cost=0.001):
    positions = signals.shift(1)  # Avoid lookahead
    returns = prices.pct_change()
    strategy_returns = positions * returns - abs(positions.diff()) * transaction_cost
    
    metrics = {
        "total_return": (1 + strategy_returns).prod() - 1,
        "sharpe": sharpe_ratio(strategy_returns),
        "max_drawdown": max_drawdown((1 + strategy_returns).cumprod()),
        "win_rate": (strategy_returns > 0).mean()
    }
    return metrics
```

### 6. Derivatives & Pricing

#### Black-Scholes
```python
from scipy.stats import norm
import numpy as np

def black_scholes(S, K, T, r, sigma, option_type='call'):
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    if option_type == 'call':
        return S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
    else:
        return K*np.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)
```

## Data Sources

| Source | Data Type | Library |
|--------|-----------|---------|
| Yahoo Finance | OHLCV, fundamentals | `yfinance` |
| Alpha Vantage | Real-time, forex | `alpha_vantage` |
| Quandl/NASDAQ | Economic, alternative | `nasdaqdatalink` |
| FRED | Macro indicators | `fredapi` |
| Bloomberg | Professional grade | `blpapi` |

## Libraries

| Library | Purpose |
|---------|---------|
| `pandas` | Data manipulation |
| `numpy` | Numerical computing |
| `scipy` | Statistical functions |
| `cvxpy` | Convex optimization |
| `PyPortfolioOpt` | Portfolio optimization |
| `statsmodels` | Econometrics, ARIMA |
| `quantlib` | Derivatives pricing |
| `zipline-reloaded` | Backtesting |
| `bt` | Flexible backtesting |

## AI-Finance Context

- Always account for **transaction costs** and **slippage** in backtests
- Use **walk-forward validation** (not simple train/test split)
- Report **risk-adjusted** returns, not raw returns
- Flag **overfitting** risk when in-sample >> out-of-sample performance
- Integrate UQ skill for confidence intervals on all predictions

## Verification Checklist

- [ ] No lookahead bias in backtests
- [ ] Transaction costs are modeled
- [ ] Risk metrics (VaR, CVaR, Sharpe, MDD) are reported
- [ ] Walk-forward or out-of-sample validation used
- [ ] Uncertainty bounds on forecasts provided
- [ ] Results are economically interpretable

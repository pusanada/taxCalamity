---
name: rapid-prototyping
description: Quickly scaffold, iterate, and validate proof-of-concept applications, data pipelines, ML experiments, and financial tools using Python notebooks, Streamlit, or minimal FastAPI. Triggers on requests about prototyping, POC, MVP, quick demos, experiments, or fast iteration.
---

# rapid-prototyping

You have the `rapid-prototyping` skill. Use it when the user needs to quickly build and validate ideas before committing to a full implementation.

## Prototyping Philosophy

> "Make it work → Make it right → Make it fast"

1. **Speed over perfection** — Get something running in minutes
2. **Validate assumptions first** — Prove the concept before engineering it
3. **Use high-level abstractions** — Streamlit, notebooks, scripts first
4. **Incremental complexity** — Start minimal, add features iteratively

## Prototyping Stack by Use Case

| Use Case | Best Tool | Time to MVP |
|----------|-----------|------------|
| Data exploration | Jupyter Notebook | 5 min |
| Interactive dashboard | Streamlit | 15 min |
| Quick API endpoint | FastAPI script | 10 min |
| ML experiment | Jupyter + sklearn | 20 min |
| Financial model POC | Pandas + Matplotlib | 15 min |
| Agent prototype | Python script + LLM | 30 min |

## Streamlit Prototype Template

```python
# streamlit_app.py — Full AI-Finance dashboard prototype
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="AI Finance POC",
    page_icon="📈",
    layout="wide"
)

st.title("📈 AI Portfolio Analyzer — POC")
st.caption("Prototype v0.1 — Not for production use")

# Sidebar config
with st.sidebar:
    st.header("Configuration")
    tickers = st.multiselect("Assets", ["AAPL","GOOGL","MSFT","AMZN","NVDA"], default=["AAPL","MSFT"])
    risk_tolerance = st.slider("Risk Tolerance", 0.0, 1.0, 0.5)
    confidence_level = st.slider("Confidence Level", 0.80, 0.99, 0.95)

# Main content
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Expected Return", "18.3%", "+2.1%")
with col2:
    st.metric("Sharpe Ratio", "1.42", "+0.18")
with col3:
    st.metric("Max Drawdown", "-12.1%", "+2.3%")

# Confidence visualization
fig = go.Figure()
x = list(range(252))
y = np.cumsum(np.random.normal(0.0008, 0.015, 252))
ci_upper = y + 0.05
ci_lower = y - 0.05

fig.add_trace(go.Scatter(x=x, y=ci_upper, fill=None, mode='lines',
    line_color='rgba(0,200,135,0.3)', name='95% CI Upper'))
fig.add_trace(go.Scatter(x=x, y=ci_lower, fill='tonexty', mode='lines',
    line_color='rgba(0,200,135,0.3)', name='95% CI Lower',
    fillcolor='rgba(0,200,135,0.1)'))
fig.add_trace(go.Scatter(x=x, y=y, mode='lines',
    line=dict(color='#00C087', width=2), name='Portfolio'))

st.plotly_chart(fig, use_container_width=True)

# AI Recommendation with HITL
st.subheader("🤖 AI Recommendation")
with st.container():
    st.info("**Rebalance recommended**: Increase NVDA by 5%, reduce AAPL by 5%")
    col_a, col_b, col_c = st.columns(3)
    if col_a.button("✅ Approve"):
        st.success("Rebalance approved and queued for execution.")
    if col_b.button("✏️ Modify"):
        st.warning("Open modification dialog...")
    if col_c.button("❌ Reject"):
        reason = st.text_input("Reason for rejection:")

if st.button("Run Analysis"):
    with st.spinner("Running AI analysis..."):
        import time; time.sleep(2)
    st.success("Analysis complete!")
```

## Jupyter Notebook Prototype

```python
# notebook_template.py
# Standard imports for financial prototyping
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import yfinance as yf
from datetime import datetime, timedelta

# ── 1. Data ────────────────────────────────────────────────────────────────
tickers = ['AAPL', 'MSFT', 'GOOGL']
data = yf.download(tickers, start='2023-01-01', end='2026-01-01')['Close']
returns = data.pct_change().dropna()
print(f"Data shape: {data.shape}")
data.tail()

# ── 2. Quick Stats ─────────────────────────────────────────────────────────
stats = returns.describe()
annual_returns = returns.mean() * 252
annual_vol = returns.std() * np.sqrt(252)
sharpe = annual_returns / annual_vol
print("Annualized Sharpe Ratios:")
print(sharpe)

# ── 3. Visualization ───────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
data.plot(ax=axes[0,0], title='Price History')
returns.cumsum().plot(ax=axes[0,1], title='Cumulative Returns')
returns.corr().pipe(sns.heatmap, ax=axes[1,0], annot=True, cmap='RdYlGn')
returns.hist(ax=axes[1,1], bins=50)
plt.tight_layout()
plt.show()

# ── 4. Model / Idea ────────────────────────────────────────────────────────
# YOUR PROTOTYPE CODE HERE

# ── 5. Results ─────────────────────────────────────────────────────────────
# Present findings concisely
```

## Quick ML Experiment Template

```python
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error
import numpy as np

# Feature engineering
def make_features(returns, lags=5):
    df = pd.DataFrame({'target': returns})
    for i in range(1, lags+1):
        df[f'lag_{i}'] = returns.shift(i)
    df['rolling_vol_5'] = returns.rolling(5).std()
    df['rolling_mean_10'] = returns.rolling(10).mean()
    return df.dropna()

# Time-series cross-validation (no lookahead!)
tscv = TimeSeriesSplit(n_splits=5)
scores = []
for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    model = GradientBoostingRegressor(n_estimators=100)
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    scores.append(score)

print(f"CV R² scores: {np.mean(scores):.3f} ± {np.std(scores):.3f}")
```

## Prototype → Production Checklist

| Prototype Stage | Production Requirement |
|----------------|----------------------|
| Hardcoded config | Move to `config.py` / env vars |
| `print()` statements | Proper logging |
| Single script | Modular package structure |
| No auth | JWT authentication |
| No error handling | Comprehensive try/except + HTTP errors |
| Manual data | Automated data pipeline |
| Notebook-based | FastAPI endpoints |
| No tests | Unit + integration tests |
| No UQ | Confidence intervals on outputs |

## Running Prototypes

```bash
# Streamlit
streamlit run streamlit_app.py --server.port 8501

# Jupyter
jupyter notebook --ip=0.0.0.0 --port=8888

# Quick FastAPI
uvicorn prototype_api:app --reload --port 8000
```

## Verification Checklist

- [ ] Prototype validates the core hypothesis quickly
- [ ] Key assumptions are clearly stated
- [ ] Results are visualized for easy interpretation
- [ ] Lookahead bias is avoided even in prototypes
- [ ] Code is commented for future reference
- [ ] A clear "promote to production" checklist exists

# Time Series Analysis

Methods for analyzing data ordered by time, detecting trends, changes, and making forecasts.

## Core Concepts

### Stationarity

A time series is **stationary** if its statistical properties (mean, variance) don't change over time.

**Why it matters**: Most statistical methods assume stationarity. Non-stationary data needs transformation first.

**Visual signs of non-stationarity**:
- Trending up or down
- Changing variance over time
- Seasonal patterns

### Testing for Stationarity

#### ADF Test (Augmented Dickey-Fuller)
- **Null hypothesis**: Series has a unit root (non-stationary)
- **If p-value < 0.05**: Reject null → Series is stationary
- **If p-value > 0.05**: Fail to reject → Series is non-stationary

#### KPSS Test
- **Null hypothesis**: Series is stationary
- **If p-value < 0.05**: Reject null → Series is non-stationary
- **If p-value > 0.05**: Fail to reject → Series is stationary

**Best practice**: Use both tests. If they disagree, series may need differencing.

### Making Series Stationary

1. **Differencing**: Subtract previous value from current
   - First difference: `y'[t] = y[t] - y[t-1]`
   - Removes linear trends

2. **Log transformation**: Stabilizes variance
   - `y'[t] = log(y[t])`
   - Use when variance increases with level

3. **Seasonal differencing**: For seasonal patterns
   - `y'[t] = y[t] - y[t-s]` where s = seasonal period

---

## Trend Decomposition

Break a time series into components:
- **Trend**: Long-term direction
- **Seasonal**: Regular periodic patterns
- **Residual**: Random noise

### STL Decomposition (Seasonal-Trend using Loess)

**Advantages**:
- Handles any seasonality
- Robust to outliers
- Allows trend to change over time

**Output**:
- Trend component: Underlying direction
- Seasonal component: Repeating patterns
- Residual: What's left (should be random noise)

### Additive vs Multiplicative

| Type | Formula | Use When |
|------|---------|----------|
| Additive | Y = Trend + Seasonal + Residual | Seasonal variation is constant |
| Multiplicative | Y = Trend × Seasonal × Residual | Seasonal variation scales with level |

**How to choose**: Plot the data. If seasonal swings grow larger as the level increases, use multiplicative.

---

## Change Point Detection

Identify when significant changes occurred in a time series.

### Methods

#### 1. Sliding Window Comparison
Compare means of adjacent windows:
- Window size: 7-14 days typically
- Calculate `ratio = next_window_mean / prev_window_mean`
- Flag as change point if ratio > threshold (e.g., 2x) or < 1/threshold

**Pros**: Simple, interpretable
**Cons**: Sensitive to window size choice

#### 2. CUSUM (Cumulative Sum)
Tracks cumulative deviations from mean:
- Detects when process mean shifts
- Good for gradual changes

#### 3. Regime Switching Models
Model assumes data comes from different "regimes" with different parameters:
- Markov switching: Probability of being in each regime
- Identifies structural breaks in the data

**Best for**: Detecting when fundamentally different dynamics began

### Practical Algorithm for Growth Detection

```
1. Calculate baseline: mean of first N days (e.g., 30 days)
2. For each subsequent day:
   - Calculate rolling mean (7-day window)
   - If rolling_mean >= baseline × threshold:
     - Mark as potential growth start
     - Verify: check if sustained for M days
3. If sustained: return growth start date
4. Calculate growth_ratio = post_growth_mean / pre_growth_mean
```

**Recommended thresholds**:
- Growth detection: 1.5x to 2x
- Significant growth: 2x+
- Explosive growth: 3x+

---

## Trend Classification

### Categories

| Type | Criteria | Interpretation |
|------|----------|----------------|
| **Rising** | Growth ratio >= 2x, recent | Active growth, high priority |
| **Stable High** | High level, low CV | Consistent demand, check competition |
| **Cooling** | Was high, now declining | Past peak, lower priority |
| **Stable Low** | Low level, low CV | Niche or saturated |
| **Volatile** | High CV, no clear trend | Unpredictable, risky |

### Key Metrics

#### Coefficient of Variation (CV)
```
CV = standard_deviation / mean
```
- CV < 0.3: Stable
- CV 0.3-0.5: Moderate variability
- CV > 0.5: Highly volatile

#### Growth Ratio
```
growth_ratio = recent_period_mean / baseline_period_mean
```

#### Momentum
```
momentum_7d = (last_7d_mean - prev_7d_mean) / prev_7d_mean × 100
```
- Positive: Still growing
- Negative: Slowing/declining

#### Days Since Change
How recently the change started:
- < 7 days: Very recent, high priority
- 7-14 days: Recent, good timing
- 15-30 days: Moderate, check competition
- > 30 days: May be late

---

## Forecasting Methods

### Simple Methods

| Method | Description | Best For |
|--------|-------------|----------|
| Naive | Forecast = last observation | Random walk data |
| Seasonal naive | Forecast = same period last cycle | Strong seasonality |
| Mean | Forecast = historical mean | Stable, no trend |
| Drift | Extrapolate from first to last | Linear trend |

### Exponential Smoothing

Weighted average with more weight to recent observations.

| Type | Trend | Seasonal | Use When |
|------|-------|----------|----------|
| Simple | No | No | Flat data |
| Holt | Yes | No | Trending, no seasonality |
| Holt-Winters | Yes | Yes | Trend and seasonality |

### ARIMA

AutoRegressive Integrated Moving Average: ARIMA(p, d, q)
- **p**: AR order (how many lags)
- **d**: Differencing order (for stationarity)
- **q**: MA order (lagged errors)

**When to use**:
- Need formal model with confidence intervals
- Data has autocorrelation structure
- More data available (50+ observations)

### Choosing a Method

| Data Characteristics | Recommended Method |
|---------------------|-------------------|
| Short series (< 20 points) | Simple methods, exponential smoothing |
| Clear seasonality | Holt-Winters, SARIMA |
| Only trend, no season | Holt, ARIMA(p,1,q) |
| Complex patterns | ARIMA, ensemble methods |

---

## Practical Guidelines

### Minimum Data Requirements

| Method | Minimum Observations |
|--------|---------------------|
| Mean comparison | 7-14 per period |
| Trend detection | 30+ days |
| Seasonal decomposition | 2+ full cycles |
| ARIMA | 50+ observations |

### Common Pitfalls

1. **Ignoring stationarity**: Always check before analysis
2. **Too short baseline**: Use 30+ days for reliable baseline
3. **Confusing noise with signal**: Smooth data or use longer windows
4. **Extrapolating too far**: Forecast accuracy degrades with horizon
5. **Ignoring outliers**: One spike can distort means

### Best Practices

1. **Visualize first**: Plot the data before any analysis
2. **Use appropriate windows**: Match to your decision timeframe
3. **Combine metrics**: Don't rely on single indicator
4. **Update baselines**: Recalculate as more data arrives
5. **Validate**: Check method on historical data before using

# Machine Learning Methods

Core ML methods for segmentation, classification, and pattern discovery in business contexts.

## When to Use ML vs Statistics

| Use Statistics When | Use ML When |
|---------------------|-------------|
| Testing a specific hypothesis | Discovering patterns |
| Understanding relationships | Making predictions |
| Sample size is small | Dataset is large |
| Need to explain "why" | Need to predict "what" |
| Inference is the goal | Accuracy is the goal |
| Assumptions can be checked | Relationships are complex |

### Decision Guide

```
Is your goal to understand WHY something happens?
├─ YES → Use statistical methods (regression, hypothesis tests)
└─ NO → Is your goal to predict WHAT will happen?
    ├─ YES → Use ML (if enough data) or statistical models
    └─ NO → Is your goal to find natural GROUPS in data?
        ├─ YES → Use clustering (unsupervised ML)
        └─ NO → Use exploratory data analysis first
```

---

## Clustering (Unsupervised Learning)

Find natural groups in data when you don't have labels.

### K-Means Clustering

**When to use:**
- Known or estimated number of clusters
- Roughly spherical clusters
- Similar-sized clusters

**Key decisions:**

| Parameter | How to Choose |
|-----------|---------------|
| Number of clusters (K) | Elbow method, silhouette score, business logic |
| Features to include | Domain relevance, avoid highly correlated features |
| Scaling | Always standardize features (mean=0, std=1) |

**Silhouette Score Interpretation:**
- Score > 0.7: Strong structure
- Score > 0.5: Good structure
- Score < 0.25: Weak structure

### Hierarchical Clustering

**When to use:**
- Unknown number of clusters
- Want to see cluster hierarchy
- Smaller datasets (<10,000 points)

| Linkage Method | Best For |
|----------------|----------|
| Ward | Minimize variance, balanced clusters |
| Complete | Maximum distance, compact clusters |
| Average | Balanced approach |

### DBSCAN

**When to use:**
- Clusters have irregular shapes
- Need to identify outliers/noise
- Unknown number of clusters

| Parameter | Tuning Guide |
|-----------|--------------|
| eps | Start with k-distance plot |
| min_samples | Start with 2 × dimensions |

**Advantages:**
- Automatically determines cluster count
- Finds arbitrarily shaped clusters
- Robust to outliers

---

## Classification (Supervised Learning)

Predict categorical outcomes with labeled training data.

### Logistic Regression

**Use when:**
- Binary classification
- Need interpretable results
- Baseline model required
- Small dataset

**Strengths:** Interpretable, fast, works with small data  
**Weaknesses:** Assumes linear decision boundary

### Decision Trees

**Use when:**
- Need easily explainable rules
- Mix of numerical and categorical features
- Non-linear relationships

| Parameter | Effect |
|-----------|--------|
| max_depth | Limits complexity, prevents overfitting |
| min_samples_split | Minimum samples to make a split |
| min_samples_leaf | Minimum samples in leaf nodes |

**Advantages:** Interpretable, no scaling needed  
**Disadvantages:** Prone to overfitting, unstable

### Random Forest

**Use when:**
- Need higher accuracy than single tree
- Can sacrifice some interpretability
- Have enough data (500+ samples)

| Parameter | Typical Value |
|-----------|---------------|
| n_estimators | 100-500 trees |
| max_depth | 10-20 or None |
| max_features | sqrt(n_features) |

---

## Model Evaluation

### Classification Metrics

| Metric | Use When |
|--------|----------|
| Accuracy | Classes are balanced |
| Precision | False positives are costly |
| Recall | False negatives are costly |
| F1 Score | Need balance of precision and recall |
| AUC-ROC | Overall model discrimination |

**Confusion Matrix:**
```
                Predicted
              Pos    Neg
Actual Pos    TP     FN
       Neg    FP     TN

Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

### Cross-Validation
- Never evaluate on training data
- Use k-fold (typically k=5 or 10)
- Report mean and standard deviation

---

## Dimensionality Reduction

### PCA (Principal Component Analysis)

**Use when:**
- Too many features
- Features are correlated
- Need to visualize high-dimensional data
- Preprocessing for other algorithms

**Choosing components:**
- Keep 80-95% of explained variance
- Use scree plot (elbow method)
- Fixed number for visualization (2-3)

---

## Minimum Data Requirements

| Method | Minimum Samples |
|--------|-----------------|
| K-means | 10-20 per cluster |
| Hierarchical | No strict minimum (slow >10K) |
| Logistic regression | 10-20 per predictor |
| Decision tree | 100+ |
| Random forest | 500+ |

## Common Mistakes

1. **Not scaling features**: K-means and PCA are scale-sensitive
2. **Overfitting**: Training >> test accuracy
3. **Ignoring class imbalance**: Use stratified splits
4. **Too many features**: Use feature selection or PCA
5. **No baseline**: Always compare to simple model
6. **Data leakage**: Using test data in training

## Feature Engineering Tips

- **Numeric**: Consider binning, log transform, interactions
- **Categorical**: One-hot encode, target encode for high cardinality
- **Text**: TF-IDF, word counts, embeddings
- **Time**: Extract day of week, month, recency
- **Missing values**: Impute or create indicator variable

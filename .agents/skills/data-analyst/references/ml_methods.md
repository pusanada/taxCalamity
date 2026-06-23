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

**What it does**: Partitions data into K clusters where each point belongs to the cluster with the nearest mean.

**When to use**:
- Known or estimated number of clusters
- Roughly spherical clusters
- Similar-sized clusters

**Key decisions**:

| Parameter | How to Choose |
|-----------|---------------|
| Number of clusters (K) | Elbow method, silhouette score, business logic |
| Features to include | Domain relevance, avoid highly correlated features |
| Scaling | Always standardize features (mean=0, std=1) |

**Elbow method**:
1. Run K-means for K = 1, 2, 3, ... 10
2. Plot inertia (within-cluster sum of squares) vs K
3. Choose K at the "elbow" where improvements slow down

**Silhouette score**:
- Range: -1 to 1
- Higher is better (points are well-matched to own cluster)
- Score > 0.5: Good structure
- Score > 0.7: Strong structure

**Interpreting clusters**:
1. Calculate mean of each feature per cluster
2. Compare to overall mean
3. Name clusters based on distinguishing characteristics

### Hierarchical Clustering

**What it does**: Builds a tree (dendrogram) of clusters from bottom-up or top-down.

**When to use**:
- Unknown number of clusters
- Want to see cluster hierarchy
- Smaller datasets (< 10,000 points)

**Key decisions**:

| Parameter | Options |
|-----------|---------|
| Linkage method | Ward (minimize variance), Complete (max distance), Average |
| Distance metric | Euclidean (default), Manhattan, Cosine |
| Cut level | Visual inspection of dendrogram |

**Choosing where to cut**:
- Look for long "stems" in the dendrogram
- Cut at a height that gives interpretable clusters
- Validate with domain knowledge

### DBSCAN

**What it does**: Finds clusters of arbitrary shape, identifies outliers.

**When to use**:
- Clusters have irregular shapes
- Need to identify outliers/noise
- Unknown number of clusters

**Key parameters**:

| Parameter | Meaning | Tuning |
|-----------|---------|--------|
| eps | Maximum distance between points in same cluster | Start with k-distance plot |
| min_samples | Minimum points to form a dense region | Start with 2 × dimensions |

**Advantages**:
- Automatically determines number of clusters
- Finds arbitrarily shaped clusters
- Robust to outliers

---

## Classification (Supervised Learning)

Predict categorical outcomes when you have labeled training data.

### Logistic Regression (as Classifier)

**When to use**:
- Binary classification
- Need interpretable results
- Understanding feature importance
- Baseline model

**Strengths**: Interpretable coefficients, fast, works with small data
**Weaknesses**: Assumes linear decision boundary

### Decision Trees

**What it does**: Creates rules by splitting data based on feature values.

**When to use**:
- Need easily explainable rules
- Mix of numerical and categorical features
- Non-linear relationships

**Key parameters**:

| Parameter | Effect |
|-----------|--------|
| max_depth | Limits tree complexity (prevents overfitting) |
| min_samples_split | Minimum samples to make a split |
| min_samples_leaf | Minimum samples in leaf nodes |

**Interpreting trees**:
- Follow path from root to leaf
- Each split is a rule
- Can extract as business rules

**Advantages**:
- Highly interpretable
- No feature scaling needed
- Handles non-linear relationships

**Disadvantages**:
- Prone to overfitting
- Unstable (small data changes → different tree)

### Random Forest

**What it does**: Ensemble of decision trees, each trained on random subset of data and features.

**When to use**:
- Need higher accuracy than single tree
- Can sacrifice some interpretability
- Have enough data

**Key parameters**:

| Parameter | Typical Value |
|-----------|---------------|
| n_estimators | 100-500 trees |
| max_depth | 10-20 or None |
| max_features | sqrt(n_features) |

**Feature importance**:
- Random forest provides feature importance scores
- Based on how much each feature improves predictions
- Useful for feature selection

### Model Evaluation

| Metric | Use When |
|--------|----------|
| Accuracy | Classes are balanced |
| Precision | False positives are costly |
| Recall | False negatives are costly |
| F1 Score | Need balance of precision and recall |
| AUC-ROC | Overall model discrimination |

**Confusion Matrix**:
```
                Predicted
              Pos    Neg
Actual Pos    TP     FN
       Neg    FP     TN

Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

**Cross-validation**:
- Never evaluate on training data
- Use k-fold cross-validation (typically k=5 or 10)
- Report mean and standard deviation of metrics

---

## Dimensionality Reduction

Reduce number of features while preserving important information.

### PCA (Principal Component Analysis)

**What it does**: Finds new axes (principal components) that capture maximum variance.

**When to use**:
- Too many features
- Features are correlated
- Need to visualize high-dimensional data
- Preprocessing for other algorithms

**Key concepts**:

| Concept | Meaning |
|---------|---------|
| Principal components | New features, linear combinations of originals |
| Explained variance | How much variance each component captures |
| Loadings | How original features contribute to each component |

**Choosing number of components**:
- Keep components that explain 80-95% of variance
- Or use scree plot (elbow method)
- Or set a fixed number for visualization (2-3)

**Interpreting components**:
1. Look at loadings for each component
2. High loadings indicate important original features
3. Name components based on their composition

---

## Practical Guidelines

### Workflow for Clustering

```
1. Define the business question
2. Select relevant features
3. Standardize features (z-score)
4. Try multiple K values (2-10)
5. Evaluate with silhouette score and business logic
6. Profile clusters (means, distributions)
7. Validate with holdout data
8. Name clusters descriptively
```

### Workflow for Classification

```
1. Define target variable clearly
2. Split data (train/test, e.g., 80/20)
3. Explore features, handle missing values
4. Start with simple model (logistic regression)
5. Evaluate with appropriate metrics
6. Try more complex models if needed
7. Compare on held-out test set
8. Document feature importance
```

### Common Mistakes

1. **Not scaling features**: K-means and PCA are sensitive to scale
2. **Overfitting**: Training accuracy >> test accuracy
3. **Ignoring class imbalance**: Use stratified splits, adjusted metrics
4. **Too many features**: Use feature selection or PCA first
5. **No baseline**: Always compare to simple model
6. **Data leakage**: Using test data information in training

### Minimum Data Requirements

| Method | Minimum Samples | Notes |
|--------|-----------------|-------|
| K-means | 10-20 per cluster | More for high dimensions |
| Hierarchical | No strict minimum | Slow for >10,000 samples |
| Logistic regression | 10-20 per predictor | More for rare events |
| Decision tree | 100+ | Prone to overfit with less |
| Random forest | 500+ | Needs enough for sampling |

### Feature Engineering Tips

1. **Numeric features**: Consider binning, log transform, interactions
2. **Categorical features**: One-hot encode, target encode for high cardinality
3. **Text features**: TF-IDF, word counts, embeddings
4. **Time features**: Extract day of week, month, recency
5. **Missing values**: Impute or create indicator variable

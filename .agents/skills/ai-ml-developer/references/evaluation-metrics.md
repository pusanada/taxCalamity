# LLM Evaluation Metrics

Comprehensive evaluation strategies for LLM applications.

## Evaluation Types Overview

| Type | Speed | Scale | Best For |
|:-----|:------|:------|:---------|
| Automated Metrics | Fast | High | Regression testing, CI/CD |
| LLM-as-Judge | Medium | Medium | Quality assessment |
| Human Evaluation | Slow | Low | Ground truth, final validation |

---

## Automated Metrics

### Text Generation

| Metric | Description | Use Case |
|:-------|:------------|:---------|
| **BLEU** | N-gram overlap | Translation |
| **ROUGE** | Recall-oriented overlap | Summarization |
| **METEOR** | Semantic similarity | General text |
| **BERTScore** | Embedding-based similarity | Semantic matching |
| **Perplexity** | Model confidence | Fluency |

### RAG-Specific

| Metric | Description |
|:-------|:------------|
| **MRR** | Mean Reciprocal Rank |
| **NDCG@K** | Normalized Discounted Cumulative Gain |
| **Precision@K** | Relevant documents in top K |
| **Recall@K** | Coverage of relevant documents |
| **Groundedness** | Answer supported by context |

### Implementation

```python
from bert_score import score

def calculate_bertscore(references, hypotheses):
    P, R, F1 = score(hypotheses, references, lang='en')
    return {'precision': P.mean(), 'recall': R.mean(), 'f1': F1.mean()}

def calculate_groundedness(response, context):
    """Check if response is grounded in context using NLI."""
    from transformers import pipeline
    nli = pipeline("text-classification", model="microsoft/deberta-large-mnli")
    result = nli(f"{context} [SEP] {response}")[0]
    return result['score'] if result['label'] == 'ENTAILMENT' else 0.0
```

---

## LLM-as-Judge

### Single Output Evaluation

```python
def llm_judge(response, question):
    prompt = f"""Rate the response on a scale of 1-10:
    
Question: {question}
Response: {response}

Rate on:
1. Accuracy (factually correct)
2. Helpfulness (answers the question)
3. Clarity (well-written)

Output JSON: {{"accuracy": <1-10>, "helpfulness": <1-10>, "clarity": <1-10>, "reasoning": "<brief>"}}"""
    
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
```

### Pairwise Comparison

```python
def compare_responses(question, response_a, response_b):
    prompt = f"""Compare these responses:
    
Question: {question}
Response A: {response_a}
Response B: {response_b}

Which is better? Consider accuracy, helpfulness, clarity.
Output JSON: {{"winner": "A" or "B" or "tie", "reasoning": "<explanation>"}}"""
    
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
```

---

## Human Evaluation

### Annotation Dimensions

| Dimension | Scale | Description |
|:----------|:------|:------------|
| Accuracy | 1-5 | Factually correct |
| Relevance | 1-5 | Answers the question |
| Coherence | 1-5 | Logically consistent |
| Fluency | 1-5 | Natural language |
| Safety | Binary | No harmful content |

### Inter-Rater Agreement

```python
from sklearn.metrics import cohen_kappa_score

def calculate_agreement(rater1, rater2):
    kappa = cohen_kappa_score(rater1, rater2)
    # Interpretation:
    # < 0.2: Slight
    # 0.2-0.4: Fair
    # 0.4-0.6: Moderate
    # 0.6-0.8: Substantial
    # > 0.8: Almost perfect
    return kappa
```

---

## A/B Testing

### Statistical Framework

```python
from scipy import stats
import numpy as np

class ABTest:
    def __init__(self):
        self.a_scores = []
        self.b_scores = []
    
    def analyze(self, alpha=0.05):
        t_stat, p_value = stats.ttest_ind(self.a_scores, self.b_scores)
        
        # Effect size (Cohen's d)
        pooled_std = np.sqrt((np.std(self.a_scores)**2 + np.std(self.b_scores)**2) / 2)
        cohens_d = (np.mean(self.b_scores) - np.mean(self.a_scores)) / pooled_std
        
        # Effect size interpretation:
        # < 0.2: negligible
        # 0.2-0.5: small
        # 0.5-0.8: medium
        # > 0.8: large
        
        return {
            'p_value': p_value,
            'significant': p_value < alpha,
            'effect_size': cohens_d,
            'winner': 'B' if np.mean(self.b_scores) > np.mean(self.a_scores) else 'A'
        }
```

---

## Regression Detection

```python
class RegressionDetector:
    def __init__(self, baseline, threshold=0.05):
        self.baseline = baseline
        self.threshold = threshold
    
    def check(self, new_results):
        regressions = []
        for metric, baseline_score in self.baseline.items():
            new_score = new_results.get(metric)
            if new_score and (new_score - baseline_score) / baseline_score < -self.threshold:
                regressions.append({
                    'metric': metric,
                    'baseline': baseline_score,
                    'current': new_score,
                    'change': (new_score - baseline_score) / baseline_score
                })
        return {'has_regression': len(regressions) > 0, 'details': regressions}
```

---

## Best Practices

1. **Multiple Metrics**: Use diverse metrics for comprehensive view
2. **Representative Data**: Test on real-world, diverse examples
3. **Baselines**: Always compare against baseline performance
4. **Statistical Rigor**: Use proper tests for comparisons
5. **Continuous Evaluation**: Integrate into CI/CD pipeline
6. **Human Validation**: Combine automated with human judgment
7. **Error Analysis**: Investigate failures to understand weaknesses

## Common Pitfalls

- **Single Metric Focus**: Optimizing one at expense of others
- **Small Sample Size**: Drawing conclusions from too few examples
- **Data Contamination**: Testing on training data
- **Ignoring Variance**: Not accounting for statistical uncertainty
- **Metric Mismatch**: Using metrics not aligned with business goals

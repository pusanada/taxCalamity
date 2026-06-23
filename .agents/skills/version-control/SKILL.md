---
name: version-control
description: Apply Git best practices for AI-Finance projects including branching strategies, commit conventions, model versioning, data versioning with DVC, code review workflows, and CI/CD integration. Triggers on requests about git, version control, branching, commits, releases, DVC, or model registry.
---

# version-control

You have the `version-control` skill. Use it when the user needs guidance on Git workflows, model versioning, data versioning, or release management.

## Git Branching Strategy

### GitFlow for AI-Finance
```
main          ─────●─────────────────●──────────── (production releases)
                   │                 │
release/v2.1  ─────●──●──●──────────●             (release candidates)
                         │
develop       ──────────────●──●──●──●────────── (integration branch)
                            │  │  │
feature/      ──────────────●  │  │               (new features)
hotfix/                        │  │               (urgent fixes)
experiment/                       │               (ML experiments)
```

### Branch Naming Conventions
```
feature/quant-factor-model
feature/aml-transaction-monitoring
bugfix/sharpe-calculation-error
hotfix/prod-risk-limit-breach
experiment/gbt-return-forecast
release/v2.1.0
chore/update-dependencies
docs/api-documentation
```

## Commit Message Convention (Conventional Commits)

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

### Types
| Type | Use Case |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `perf` | Performance improvement |
| `refactor` | Code restructuring |
| `model` | ML model update (custom) |
| `data` | Data pipeline change (custom) |
| `docs` | Documentation |
| `test` | Tests only |
| `chore` | Build, dependencies |
| `compliance` | Regulatory/compliance change (custom) |

### Examples
```bash
git commit -m "feat(portfolio): add Black-Litterman optimizer"
git commit -m "model(returns): upgrade GBT to v2.3 — Sharpe +0.15"
git commit -m "fix(risk): correct VaR calculation annualization"
git commit -m "compliance(aml): add FinCEN CTR threshold validation"
git commit -m "perf(api): cache factor loadings, reduces latency 40%"
```

## Model Versioning

### MLflow Tracking
```python
import mlflow

with mlflow.start_run(run_name="portfolio_optimizer_v2.1"):
    # Log parameters
    mlflow.log_params({
        "model_type": "GradientBoosting",
        "n_estimators": 200,
        "learning_rate": 0.05,
        "training_period": "2020-2025"
    })
    
    # Log metrics
    mlflow.log_metrics({
        "sharpe_ratio": 1.42,
        "max_drawdown": -0.121,
        "annual_return": 0.217,
        "var_95": -0.018
    })
    
    # Log model artifact
    mlflow.sklearn.log_model(model, "model", registered_model_name="PortfolioOptimizer")
    
    # Log compliance metadata
    mlflow.set_tags({
        "regulatory_validated": "true",
        "compliance_officer": "jane.smith",
        "approved_for_production": "true"
    })
```

### Model Registry Workflow
```
Experiment → Staging → Validated → Production → Archived
```
- **Experiment**: Active development, not production-ready
- **Staging**: Passed backtests, under review
- **Validated**: Compliance sign-off, shadow testing complete
- **Production**: Live in production
- **Archived**: Retired model, kept for audit

## Data Versioning with DVC

```bash
# Initialize DVC
dvc init
git add .dvc .dvcignore
git commit -m "chore: initialize DVC"

# Track a dataset
dvc add data/market_data.parquet
git add data/market_data.parquet.dvc .gitignore
git commit -m "data: add market data v1.0 (2020-2026)"

# Remote storage
dvc remote add -d s3_remote s3://ai-finance-data/dvc
dvc push

# Reproduce pipeline
dvc repro  # Runs pipeline.yaml stages

# Switch to data version
git checkout v1.0
dvc checkout
```

### DVC Pipeline (pipeline.yaml)
```yaml
stages:
  fetch_data:
    cmd: python src/data/fetch.py
    deps: [src/data/fetch.py]
    outs: [data/raw/]
    
  preprocess:
    cmd: python src/data/preprocess.py
    deps: [src/data/preprocess.py, data/raw/]
    outs: [data/processed/]
    
  train:
    cmd: python src/models/train.py
    deps: [src/models/train.py, data/processed/]
    outs: [models/]
    metrics: [metrics.json]
    
  evaluate:
    cmd: python src/models/evaluate.py
    deps: [src/models/evaluate.py, models/]
    metrics: [evaluation.json]
```

## CI/CD Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/ai-finance.yml
name: AI-Finance CI/CD

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Tests
        run: pytest tests/ -v --cov=src --cov-report=xml
      
      - name: Backtest Validation
        run: python scripts/validate_backtest.py
        
      - name: Compliance Check
        run: python scripts/check_compliance.py
        
      - name: Model Performance Gate
        run: |
          python scripts/check_model_metrics.py \
            --min-sharpe 1.0 \
            --max-drawdown 0.20

  deploy_staging:
    needs: test
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Staging
        run: ./scripts/deploy.sh staging
```

## .gitignore for AI-Finance

```gitignore
# Python
__pycache__/
*.pyc
.venv/
.env
.env.*

# Data (use DVC instead)
data/raw/
data/processed/
*.parquet
*.csv
*.h5

# Models (use MLflow/DVC instead)
models/
*.pkl
*.joblib
*.pt

# Jupyter
.ipynb_checkpoints/
*.ipynb  # Optional: track or gitignore

# Secrets
*.key
secrets/
credentials/

# OS
.DS_Store
Thumbs.db
```

## Git Hooks (pre-commit)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks: [{id: black}]
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks: [{id: flake8}]
  - repo: local
    hooks:
      - id: no-secrets
        name: Check for secrets
        entry: python scripts/check_secrets.py
        language: python
      - id: compliance-check
        name: Regulatory compliance check
        entry: python scripts/check_compliance.py --quick
        language: python
```

## Verification Checklist

- [ ] Branch naming follows convention
- [ ] Commit messages use Conventional Commits format
- [ ] Models are versioned in MLflow registry
- [ ] Datasets are tracked with DVC
- [ ] .gitignore excludes data/models/secrets
- [ ] CI pipeline runs tests and compliance checks
- [ ] Pre-commit hooks are set up
- [ ] Release tags follow semver (v2.1.0)

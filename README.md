# Rakuten MLOps Pipeline

Pipeline MLOps complet pour la classification de produits Rakuten.
Certification DataScientest — September 2025.

## Architecture

```
CSV → PostgreSQL → Airflow → Auto-Train → MLflow → Promotion (F1>0.75?) → FastAPI → Drift Detection → Alerte
```

**10 containers Docker** : PostgreSQL, MinIO, MLflow, FastAPI, Airflow (x3), Prometheus, Grafana + Streamlit (local).

## Quick Start

```bash
make demo            # Setup + start + init DB (40%)
make run-streamlit   # Lancer l'interface Streamlit
```

**URLs** : MLflow http://localhost:5000 · Airflow http://localhost:8080 · Grafana http://localhost:3000 · API http://localhost:8000/docs

## Pipelines automatisés (Airflow)

| DAG | Fréquence | Actions |
|-----|-----------|---------|
| `weekly_ml_pipeline` | Lundi 2h | Load +3% → Train → Promote si meilleur |
| `daily_drift_check` | Tous les jours 1h | Analyse drift (PSI, KS, Chi²) → Alerte si seuil dépassé |

## Commandes principales

```bash
# Infrastructure
make start / stop / restart / ps / check-health

# Données
make init-db / load-data / status / generate-dataset

# Modèles
make train-model / trigger-auto-train / trigger-pipeline

# Monitoring
make check-drift / view-drift-reports / view-alerts / clear-alerts

# Tests
make test / test-pipeline / test-monitoring
```

## Seuils de drift

| Sévérité | Score | Action |
|----------|-------|--------|
| OK | < 0.1 | Aucune |
| WARNING | 0.1 – 0.2 | Surveiller |
| ALERT | 0.2 – 0.3 | Investiguer |
| CRITICAL | > 0.3 | Retrain / rollback |

Actions humaines disponibles via Streamlit ou API : `POST /api/trigger-retrain`, `POST /api/rollback-model`.

## Stack technique

- **Données** : PostgreSQL + audit trail, chargement incrémental 40%→100%
- **Training** : TF-IDF + Logistic Regression, RandomOverSampling
- **Tracking** : MLflow (expériences, registre, artifacts sur MinIO)
- **Serving** : FastAPI + Prometheus metrics
- **Orchestration** : Apache Airflow
- **Monitoring** : PSI, KS, Chi-Square sur logs d'inférence
- **Visualisation** : Grafana dashboards, Streamlit UI

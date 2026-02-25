# Rakuten MLOps Pipeline

Pipeline MLOps de classification de produits (DataScientest, 2025).

## Pipeline (résumé)

`CSV -> PostgreSQL -> Airflow -> Training -> MLflow -> Promotion -> FastAPI -> Drift -> Alerte/Action`

- **Hebdo (`weekly_ml_pipeline`)** : charge `+3%` de données, entraîne `TF-IDF + Logistic Regression` (avec rééquilibrage), log dans MLflow.
- **Promotion auto** : un modèle passe en `Production` si `F1 >= 0.75` **et** meilleur que le modèle actuel.
- **Quotidien (`daily_drift_check`)** : compare fenêtre courante (7 jours) vs référence (30 jours) avec `PSI`, `KS`, `Chi²`.
- **Action humaine** : retrain/rollback via Streamlit ou API (`/api/trigger-retrain`, `/api/rollback-model`).

## Démarrage rapide

```bash
make demo            # Démarre l'infra + initialise la DB (40%)
make run-streamlit   # Lance l'interface Streamlit
```

## Services (URLs)

- Airflow: `http://localhost:8080`
- MLflow: `http://localhost:5000`
- FastAPI docs: `http://localhost:8000/docs`
- Grafana: `http://localhost:3000`

## Docker (services)

- `postgres` : stockage données produits + labels + tables de suivi (loads, drift, logs).
- `minio` (+ `minio-init`) : stockage S3 des artifacts MLflow.
- `mlflow` : tracking des runs, métriques, registre de modèles.
- `api` (FastAPI) : service de prédiction en production + endpoints de contrôle.
- `airflow-webserver`, `airflow-scheduler`, `airflow-init` : orchestration des DAGs.
- `prometheus` : scraping des métriques API (`/metrics`) toutes les 15s.
- `grafana` : dashboards ops (latence, débit, classes prédites, signaux de drift).
- `streamlit` (local) : interface de pilotage et visualisation.

## Airflow

- `weekly_ml_pipeline` (hebdo) : `load +3% -> train -> evaluate -> promote if better`.
- `daily_drift_check` (quotidien) : calcule `PSI/KS/Chi²`, génère rapport et niveau de sévérité.

## MLflow

- Trace chaque entraînement (params, métriques, artifacts, run id, git sha).
- Registre `rakuten_classifier` avec stages (`Production`, `Staging`, `Archived`, `None`).
- Promotion automatique si seuil qualité atteint et gain vs modèle en production.

## FastAPI

- `POST /predict` : inférence sur le modèle `Production`.
- Chaque prédiction est loggée pour le monitoring et la détection de drift.
- Endpoints de contrôle : `/api/trigger-retrain`, `/api/rollback-model`.

## Prometheus + Grafana

- Prometheus collecte les métriques de service (latence, débit, erreurs, distribution).
- Grafana expose la vue temps réel opérationnelle.
- Le drift statistique batch (PSI/KS/Chi²) est calculé côté pipeline et stocké en base.

## Make (commandes clés)

```bash
# Infra
make start | stop | restart | ps | check-health | logs | demo

# Data
make init-db | load-data | status | generate-dataset

# Training / pipeline
make train-model | train-model-promote | trigger-auto-train | trigger-pipeline

# Monitoring
make check-drift | trigger-drift-check | view-drift-reports | view-alerts | clear-alerts

# Tests / UI
make test | test-pipeline | test-monitoring | test-api | run-streamlit
```

## Stack

PostgreSQL, MinIO, MLflow, FastAPI, Airflow, Prometheus, Grafana, Streamlit.

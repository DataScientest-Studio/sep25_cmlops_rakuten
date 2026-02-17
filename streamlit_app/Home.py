"""
Rakuten MLOps Pipeline - Home & Presentation

Welcome page with horizontal pipeline diagram.
"""
import streamlit as st
from pathlib import Path
import sys
import graphviz
import requests

# Load environment variables
sys.path.insert(0, str(Path(__file__).parent))
from utils.env_config import load_env_vars
load_env_vars()

# Page configuration
st.set_page_config(
    page_title="Rakuten MLOps - Pipeline",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title
st.markdown(
    '<h1 style="text-align:center;">Rakuten MLOps Pipeline</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="text-align:center;color:#666;">Classification automatisée de produits — Certification MLOps DataScientest</p>',
    unsafe_allow_html=True,
)

st.markdown("")

# ── Horizontal pipeline diagram ──────────────────────────────────────────────

diagram = graphviz.Digraph()
diagram.attr(rankdir="LR", size="14,3", nodesep="0.6", ranksep="0.8")
diagram.attr(
    "node",
    shape="box",
    style="filled,rounded",
    fontname="Arial",
    fontsize="11",
    margin="0.2,0.1",
)
diagram.attr("edge", fontname="Arial", fontsize="9")

# Nodes — left to right
diagram.node("csv",       "CSV\nData",              fillcolor="#E8F4F8", color="#2E86AB")
diagram.node("postgres",  "PostgreSQL\n+ Audit",     fillcolor="#B8E6F0", color="#2E86AB")
diagram.node("airflow",   "Airflow\nScheduler",      fillcolor="#FFF3CD", color="#F39C12")
diagram.node("train",     "Auto\nTraining",          fillcolor="#FFE5B4", color="#FF9800")
diagram.node("mlflow",    "MLflow\nRegistry",        fillcolor="#FFC266", color="#FF9800")
diagram.node("promote",   "Promotion\nF1 > 0.75 ?",  fillcolor="#C8E6C9", color="#4CAF50", shape="diamond")
diagram.node("api",       "FastAPI\nServing",        fillcolor="#A5D6A7", color="#4CAF50")
diagram.node("monitor",   "Drift\nDetection",        fillcolor="#F8BBD0", color="#E91E63")
diagram.node("alert",     "Alerte\n& Action",        fillcolor="#F06292", color="#C2185B")

# Edges
diagram.edge("csv",      "postgres",  label="+3% / sem.")
diagram.edge("postgres", "airflow",   label="trigger")
diagram.edge("airflow",  "train",     label="weekly")
diagram.edge("train",    "mlflow",    label="log")
diagram.edge("mlflow",   "promote",   label="compare")
diagram.edge("promote",  "api",       label="oui")
diagram.edge("promote",  "mlflow",    label="non", style="dashed")
diagram.edge("api",      "monitor",   label="inferences")
diagram.edge("monitor",  "alert",     label="drift > seuil")
diagram.edge("alert",    "airflow",   label="retrain", style="dashed")

st.graphviz_chart(diagram, use_container_width=True)

# ── Project summary ──────────────────────────────────────────────────────────

st.markdown("""
Ce projet met en place un **pipeline MLOps complet** pour la classification de produits Rakuten.
Chaque semaine, **Airflow** charge automatiquement 3 % de données supplémentaires dans PostgreSQL,
entraîne un modèle TF-IDF + Logistic Regression, et le promeut en production
si son F1-score dépasse 0.75 et surpasse le modèle actuel.
En parallèle, un **check quotidien** analyse le drift des prédictions (PSI, KS, Chi-Square)
et déclenche une alerte si les distributions dérivent significativement,
permettant une **intervention humaine** (ré-entraînement, rollback) via l'interface Streamlit.
""")

# ── Pipeline action + Airflow link ───────────────────────────────────────────

st.markdown("---")

col_action, col_airflow, _ = st.columns([1, 1, 2])

with col_action:
    if st.button("🚀 Lancer le pipeline complet", type="primary", use_container_width=True):
        with st.spinner("Déclenchement du DAG weekly_ml_pipeline..."):
            try:
                resp = requests.post(
                    "http://localhost:8080/api/v1/dags/weekly_ml_pipeline/dagRuns",
                    json={"conf": {}},
                    auth=("admin", "admin"),
                    timeout=10,
                )
                if resp.status_code in (200, 201):
                    st.success("Pipeline déclenché avec succès. Suivre dans Airflow.")
                else:
                    st.error(f"Erreur Airflow : {resp.status_code} — {resp.text[:200]}")
            except Exception as e:
                st.error(f"Impossible de contacter Airflow : {e}")

with col_airflow:
    st.link_button("Ouvrir Airflow UI", "http://localhost:8080", use_container_width=True)

# ── Commandes Make ───────────────────────────────────────────────────────────

st.markdown("---")
st.header("Commandes Make disponibles")

st.markdown(
    "Toutes les opérations du pipeline sont accessibles via `make <commande>` depuis la racine du projet."
)

col_infra, col_data, col_ml = st.columns(3)

with col_infra:
    st.markdown("""
**Infrastructure**
| Commande | Description |
|----------|-------------|
| `make start` | Démarrer tous les services |
| `make stop` | Arrêter tous les services |
| `make restart` | Redémarrer |
| `make ps` | Voir les containers |
| `make check-health` | Vérifier la santé |
| `make logs` | Voir tous les logs |
| `make demo` | Setup complet (start + init) |
    """)

with col_data:
    st.markdown("""
**Données & Base**
| Commande | Description |
|----------|-------------|
| `make init-db` | Initialiser la base (40 %) |
| `make load-data` | Charger +3 % de données |
| `make status` | État du chargement |
| `make generate-dataset` | Générer dataset équilibré |
| `make shell-postgres` | Console PostgreSQL |
| `make backup-db` | Sauvegarder la base |
    """)

with col_ml:
    st.markdown("""
**Entraînement & Modèles**
| Commande | Description |
|----------|-------------|
| `make train-model` | Entraîner un modèle |
| `make train-model-promote` | Entraîner + auto-promotion |
| `make trigger-auto-train` | Forcer un auto-training |
| `make trigger-auto-promote` | Forcer l'évaluation de promotion |
| `make trigger-pipeline` | Lancer le pipeline complet |
    """)

col_monitor, col_test, _ = st.columns(3)

with col_monitor:
    st.markdown("""
**Monitoring & Alertes**
| Commande | Description |
|----------|-------------|
| `make check-drift` | Lancer une analyse de drift |
| `make trigger-drift-check` | Déclencher le DAG drift |
| `make view-drift-reports` | Voir les rapports de drift |
| `make view-alerts` | Voir les alertes actives |
| `make clear-alerts` | Acquitter toutes les alertes |
    """)

with col_test:
    st.markdown("""
**Tests & Dev**
| Commande | Description |
|----------|-------------|
| `make test` | Lancer tous les tests |
| `make test-pipeline` | Tests pipeline |
| `make test-monitoring` | Tests monitoring |
| `make test-api` | Tester les endpoints API |
| `make run-streamlit` | Lancer Streamlit |
    """)

# ── Docker Compose ───────────────────────────────────────────────────────────

st.markdown("---")
st.header("Services Docker")

st.markdown(
    "L'ensemble du pipeline tourne dans **10 containers** orchestrés par `docker-compose.yml`."
)

col_d1, col_d2, col_d3 = st.columns(3)

with col_d1:
    st.markdown("""
**Données & Stockage**
| Container | Rôle |
|-----------|------|
| `postgres` | Base de données + audit trail |
| `minio` | Stockage S3 des artifacts MLflow |
| `minio-init` | Init : crée le bucket au démarrage |
    """)

with col_d2:
    st.markdown("""
**ML & Serving**
| Container | Rôle |
|-----------|------|
| `mlflow` | Tracking des expériences + registre modèles |
| `api` (FastAPI) | Sert le modèle Production + routes de contrôle |
| `airflow-scheduler` | Exécute les DAGs (weekly + daily) |
| `airflow-webserver` | Interface web Airflow (port 8080) |
| `airflow-init` | Init : crée la DB Airflow + user admin |
    """)

with col_d3:
    st.markdown("""
**Monitoring**
| Container | Rôle |
|-----------|------|
| `prometheus` | Collecte les métriques de l'API |
| `grafana` | Dashboards (métriques + drift) |

**Local (hors Docker)**
| Service | Rôle |
|---------|------|
| `streamlit` | Interface de présentation + actions |
    """)

# Footer
st.markdown("---")
st.caption("DataScientest MLOps Certification — September 2025")

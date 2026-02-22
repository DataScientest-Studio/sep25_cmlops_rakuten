"""
Monitoring du modèle

Surveillance du modèle en production : scores de drift (batch)
et lien vers le dashboard opérationnel Grafana (temps réel).
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import psycopg2

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
streamlit_app_root = Path(__file__).parent.parent
sys.path.insert(0, str(streamlit_app_root))

from utils.env_config import get_db_config

st.set_page_config(
    page_title="Monitoring - Rakuten MLOps",
    page_icon="📈",
    layout="wide",
)

DB_CONFIG = get_db_config()

# ─────────────────────────────────────────────────────────────────────────────
st.title("Monitoring du modèle")
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    "Le monitoring repose sur deux axes complémentaires : "
    "le **dashboard Grafana** surveille les métriques opérationnelles en "
    "temps réel (latence, débit, distribution des classes), tandis que cette "
    "page présente l'**analyse de drift** calculée périodiquement à partir "
    "des logs d'inférence."
)

st.markdown("---")

# ── Derniers rapports de drift ────────────────────────────────────────────────

SEVERITY_STYLE = {
    "OK": ("🟢", "success"),
    "WARNING": ("🟡", "warning"),
    "ALERT": ("🟠", "warning"),
    "CRITICAL": ("🔴", "error"),
}


@st.cache_data(ttl=30)
def get_latest_drift_reports(limit=3):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        df = pd.read_sql_query(
            """
            SELECT report_date, status, severity,
                   data_drift_score, prediction_drift_score,
                   performance_drift_score, overall_drift_score,
                   drift_detected, reference_samples, current_samples
            FROM drift_reports
            WHERE status = 'completed'
            ORDER BY report_date DESC
            LIMIT %s
            """,
            conn,
            params=(limit,),
        )
        conn.close()
        return df
    except Exception as e:
        st.error(f"Connexion impossible : {e}")
        return None


st.header("Derniers rapports de drift")

drift_df = get_latest_drift_reports(3)

if drift_df is not None and len(drift_df) > 0:
    cols = st.columns(len(drift_df))
    for col, (_, row) in zip(cols, drift_df.iterrows()):
        icon, _ = SEVERITY_STYLE.get(row["severity"], ("⚪", "info"))
        report_date = pd.to_datetime(row["report_date"]).strftime("%d/%m/%Y %H:%M")

        with col:
            st.subheader(f"{icon} {row['severity']}")
            st.caption(report_date)
            st.metric("Score global", f"{row['overall_drift_score']:.4f}")
            st.markdown(
                f"| Métrique | Score |\n"
                f"|----------|-------|\n"
                f"| Data drift (PSI) | `{row['data_drift_score']:.4f}` |\n"
                f"| Prediction drift (PSI) | `{row['prediction_drift_score']:.4f}` |\n"
                f"| Confidence drift | `{row['performance_drift_score']:.4f}` |\n"
            )
            st.caption(
                f"{row['reference_samples']} réf. / {row['current_samples']} courant"
            )
else:
    st.info(
        "Aucun rapport de drift disponible. "
        "Lancez `make check-drift` pour en générer."
    )

st.markdown("---")

# ── Stratégie de détection ────────────────────────────────────────────────────

st.header("Stratégie de détection du drift")

st.markdown("""
Le drift est évalué en comparant les prédictions récentes à une fenêtre
de référence à l'aide de trois tests statistiques :
""")

col_psi, col_ks, col_chi = st.columns(3)

with col_psi:
    st.subheader("PSI")
    st.markdown(
        "**Population Stability Index**\n\n"
        "Mesure la stabilité de la distribution des classes prédites "
        "et de la longueur des textes entre la période de référence "
        "et la période courante."
    )

with col_ks:
    st.subheader("KS")
    st.markdown(
        "**Test de Kolmogorov-Smirnov**\n\n"
        "Compare les distributions cumulées des scores de confiance. "
        "Un écart significatif signale un changement dans la certitude "
        "du modèle."
    )

with col_chi:
    st.subheader("Chi²")
    st.markdown(
        "**Test du Chi-carré**\n\n"
        "Évalue si la répartition des catégories prédites a changé "
        "de manière statistiquement significative."
    )

st.markdown("")

st.subheader("Seuils de sévérité")

st.markdown("""
Le score global de drift (moyenne des PSI) détermine le niveau d'alerte :

| Niveau | Score | Action |
|--------|-------|--------|
| 🟢 OK | < 0.1 | Aucune action requise |
| 🟡 WARNING | 0.1 – 0.2 | À surveiller |
| 🟠 ALERT | 0.2 – 0.3 | Investigation recommandée |
| 🔴 CRITICAL | > 0.3 | Ré-entraînement recommandé |
""")

st.markdown("---")

# ── Orchestration ─────────────────────────────────────────────────────────────

st.header("Orchestration")

st.markdown("""
La vérification du drift est automatisée via un **DAG Airflow**
(`daily_drift_check`) exécuté quotidiennement :

1. Collecte les inférences des 7 derniers jours (fenêtre courante).
2. Les compare à une fenêtre de référence de 30 jours.
3. Calcule les métriques PSI, KS et Chi² puis détermine la sévérité.
4. Sauvegarde le rapport en base de données (affiché ci-dessus).
""")

st.markdown("---")

# ── Dashboard Grafana ─────────────────────────────────────────────────────────

st.header("Monitoring temps réel (Grafana)")

st.markdown("""
Le dashboard Grafana **Rakuten - Production** complète cette page en
offrant une vue temps réel sur :

- **Performance API** : latence (P50 / P95 / P99) et débit de prédictions.
- **Signaux de drift** : évolution de la distribution des classes prédites
  et de la longueur moyenne des textes en entrée.

Ces métriques sont collectées par **Prometheus** toutes les 15 secondes
depuis l'endpoint `/metrics` de l'API.
""")

st.link_button("Ouvrir Grafana", "http://localhost:3000")

"""
Monitoring & Alertes

Explanation of drift detection rules, active alerts with actions,
drift history, and action audit trail.
"""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Load environment
from utils.env_config import load_env_vars, get_env

load_env_vars()

# Page configuration
st.set_page_config(
    page_title="Monitoring - Rakuten MLOps",
    page_icon="📈",
    layout="wide",
)

API_URL = get_env("API_URL", "http://localhost:8000")

SEVERITY_COLORS = {
    "OK": "🟢",
    "WARNING": "🟡",
    "ALERT": "🟠",
    "CRITICAL": "🔴",
}


def api_get(path: str):
    try:
        resp = requests.get(f"{API_URL}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(path: str, json_body: dict = None):
    try:
        resp = requests.post(f"{API_URL}{path}", json=json_body or {}, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
st.title("Monitoring & Alertes")
# ─────────────────────────────────────────────────────────────────────────────

# ── Alerting rules explanation ───────────────────────────────────────────────

st.header("Règles de détection du drift")

col_how, col_thresholds = st.columns(2)

with col_how:
    st.markdown("""
**Check quotidien** (Airflow, 1 h du matin)

Le DAG `daily_drift_check` compare les inférences récentes (7 jours)
à une fenêtre de référence (30 jours) en utilisant trois tests statistiques :
- **PSI** (Population Stability Index) sur les distributions des inputs et prédictions
- **KS** (Kolmogorov-Smirnov) sur les confidences
- **Chi-Square** sur les classes prédites

Le score global détermine la sévérité de l'alerte.
    """)

with col_thresholds:
    st.markdown("""
**Seuils de sévérité**

| Niveau | Score | Action |
|--------|-------|--------|
| 🟢 OK | < 0.1 | Aucune |
| 🟡 WARNING | 0.1 – 0.2 | Surveiller |
| 🟠 ALERT | 0.2 – 0.3 | Investiguer, envisager un retrain |
| 🔴 CRITICAL | > 0.3 | Retrain ou rollback recommandé |

Quand une alerte est créée, l'utilisateur peut agir via les boutons
ci-dessous : **ré-entraîner**, **rollback**, ou **investiguer**.
    """)

st.link_button("Ouvrir Grafana (dashboards)", "http://localhost:3000")

st.markdown("---")

# ── Tabs: Alerts, History, Actions ───────────────────────────────────────────

tab_alerts, tab_history, tab_actions = st.tabs(
    ["Alertes actives", "Historique du drift", "Actions effectuées"]
)

# ── Tab 1: Active Alerts ─────────────────────────────────────────────────────

with tab_alerts:

    if st.button("🔄 Rafraîchir", key="refresh_alerts"):
        st.rerun()

    data = api_get("/api/alerts?limit=20")

    if data and data.get("alerts"):
        for alert in data["alerts"]:
            severity = alert.get("severity", "UNKNOWN")
            icon = SEVERITY_COLORS.get(severity, "⚪")
            score = alert.get("overall_drift_score", 0)
            ack = alert.get("acknowledged", False)
            alert_id = alert.get("id")
            date = alert.get("report_date", "")[:19]
            status_tag = "✅ Traité" if ack else "⏳ En attente"

            with st.expander(
                f"{icon} [{severity}] Score : {score:.4f} — {date} — {status_tag}",
                expanded=not ack,
            ):
                c1, c2, c3 = st.columns(3)
                c1.metric("Data Drift (PSI)", f"{alert.get('data_drift_score', 0):.4f}")
                c2.metric("Prediction Drift (PSI)", f"{alert.get('prediction_drift_score', 0):.4f}")
                c3.metric("Score global", f"{score:.4f}")

                st.caption(
                    f"Référence : {alert.get('reference_samples', 0)} samples — "
                    f"Courant : {alert.get('current_samples', 0)} samples"
                )

                if not ack:
                    cols = st.columns(4)
                    with cols[0]:
                        if st.button("🔁 Retrain", key=f"retrain_{alert_id}"):
                            with st.spinner("Ré-entraînement..."):
                                result = api_post("/api/trigger-retrain")
                            if result:
                                st.success(result.get("message", "OK"))
                                api_post(
                                    f"/api/alerts/{alert_id}/acknowledge",
                                    {"action_type": "retrain", "details": {"result": result}, "performed_by": "streamlit_user"},
                                )
                    with cols[1]:
                        if st.button("⏪ Rollback", key=f"rollback_{alert_id}"):
                            with st.spinner("Rollback..."):
                                result = api_post("/api/rollback-model")
                            if result:
                                st.success(result.get("message", "OK"))
                                api_post(
                                    f"/api/alerts/{alert_id}/acknowledge",
                                    {"action_type": "rollback", "details": {"result": result}, "performed_by": "streamlit_user"},
                                )
                    with cols[2]:
                        if st.button("🔍 Investiguer", key=f"investigate_{alert_id}"):
                            api_post(
                                f"/api/alerts/{alert_id}/acknowledge",
                                {"action_type": "investigate", "performed_by": "streamlit_user"},
                            )
                            st.info("Marqué comme en investigation.")
                    with cols[3]:
                        if st.button("✅ OK", key=f"ack_{alert_id}"):
                            api_post(
                                f"/api/alerts/{alert_id}/acknowledge",
                                {"action_type": "acknowledge", "performed_by": "streamlit_user"},
                            )
                            st.success("Alerte acquittée.")
    else:
        st.success("Aucune alerte active. Le modèle fonctionne dans les seuils attendus.")

# ── Tab 2: Drift History ─────────────────────────────────────────────────────

with tab_history:
    data = api_get("/api/drift-reports?limit=60")

    if data and data.get("reports"):
        df = pd.DataFrame(data["reports"])
        df["report_date"] = pd.to_datetime(df["report_date"])
        df = df.sort_values("report_date")

        # Chart only completed analyses (avoid flat zeros from error/insufficient reports)
        completed_df = df[df["status"] == "completed"]
        if len(completed_df) > 1:
            chart_df = completed_df.set_index("report_date")[
                ["overall_drift_score", "data_drift_score", "prediction_drift_score"]
            ].rename(columns={
                "overall_drift_score": "Global",
                "data_drift_score": "Data Drift",
                "prediction_drift_score": "Pred Drift",
            })
            st.line_chart(chart_df)

        st.caption(
            "🟢 OK < 0.1 | 🟡 WARNING >= 0.1 | 🟠 ALERT >= 0.2 | 🔴 CRITICAL >= 0.3"
        )

        display_cols = ["report_date", "status", "severity", "overall_drift_score",
                        "data_drift_score", "prediction_drift_score", "drift_detected",
                        "reference_samples", "current_samples"]
        available_cols = [c for c in display_cols if c in df.columns]
        display_df = df[available_cols].sort_values("report_date", ascending=False)

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "report_date": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD HH:mm"),
                "status": st.column_config.TextColumn("Statut"),
                "overall_drift_score": st.column_config.NumberColumn("Global", format="%.4f"),
                "data_drift_score": st.column_config.NumberColumn("Data PSI", format="%.4f"),
                "prediction_drift_score": st.column_config.NumberColumn("Pred PSI", format="%.4f"),
            },
        )
    else:
        st.info("Pas encore de rapports de drift. Le DAG quotidien les génère automatiquement.")

# ── Tab 3: Action History ────────────────────────────────────────────────────

with tab_actions:
    data = api_get("/api/action-history?limit=50")

    if data and data.get("actions"):
        df = pd.DataFrame(data["actions"])
        df["created_at"] = pd.to_datetime(df["created_at"])
        df = df.sort_values("created_at", ascending=False)

        st.dataframe(
            df[["created_at", "action_type", "severity", "overall_drift_score", "performed_by", "drift_report_id"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "created_at": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD HH:mm"),
                "overall_drift_score": st.column_config.NumberColumn("Score", format="%.4f"),
            },
        )
    else:
        st.info("Aucune action enregistrée.")

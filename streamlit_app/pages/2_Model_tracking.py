"""
Modèles & Prédiction

Tab 1: Model tracking, auto-training, auto-promotion explanations
Tab 2: Test a prediction against the deployed model
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
import requests
import os
from datetime import datetime

# Add paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
streamlit_app_root = Path(__file__).parent.parent
sys.path.insert(0, str(streamlit_app_root))

# Page configuration
st.set_page_config(
    page_title="Model tracking - Rakuten MLOps",
    page_icon="🔬",
    layout="wide",
)

st.title("Modèles & Prédiction")

# Config
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
API_URL = os.getenv("API_URL", "http://localhost:8000")


@st.cache_resource
def get_mlflow_client():
    try:
        mlflow.set_tracking_uri(MLFLOW_URI)
        return MlflowClient(tracking_uri=MLFLOW_URI)
    except Exception as e:
        st.error(f"MLflow non disponible : {e}")
        return None


client = get_mlflow_client()

tab_tracking, tab_predict = st.tabs(["Suivi des modèles", "Test de prédiction"])

# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 : Model Tracking
# ─────────────────────────────────────────────────────────────────────────────

with tab_tracking:

    # ── Explanations ─────────────────────────────────────────────────────────

    st.header("Auto-training & Auto-promotion")

    col_train, col_promo = st.columns(2)

    with col_train:
        st.markdown("""
**Entraînement automatique** (hebdomadaire, Airflow)

Chaque lundi à 2h, le DAG `weekly_ml_pipeline` :
1. Charge +3 % de données dans PostgreSQL
2. Génère un dataset rééquilibré (RandomOverSampler)
3. Entraîne un modèle TF-IDF + LogReg
4. Enregistre le run, les métriques et les artifacts dans MLflow
        """)

    with col_promo:
        st.markdown("""
**Promotion conditionnelle**

Après chaque entraînement, le modèle est évalué :
- **F1 >= 0.75** et **meilleur** que le modèle en Production → promotion automatique
- **F1 < 0.75** ou **moins bon** → archivage, le modèle actuel reste en Production

Cela évite toute dégradation non contrôlée du service.
        """)

    st.markdown("")
    st.link_button("Ouvrir MLflow UI", "http://localhost:5000")

    st.markdown("---")

    # ── Model registry ───────────────────────────────────────────────────────

    st.header("Registre des modèles")

    MODEL_NAME = "rakuten_classifier"

    if client:
        try:
            versions = client.search_model_versions(f"name='{MODEL_NAME}'")

            if versions:
                version_data = []
                for v in versions:
                    version_data.append({
                        "Version": v.version,
                        "Stage": v.current_stage,
                        "Créé le": datetime.fromtimestamp(
                            v.creation_timestamp / 1000
                        ).strftime("%Y-%m-%d %H:%M"),
                        "Run ID": v.run_id[:8] if v.run_id else "N/A",
                    })

                st.dataframe(
                    pd.DataFrame(version_data),
                    use_container_width=True,
                    hide_index=True,
                )

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Production", sum(1 for v in versions if v.current_stage == "Production"))
                c2.metric("Staging",    sum(1 for v in versions if v.current_stage == "Staging"))
                c3.metric("None",       sum(1 for v in versions if v.current_stage == "None"))
                c4.metric("Archived",   sum(1 for v in versions if v.current_stage == "Archived"))
            else:
                st.info("Aucun modèle enregistré. Lancez un premier entraînement.")

        except Exception as e:
            st.warning(f"Impossible de charger le registre : {e}")
    else:
        st.info(f"MLflow non disponible ({MLFLOW_URI})")

    st.markdown("---")

    # ── Recent training runs ─────────────────────────────────────────────────

    st.header("Derniers entraînements")

    if client:
        try:
            experiments = client.search_experiments()
            training_exp = [e for e in experiments if "training" in e.name.lower()]

            if training_exp:
                runs = client.search_runs(
                    experiment_ids=[training_exp[0].experiment_id],
                    max_results=10,
                    order_by=["start_time DESC"],
                )

                if runs:
                    run_rows = []
                    for run in runs:
                        m = run.data.metrics
                        p = run.data.params
                        run_rows.append({
                            "Date": datetime.fromtimestamp(
                                run.info.start_time / 1000
                            ).strftime("%Y-%m-%d %H:%M"),
                            "Run ID": run.info.run_id[:8],
                            "F1": f"{m.get('test_f1_weighted', 0):.4f}",
                            "Accuracy": f"{m.get('test_accuracy', 0):.4f}",
                            "Features": p.get("max_features", "?"),
                            "C": p.get("C", "?"),
                        })

                    st.dataframe(
                        pd.DataFrame(run_rows),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("Aucun entraînement trouvé.")
            else:
                st.info("Pas d'expérience de training dans MLflow.")
        except Exception as e:
            st.warning(f"Impossible de charger les runs : {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 : Test Prediction
# ─────────────────────────────────────────────────────────────────────────────

with tab_predict:

    st.header("Tester une prédiction")

    st.markdown(
        "Envoyez une requête au modèle **Production** déployé sur FastAPI. "
        "Chaque prédiction est loggée pour le suivi du drift."
    )

    st.link_button("Ouvrir la documentation API", f"{API_URL}/docs")

    examples = {
        "Livre Harry Potter": {
            "designation": "Harry Potter à l'école des sorciers",
            "description": "Premier tome de la saga Harry Potter. Roman jeunesse fantastique.",
        },
        "Chaise de bureau": {
            "designation": "Chaise de bureau ergonomique",
            "description": "Chaise avec dossier réglable, accoudoirs, roulettes pour parquet.",
        },
        "Console PlayStation": {
            "designation": "PlayStation 5 Console",
            "description": "Console de jeux vidéo nouvelle génération avec lecteur Blu-ray.",
        },
    }

    example_choice = st.selectbox(
        "Exemple ou saisie libre",
        options=["Saisie libre"] + list(examples.keys()),
    )

    if example_choice != "Saisie libre":
        selected = examples[example_choice]
        designation = st.text_input("Designation", value=selected["designation"])
        description = st.text_area("Description", value=selected["description"], height=80)
    else:
        designation = st.text_input("Designation", value="")
        description = st.text_area("Description", value="", height=80)

    if st.button("Prédire", type="primary", disabled=(not designation or not description)):
        payload = {"designation": designation, "description": description}

        try:
            with st.spinner("Prédiction en cours..."):
                response = requests.post(f"{API_URL}/predict", json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()

                col1, col2 = st.columns(2)
                col1.metric("Classe prédite", result.get("predicted_class", "N/A"))
                col2.metric("Confiance", f"{result.get('confidence', 0):.2%}")

                if "probabilities" in result:
                    probs = result["probabilities"]
                    top = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5]
                    st.dataframe(
                        pd.DataFrame(top, columns=["Classe", "Probabilité"]),
                        use_container_width=True,
                        hide_index=True,
                    )

                with st.expander("Réponse API complète"):
                    st.json(result)
            else:
                st.error(f"Erreur API : {response.status_code}")
                st.text(response.text)

        except requests.exceptions.ConnectionError:
            st.error(f"API non disponible ({API_URL})")
        except Exception as e:
            st.error(f"Erreur : {e}")

"""
Données & Stratégie d'Entraînement

Overview of the database state and explanation of the training approach.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import plotly.express as px

# Add paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
streamlit_app_root = Path(__file__).parent.parent
sys.path.insert(0, str(streamlit_app_root))

from utils.env_config import get_db_config

# Page configuration
st.set_page_config(
    page_title="Data - Rakuten MLOps",
    page_icon="🗄️",
    layout="wide",
)

st.title("Données & Stratégie d'Entraînement")

DB_CONFIG = get_db_config()

# ─────────────────────────────────────────────────────────────────────────────
# Section 1 : État de la base de données
# ─────────────────────────────────────────────────────────────────────────────

st.header("État de la base de données")


@st.cache_data(ttl=30)
def get_database_stats():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT COUNT(*) as total_products,
                   COUNT(DISTINCT l.prdtypecode) as total_classes
            FROM products p
            LEFT JOIN labels l ON p.productid = l.productid
        """)
        stats = cur.fetchone()

        cur.execute("""
            SELECT percentage, total_rows, completed_at
            FROM data_loads WHERE status = 'completed'
            ORDER BY percentage DESC LIMIT 1
        """)
        load_info = cur.fetchone()

        cur.close()
        conn.close()

        return {
            "total_products": stats["total_products"] if stats else 0,
            "total_classes": stats["total_classes"] if stats else 0,
            "current_percentage": float(load_info["percentage"]) if load_info else 0,
            "last_load_date": load_info["completed_at"] if load_info else None,
        }
    except Exception as e:
        st.error(f"Connexion impossible : {e}")
        return None


stats = get_database_stats()

if stats:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Produits en base", f"{stats['total_products']:,}")
    c2.metric("Classes", stats["total_classes"])
    c3.metric("Données chargées", f"{stats['current_percentage']:.0f} %")
    c4.metric("Prochain chargement", f"{min(stats['current_percentage'] + 3, 100):.0f} %")

    st.progress(stats["current_percentage"] / 100)
    if stats["last_load_date"]:
        st.caption(f"Dernier chargement : {stats['last_load_date'].strftime('%Y-%m-%d %H:%M')}")
else:
    st.warning("Base de données non disponible. Lancer `make init-db`.")

st.markdown("")

# ── Class distribution ───────────────────────────────────────────────────────


@st.cache_data(ttl=30)
def get_class_distribution():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        df = pd.read_sql_query(
            """
            SELECT l.prdtypecode, COUNT(*) as count
            FROM labels l JOIN products p ON p.productid = l.productid
            GROUP BY l.prdtypecode ORDER BY count DESC
            """,
            conn,
        )
        conn.close()
        return df
    except Exception:
        return None


dist_df = get_class_distribution()

if dist_df is not None and len(dist_df) > 0:
    # Sort by count ascending so largest bar is at the top
    plot_df = dist_df.sort_values("count", ascending=True)
    plot_df["prdtypecode"] = plot_df["prdtypecode"].astype(str)

    fig = px.bar(
        plot_df,
        x="count",
        y="prdtypecode",
        orientation="h",
        title="Distribution des classes (données brutes)",
        labels={"prdtypecode": "Code catégorie", "count": "Nombre de produits"},
    )
    fig.update_traces(marker_color="#1f77b4")
    fig.update_layout(yaxis=dict(type="category"))
    st.plotly_chart(fig, use_container_width=True)

    imbalance = dist_df["count"].max() / dist_df["count"].min() if dist_df["count"].min() > 0 else 0
    st.caption(
        f"{len(dist_df)} classes — ratio de déséquilibre : **{imbalance:.1f}x** "
        f"(classe la plus fréquente / la plus rare)"
    )

# ── Load history ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=30)
def get_load_history():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        df = pd.read_sql_query(
            """
            SELECT batch_name, percentage, total_rows, completed_at
            FROM data_loads WHERE status = 'completed'
            ORDER BY percentage ASC
            """,
            conn,
        )
        conn.close()
        return df
    except Exception:
        return None


history_df = get_load_history()

if history_df is not None and len(history_df) > 0:
    st.subheader("Historique des chargements")
    display = history_df.copy()
    display["completed_at"] = pd.to_datetime(display["completed_at"]).dt.strftime("%Y-%m-%d %H:%M")
    display["percentage"] = display["percentage"].apply(lambda x: f"{x:.0f} %")
    display["total_rows"] = display["total_rows"].apply(lambda x: f"{x:,}")
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "batch_name": "Batch",
            "percentage": "Chargé",
            "total_rows": "Lignes",
            "completed_at": "Date",
        },
    )

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Section 2 : Stratégie d'entraînement
# ─────────────────────────────────────────────────────────────────────────────

st.header("Stratégie d'entraînement")

st.markdown("""
**Chargement incrémental (+3 % / semaine)**
Les données sont chargées progressivement de 40 % à 100 % pour simuler un flux réel
de nouvelles données en production. Chaque chargement est tracé dans une table d'audit
PostgreSQL, garantissant la reproductibilité complète de chaque entraînement.

**Modèle : TF-IDF + Logistic Regression**
Choix pragmatique pour un pipeline de classification texte : rapide à entraîner,
facile à interpréter, et suffisamment performant pour un grand nombre de classes.
Les features sont extraites via TF-IDF (unigrammes + bigrammes, 5 000 features max),
puis classifiées par une Logistic Regression régularisée.

**Rééquilibrage par RandomOverSampling**
Le dataset original est fortement déséquilibré (ratio jusqu'à ~30x).
Avant chaque entraînement, un sur-échantillonnage aléatoire ramène toutes les classes
au même effectif, évitant que le modèle ignore les classes minoritaires.
Le dataset rééquilibré est loggé dans MLflow comme artifact pour traçabilité.
""")

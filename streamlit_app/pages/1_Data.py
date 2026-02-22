"""
Donnees

Presentation du jeu de donnees, du processus d'ingestion et du suivi des donnees.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import plotly.express as px

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
streamlit_app_root = Path(__file__).parent.parent
sys.path.insert(0, str(streamlit_app_root))

from utils.env_config import get_db_config

st.set_page_config(
    page_title="Donnees - Rakuten MLOps",
    page_icon="",
    layout="wide",
)

st.title("Donnees")

DB_CONFIG = get_db_config()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Section 1 : Jeu de donnees
# ---------------------------------------------------------------------------

st.header("Jeu de donnees")

st.markdown(
    "Le catalogue Rakuten France est utilise comme donnees d'entrainement. "
    "Chaque produit possede une **designation** (titre court), une **description** "
    "optionnelle (texte plus long), une **image** et un **code categorie** "
    "(le label a predire). Le jeu de donnees contient 27 categories de produits."
)

stats = get_database_stats()

if stats:
    c1, c2, c3 = st.columns(3)
    c1.metric("Produits en base", f"{stats['total_products']:,}")
    c2.metric("Classes", stats["total_classes"])
    c3.metric("Donnees chargees", f"{stats['current_percentage']:.0f} %")

    st.progress(stats["current_percentage"] / 100)
    if stats["last_load_date"]:
        st.caption(f"Dernier chargement : {stats['last_load_date'].strftime('%Y-%m-%d %H:%M')}")
else:
    st.warning("Base de donnees non disponible. Lancer `make init-db`.")

dist_df = get_class_distribution()

if dist_df is not None and len(dist_df) > 0:
    plot_df = dist_df.sort_values("count", ascending=True)
    plot_df["prdtypecode"] = plot_df["prdtypecode"].astype(str)

    fig = px.bar(
        plot_df,
        x="count",
        y="prdtypecode",
        orientation="h",
        title="Distribution des classes",
        labels={"prdtypecode": "Code categorie", "count": "Nombre de produits"},
    )
    fig.update_traces(marker_color="#1f77b4")
    fig.update_layout(yaxis=dict(type="category"))
    st.plotly_chart(fig, use_container_width=True)

    imbalance = (
        dist_df["count"].max() / dist_df["count"].min()
        if dist_df["count"].min() > 0
        else 0
    )
    st.caption(
        f"{len(dist_df)} classes -- ratio de desequilibre : **{imbalance:.1f}x** "
        f"(classe la plus frequente / la plus rare)"
    )

history_df = get_load_history()

if history_df is not None and len(history_df) > 0:
    st.subheader("Historique des chargements")
    display = history_df.copy()
    display["completed_at"] = pd.to_datetime(display["completed_at"]).dt.strftime(
        "%Y-%m-%d %H:%M"
    )
    display["percentage"] = display["percentage"].apply(lambda x: f"{x:.0f} %")
    display["total_rows"] = display["total_rows"].apply(lambda x: f"{x:,}")
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "batch_name": "Batch",
            "percentage": "Charge",
            "total_rows": "Lignes",
            "completed_at": "Date",
        },
    )


# ---------------------------------------------------------------------------
# Section 2 : Ingestion des donnees
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Ingestion des donnees")

st.markdown("""
Les donnees brutes se presentent sous forme de fichiers CSV (`x_train.csv`
pour les caracteristiques produit, `y_train.csv` pour les labels).
Le pipeline d'ingestion les charge dans PostgreSQL en deux etapes.

**1. Stockage brut.**
Les lignes des fichiers CSV sont inserees telles quelles dans la table
`raw_products`. Chaque ligne conserve la designation, la description,
l'identifiant image et le code categorie d'origine, accompagnes d'un
`batch_id` et d'un horodatage `dt_ingested`.

**2. Traitement.**
Une etape de nettoyage produit la table `processed_products` : les champs
texte sont normalises (mise en minuscules, suppression du HTML et des
caracteres speciaux), et les references images sont resolues vers leur
chemin de stockage MinIO. Chaque ligne traitee porte egalement son
`batch_id` et un horodatage `dt_processed`.

Les tables `products` et `labels` contiennent la vue consolidee de
l'ensemble des donnees ingerees et servent de source pour l'entrainement.
""")


# ---------------------------------------------------------------------------
# Section 3 : Suivi des donnees
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Suivi des donnees")

st.markdown("""
Chaque table du schema porte des horodatages et des identifiants de batch,
ce qui permet de reconstituer le jeu de donnees exact utilise pour
n'importe quel entrainement.

- La table `data_loads` enregistre chaque batch d'ingestion avec ses
  horodatages `started_at` / `completed_at`, le nombre de lignes chargees,
  et une colonne JSONB `metadata` pour le contexte supplementaire.
- La table `products_history` est alimentee automatiquement par un trigger :
  chaque INSERT ou UPDATE sur `products` est journalise avec la date de
  l'operation (`operation_date`) et le `load_batch_id` correspondant.
- Lorsqu'un entrainement demarre, il interroge la base a un instant donne.
  Comme chaque ligne de `products` possede un horodatage `created_at`,
  la requete peut etre rejouee ulterieurement pour retrouver exactement
  les memes lignes.

Ainsi, pour tout modele enregistre dans MLflow, on peut remonter au batch
exact, aux lignes exactes et au moment precis ou les donnees d'entrainement
ont ete extraites.
""")

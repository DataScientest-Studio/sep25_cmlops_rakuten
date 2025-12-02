"""
Ingestion SQL (CSV surrogate)
-----------------------------
Ce module lit les fichiers bruts X/Y, fusionne les colonnes utiles et produit
un CSV canonicalisé partagé par toute la pipeline de features/training.
"""

from pathlib import Path
from typing import Iterable

import pandas as pd

# Colonnes attendues par le reste de la chaîne.
CANONICAL_COLUMNS = ["productid", "imageid", "designation", "description", "prdtypecode"]


def clean_text(value: str) -> str:
    """Nettoyage simple: string, trim + minuscules."""
    if not isinstance(value, str):
        value = "" if pd.isna(value) else str(value)
    return value.strip().lower()


def load_and_merge(x_path: Path, y_path: Path) -> pd.DataFrame:
    """Charge X/Y puis fusionne via l'index présent en première colonne."""
    x_df = pd.read_csv(x_path)
    y_df = pd.read_csv(y_path)

    x_df = x_df.rename(columns={x_df.columns[0]: "idx"})
    y_df = y_df.rename(columns={y_df.columns[0]: "idx"})

    merged = x_df.merge(y_df, on="idx", how="left")
    return merged


def ensure_canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ne conserve que les colonnes standard dans le bon ordre."""
    missing = [col for col in CANONICAL_COLUMNS if col not in df.columns]
    if missing:
        raise KeyError(f"Colonnes manquantes dans les CSV: {missing}")

    canonical = df[CANONICAL_COLUMNS].copy()
    for text_col in ["designation", "description"]:
        canonical[text_col] = canonical[text_col].apply(clean_text)
    return canonical


def validate_images(df: pd.DataFrame, image_dir: Path) -> Iterable[str]:
    """Retourne la liste des images manquantes (simple contrôle pédagogique)."""
    missing = []
    for _, row in df.iterrows():
        filename = f"image_{row['imageid']}_product_{row['productid']}.jpg"
        if not (image_dir / filename).exists():
            missing.append(filename)
    return missing


def export_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    """Sauvegarde le CSV canonicalisé dans data/interim."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"✅ CSV généré: {output_path}")


def run_ingestion(
    x_path: Path = Path("data/raw/X_train.csv"),
    y_path: Path = Path("data/raw/Y_train.csv"),
    image_dir: Path = Path("data/raw/images/image_train"),
    output_path: Path = Path("data/interim/merged_train_sql.csv"),
) -> None:
    """Pipeline complète utilisée par Prefect ou exécutée à la main."""
    print("📥 Chargement CSV...")
    merged = load_and_merge(x_path, y_path)

    print("🧹 Canonicalisation des colonnes...")
    canonical = ensure_canonical_columns(merged)

    print("🖼️ Vérification basique des images...")
    missing = validate_images(canonical, image_dir)
    if missing:
        print(f"⚠️ {len(missing)} images manquantes (liste tronquée): {missing[:5]}")
    else:
        print("👌 Toutes les images attendues sont présentes au chemin fourni.")

    print("💾 Export CSV final...")
    export_dataframe(canonical, output_path)


if __name__ == "__main__":
    run_ingestion()

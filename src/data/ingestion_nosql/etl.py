"""
Ingestion NoSQL
---------------
Lit les fichiers bruts X/Y, prépare un DataFrame canonicalisé, charge MongoDB
avec ces documents puis exporte un CSV identique à la version SQL.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Ensure project root is importable when running as a script (python src/...).
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.data.ingestion_sql.etl import (
    CANONICAL_COLUMNS,
    clean_text,
    ensure_canonical_columns,
    load_and_merge,
)


def push_to_mongo(
    df: pd.DataFrame,
    mongo_uri: str,
    db_name: str,
    collection_name: str,
) -> None:
    """Remplace le contenu de la collection par le DataFrame fourni."""
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    collection = client[db_name][collection_name]
    collection.delete_many({})
    collection.insert_many(df.to_dict("records"))
    print(f"🍃 Mongo alimenté avec {len(df)} documents.")


def export_csv(df: pd.DataFrame, output_path: Path) -> None:
    """Sauvegarde le DataFrame canonicalisé sur disque."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"💾 CSV généré: {output_path}")


def run_ingestion(
    x_path: Path,
    y_path: Path,
    output_path: Path,
    *,
    mongo_uri: str,
    db_name: str,
    collection_name: str,
    skip_mongo: bool = False,
) -> None:
    """Pipeline NoSQL complète: fichiers bruts -> Mongo (optionnel) + CSV."""
    print("📥 Lecture des fichiers bruts...")
    merged = load_and_merge(x_path, y_path)

    print("🧹 Canonicalisation des colonnes...")
    canonical = ensure_canonical_columns(merged)

    if skip_mongo:
        print("⚠️ Option --skip-mongo activée, chargement Mongo ignoré.")
    else:
        try:
            print("🍃 Chargement MongoDB...")
            push_to_mongo(
                canonical[CANONICAL_COLUMNS],
                mongo_uri=mongo_uri,
                db_name=db_name,
                collection_name=collection_name,
            )
        except PyMongoError as exc:
            print(f"❌ Impossible de contacter Mongo ({exc}). Poursuite avec CSV seulement.")

    print("💾 Export CSV final (source NoSQL)...")
    export_csv(canonical[CANONICAL_COLUMNS], output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ETL NoSQL -> Mongo + CSV canonique.")
    parser.add_argument("--x-path", type=Path, default=Path("data/raw/X_train.csv"))
    parser.add_argument("--y-path", type=Path, default=Path("data/raw/Y_train.csv"))
    parser.add_argument("--output-path", type=Path, default=Path("data/interim/merged_train_nosql.csv"))
    parser.add_argument("--mongo-uri", type=str, default="mongodb://localhost:27017")
    parser.add_argument("--db-name", type=str, default="rakuten_db")
    parser.add_argument("--collection-name", type=str, default="produits")
    parser.add_argument("--skip-mongo", action="store_true", help="Ne pas charger Mongo (utile pour tests hors-ligne).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_ingestion(
        x_path=args.x_path,
        y_path=args.y_path,
        output_path=args.output_path,
        mongo_uri=args.mongo_uri,
        db_name=args.db_name,
        collection_name=args.collection_name,
        skip_mongo=args.skip_mongo,
    )
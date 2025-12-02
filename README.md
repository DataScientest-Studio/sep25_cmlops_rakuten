Rakuten Class Prediction (WIP)
==============================

This repository tracks an in-progress effort to classify Rakuten product listings into their category codes. The scope includes:

- cleaning and ingesting catalog data
- training and serving text-based models
- exposing lightweight APIs for experimentation

Documentation will stay intentionally minimal for now and evolve alongside the project. Expect frequent structural changes as we iterate.

Quick start (local data)
------------------------

- place `X_train.csv`, `Y_train.csv` and `images/image_train/` inside `data/raw/`
- run `python src/data/ingestion_sql/etl.py` → generates `data/interim/merged_train_sql.csv`
- run `python src/data/ingestion_nosql/etl.py` → seeds MongoDB **and** exports `data/interim/merged_train_nosql.csv`
- optional: `python src/data/incremental_dataset.py` to simulate weekly data growth (use with cron)

Ingestion pipelines
-------------------

- **SQL/CSV path** (`src/data/ingestion_sql/etl.py`): fusionne `X_train/Y_train`, nettoie `designation/description`, contrôle simplement les images, puis écrit le CSV canonique `merged_train_sql.csv`.
- **NoSQL path** (`src/data/ingestion_nosql/etl.py`): réutilise la même logique pour générer un DataFrame identique, charge MongoDB (`rakuten_db.produits`) et exporte `merged_train_nosql.csv`.
- Les deux fichiers partagent les colonnes `productid, imageid, designation, description, prdtypecode`. Pour vérifier rapidement :
  ```
  python - <<'PY'
  import pandas as pd
  sql = pd.read_csv("data/interim/merged_train_sql.csv")
  nosql = pd.read_csv("data/interim/merged_train_nosql.csv")
  print("Colonnes identiques ?", list(sql.columns) == list(nosql.columns))
  print(f"Tailles -> SQL:{len(sql)}, NoSQL:{len(nosql)}")
  PY
  ```

Incremental data simulator
--------------------------

- `python src/data/incremental_dataset.py` écrit `data/incremented/merged_train_incremental.csv` avec 10 % du dataset lors de la première exécution, puis ajoute +2 % à chaque relance (ratios configurables via `--initial-ratio` et `--step-ratio`).
- L’état est stocké dans `data/incremented/state.json`, ce qui permet d’automatiser l’exécution (cron/launchd) pour démontrer l’entraînement répété sur des données évolutives.

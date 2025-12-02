"""
Dataset incrémental
-------------------
Ce script simule l'arrivée progressive de nouvelles données.
- 1ère exécution : écrit 10 % du dataset dans data/incremented/
- exécutions suivantes : ajoute 2 % supplémentaires (jusqu'à 100 %)

Idéal pour être déclenché par cron/launchd chaque dimanche soir.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

import pandas as pd

# Ensure project root is importable when running as script (python src/...).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.data.ingestion_sql.etl import ensure_canonical_columns, load_and_merge

STATE_FILE = Path("data/incremented/state.json")
OUTPUT_FILE = Path("data/incremented/merged_train_incremental.csv")


def load_state() -> Dict[str, float]:
    """Charge le pourcentage déjà disponible (0.0 si première exécution)."""
    if not STATE_FILE.exists():
        return {"current_ratio": 0.0}
    with STATE_FILE.open() as fh:
        return json.load(fh)


def save_state(state: Dict[str, float]) -> None:
    """Persiste le nouveau pourcentage exposé."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w") as fh:
        json.dump(state, fh, indent=2)


def compute_next_ratio(current_ratio: float, initial: float, step: float) -> float:
    """Calcule le prochain pourcentage à exposer."""
    if current_ratio <= 0.0:
        return initial
    return min(1.0, current_ratio + step)


def build_subset(df: pd.DataFrame, ratio: float) -> pd.DataFrame:
    """Retourne les premières N lignes correspondant au ratio souhaité."""
    n_rows = max(1, int(len(df) * ratio))
    return df.iloc[:n_rows].copy()


def write_subset(df: pd.DataFrame) -> None:
    """Sauvegarde le subset dans data/incremented/."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"💾 Dataset incrémental mis à jour ({len(df)} lignes) -> {OUTPUT_FILE}")


def update_incremental_dataset(
    x_path: Path,
    y_path: Path,
    initial_ratio: float = 0.10,
    step_ratio: float = 0.02,
) -> None:
    """Pipeline principale: merge -> canonicalisation -> sous-échantillon."""
    if not (0.0 < initial_ratio <= 1.0) or not (0.0 < step_ratio <= 1.0):
        raise ValueError("Les ratios doivent être compris entre 0 et 1.")

    state = load_state()
    target_ratio = compute_next_ratio(state["current_ratio"], initial_ratio, step_ratio)
    if target_ratio == state["current_ratio"] and target_ratio >= 1.0:
        print("100 % des données sont déjà exposées. Rien à faire.")
        return

    print(f"Ratio visé cette exécution: {target_ratio:.2%}")

    merged = load_and_merge(x_path, y_path)
    canonical = ensure_canonical_columns(merged)

    subset = build_subset(canonical, target_ratio)
    write_subset(subset)

    save_state({"current_ratio": target_ratio})


def parse_args() -> argparse.Namespace:
    """Lecture des arguments CLI."""
    parser = argparse.ArgumentParser(description="Simule l'arrivée incrémentale de données.")
    parser.add_argument("--initial-ratio", type=float, default=0.10, help="Part du dataset disponible lors de la première exécution (0-1).")
    parser.add_argument("--step-ratio", type=float, default=0.02, help="Part supplémentaire ajoutée à chaque exécution suivante (0-1).")
    parser.add_argument("--x-path", type=Path, default=Path("data/raw/X_train.csv"), help="Chemin vers X_train.csv local.")
    parser.add_argument("--y-path", type=Path, default=Path("data/raw/Y_train.csv"), help="Chemin vers Y_train.csv local.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    update_incremental_dataset(
        x_path=args.x_path,
        y_path=args.y_path,
        initial_ratio=args.initial_ratio,
        step_ratio=args.step_ratio,
    )


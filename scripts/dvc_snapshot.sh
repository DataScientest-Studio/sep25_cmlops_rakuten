#!/bin/bash
# =========================================================================
# DVC Snapshot Script
# Usage: docker exec rakuten_dvc bash /workspace/scripts/dvc_snapshot.sh
#
# Appelé après que le DAG a exporté processed_products.csv
# Versionne data/processed/ dans DVC et push vers MinIO
# =========================================================================

set -e

cd /workspace

echo "=== DVC Snapshot ==="
echo "Date: $(date)"

# Vérifier que le fichier exporté existe
if [ ! -f data/processed/processed_products.csv ]; then
    echo "ERROR: data/processed/processed_products.csv not found"
    echo "Le DAG doit d'abord exporter les données (task export_processed)"
    exit 1
fi

# Stats du fichier
ROWS=$(tail -n +2 data/processed/processed_products.csv | wc -l)
echo "Fichier: data/processed/processed_products.csv"
echo "Lignes: $ROWS"

# DVC add
echo "=== dvc add ==="
dvc add data/processed/processed_products.csv

# DVC push vers MinIO
echo "=== dvc push ==="
dvc push

# Git commit
echo "=== git commit ==="
git add data/processed/processed_products.csv.dvc &&
git commit -m "data: snapshot $(date +%Y%m%d_%H%M%S) - ${ROWS} rows" --allow-empty

echo "=== DVC Snapshot terminé ==="
echo "Hash DVC: $(cat data/processed/processed_products.csv.dvc | grep md5 | head -1)"


chmod 666 /workspace/data/processed/processed_products.csv

#!/bin/bash
set -e

# Create additional databases
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE airflow_db;
    CREATE DATABASE mlflow_db;
EOSQL

echo "Created airflow_db and mlflow_db databases"

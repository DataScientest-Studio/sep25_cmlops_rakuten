"""
Export module:
    Export processed_products to CSV file for DVC versioning.
    Output: /opt/airflow/data/processed/processed_products.csv
"""

import logging
import os

import pandas as pd
import psycopg2

logger = logging.getLogger(__name__)


def get_pg_conn():
    """Create PostgreSQL connection using psycopg2."""
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "rakuten_db"),
        user=os.environ.get("POSTGRES_USER", "rakuten_user"),
        password=os.environ.get("POSTGRES_PASSWORD", "change_this_password"),
    )


def run_export(**context) -> dict:
    """
    Export all processed_products to CSV for DVC snapshot.
    """
    output_dir = "/opt/airflow/data/processed"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "processed_products.csv")

    conn = get_pg_conn()
    query = """
        SELECT productid, imageid, prdtypecode, prodtype,
               designation_tr, description_tr, text_tr,
               path_image_minio, image_exists, batch_id, dt_processed
        FROM processed_products
        ORDER BY productid
    """
    df = pd.read_sql(query, conn)
    conn.close()

    df.to_csv(output_path, index=False, sep=";")
    logger.info(f"Exported {len(df)} rows to {output_path}")

    context["ti"].xcom_push(key="export_path", value=output_path)
    context["ti"].xcom_push(key="export_rows", value=len(df))

    return {"path": output_path, "rows": len(df)}

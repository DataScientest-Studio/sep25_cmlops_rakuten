"""
Transformation module:
    1. Read batch from raw_products
    2. Apply clean_text → designation_tr, description_tr, text_tr
    3. Build path_image_minio, check image_exists
    4. Insert into processed_products
"""

import logging
import os

import pandas as pd
import psycopg2
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from psycopg2.extras import execute_values

from utils.text_preprocessing import input_text_train

logger = logging.getLogger(__name__)

MINIO_CONN_ID = "minio_s3"
IMAGES_BUCKET = "dvc-storage"


def get_pg_conn():
    """Create PostgreSQL connection using psycopg2."""
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "rakuten_db"),
        user=os.environ.get("POSTGRES_USER", "rakuten_user"),
        password=os.environ.get("POSTGRES_PASSWORD", "change_this_password"),
    )


def check_images_exist(df: pd.DataFrame) -> pd.Series:
    """Check which images exist in MinIO."""
    hook = S3Hook(aws_conn_id=MINIO_CONN_ID)
    existing_keys = hook.list_keys(bucket_name=IMAGES_BUCKET, prefix="images/") or []
    existing_filenames = {os.path.basename(k) for k in existing_keys}

    image_filenames = df.apply(
        lambda row: f"image_{int(row['imageid'])}_product_{int(row['productid'])}.jpg",
        axis=1,
    )
    return image_filenames.isin(existing_filenames)


def run_transformation(**context) -> dict:
    """
    Transform raw_products → processed_products for a given batch.
    """
    batch_id = context["ti"].xcom_pull(task_ids="ingest", key="batch_id")
    if not batch_id:
        logger.warning("No batch_id received, skipping transformation")
        return {"batch_id": None, "rows": 0}

    logger.info(f"Transforming batch: {batch_id}")

    conn = get_pg_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM processed_products WHERE batch_id = %s", (batch_id,)
    )
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    if count > 0:
        logger.warning(f"Batch {batch_id} already transformed ({count} rows), skipping")
        return {"batch_id": batch_id, "rows": 0}

    # Read batch from raw_products
    conn = get_pg_conn()
    query = f"SELECT * FROM raw_products WHERE batch_id = '{batch_id}'"
    df = pd.read_sql(query, conn)
    conn.close()
    logger.info(f"Read {len(df)} rows from raw_products")

    if df.empty:
        logger.warning(f"No data found for batch {batch_id}")
        return {"batch_id": batch_id, "rows": 0}

    # Apply clean_text → designation_tr, description_tr, text_tr
    df = input_text_train(
        df, col_des="product_designation", col_desc="product_description"
    )
    logger.info("Text cleaning applied")

    # Build MinIO image paths
    df["path_image_minio"] = df.apply(
        lambda row: (
            f"s3://{IMAGES_BUCKET}/images/image_{int(row['imageid'])}_product_{int(row['productid'])}.jpg"
        ),
        axis=1,
    )

    # Check image existence in MinIO
    df["image_exists"] = check_images_exist(df)
    n_images = int(df["image_exists"].sum())
    logger.info(f"Images found in MinIO: {n_images}/{len(df)}")

    # Insert into processed_products
    columns = [
        "productid",
        "imageid",
        "prdtypecode",
        "prodtype",
        "designation_tr",
        "description_tr",
        "text_tr",
        "path_image_minio",
        "image_exists",
        "batch_id",
    ]

    values = [tuple(row[col] for col in columns) for _, row in df.iterrows()]

    conn = get_pg_conn()
    cursor = conn.cursor()

    insert_query = f"""
        INSERT INTO processed_products ({", ".join(columns)})
        VALUES %s
    """

    execute_values(cursor, insert_query, values, page_size=1000)
    conn.commit()
    cursor.close()
    conn.close()

    logger.info(f"Inserted {len(df)} rows into processed_products")

    # Push to XCom
    context["ti"].xcom_push(key="batch_id", value=batch_id)
    context["ti"].xcom_push(key="transform_rows", value=len(df))

    return {"batch_id": batch_id, "rows": len(df), "images": n_images}

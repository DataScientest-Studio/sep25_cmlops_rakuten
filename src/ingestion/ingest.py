"""
Ingestion module:
    1. Download ZIP from MinIO (landing/incoming/)
    2. Unzip: extract products.csv + images/
    3. Load products.csv → raw_products (PostgreSQL)
    4. Upload images → MinIO (dvc-storage/images/)
    5. Archive ZIP (incoming/ → archived/)
"""

import logging
import os
import shutil
import zipfile

import pandas as pd
import psycopg2
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

MINIO_CONN_ID = "minio_s3"
LANDING_BUCKET = "landing"
IMAGES_BUCKET = "dvc-storage"
TMP_DIR = "/tmp/rakuten_ingest"


def get_pg_conn():
    """Create PostgreSQL connection"""
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "rakuten_db"),
        user=os.environ.get("POSTGRES_USER", "rakuten_user"),
        password=os.environ.get("POSTGRES_PASSWORD", "change_this_password"),
    )


def list_new_zips() -> list[str]:
    """List ZIP files in MinIO landing/incoming/."""
    hook = S3Hook(aws_conn_id=MINIO_CONN_ID)
    keys = hook.list_keys(bucket_name=LANDING_BUCKET, prefix="incoming/") or []
    zip_keys = [k for k in keys if k.endswith(".zip")]
    logger.info(f"Found {len(zip_keys)} ZIP files in landing/incoming/")
    return zip_keys


def download_zip(key: str) -> str:
    """Download a ZIP file from MinIO to local tmp."""
    os.makedirs(TMP_DIR, exist_ok=True)
    hook = S3Hook(aws_conn_id=MINIO_CONN_ID)
    local_path = os.path.join(TMP_DIR, os.path.basename(key))

    obj = hook.get_key(key=key, bucket_name=LANDING_BUCKET)
    obj.download_file(local_path)

    logger.info(f"Downloaded {key} → {local_path}")
    return local_path


def unzip_file(zip_path: str) -> str:
    """Unzip file and return extraction directory."""
    extract_dir = zip_path.replace(".zip", "")
    os.makedirs(extract_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    logger.info(f"Unzipped → {extract_dir}")
    return extract_dir


def load_csv_to_raw(extract_dir: str, batch_id: str) -> int:
    """Load products.csv into raw_products table"""
    csv_path = os.path.join(extract_dir, "products.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"products.csv not found in {extract_dir}")

    df = pd.read_csv(csv_path, sep=";", encoding="utf-8")
    logger.info(f"CSV loaded: {len(df)} rows, columns: {list(df.columns)}")

    # Add pipeline metadata
    df["batch_id"] = batch_id
    df["source_file"] = "products.csv"

    # Fill NaN descriptions with empty string
    df["product_description"] = df["product_description"].fillna("")

    conn = get_pg_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM raw_products WHERE batch_id = %s", (batch_id,))
    count = cursor.fetchone()[0]

    if count > 0:
        logger.warning(f"Batch {batch_id} already exists ({count} rows), skipping")
        cursor.close()
        conn.close()
        return 0

    columns = [
        "productid",
        "imageid",
        "prdtypecode",
        "prodtype",
        "product_designation",
        "product_description",
        "batch_id",
        "source_file",
    ]

    values = [tuple(row[col] for col in columns) for _, row in df.iterrows()]

    insert_query = f"""
        INSERT INTO raw_products ({", ".join(columns)})
        VALUES %s
    """

    execute_values(cursor, insert_query, values, page_size=1000)
    conn.commit()
    cursor.close()
    conn.close()

    logger.info(f"Inserted {len(df)} rows into raw_products (batch: {batch_id})")
    return len(df)


def upload_images_to_minio(extract_dir: str, batch_id: str) -> int:
    """Upload extracted images to MinIO dvc-storage/images/."""
    images_dir = os.path.join(extract_dir, "images")
    if not os.path.isdir(images_dir):
        logger.warning(f"No images/ directory in {extract_dir}")
        return 0

    hook = S3Hook(aws_conn_id=MINIO_CONN_ID)
    count = 0

    for img_file in os.listdir(images_dir):
        if not img_file.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        local_path = os.path.join(images_dir, img_file)
        s3_key = f"images/{img_file}"
        hook.load_file(
            filename=local_path,
            key=s3_key,
            bucket_name=IMAGES_BUCKET,
            replace=True,
        )
        count += 1

    logger.info(f"Uploaded {count} images to s3://{IMAGES_BUCKET}/images/")
    return count


def archive_zip(key: str):
    """Move ZIP from incoming/ to archived/ in MinIO."""
    hook = S3Hook(aws_conn_id=MINIO_CONN_ID)
    archived_key = key.replace("incoming/", "archived/")

    hook.copy_object(
        source_bucket_name=LANDING_BUCKET,
        source_bucket_key=key,
        dest_bucket_name=LANDING_BUCKET,
        dest_bucket_key=archived_key,
    )
    hook.delete_objects(bucket=LANDING_BUCKET, keys=[key])
    logger.info(f"Archived {key} → {archived_key}")


def cleanup_tmp(zip_path: str):
    """Remove temporary files."""
    extract_dir = zip_path.replace(".zip", "")
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    if os.path.exists(zip_path):
        os.remove(zip_path)
    logger.info("Temporary files cleaned up")


# Main ingestion
def run_ingestion(**context) -> dict:
    """
    Full ingestion pipeline:
        MinIO (landing/incoming/*.zip) → unzip → raw_products + MinIO images
    """
    zip_keys = list_new_zips()
    if not zip_keys:
        logger.info("No new ZIP files found")
        return {"batch_id": None, "rows": 0, "images": 0}

    results = []

    for key in zip_keys:
        batch_id = os.path.basename(key).replace(".zip", "")
        logger.info(f"Processing batch: {batch_id}")

        # Download + Unzip
        zip_path = download_zip(key)
        extract_dir = unzip_file(zip_path)

        # Load CSV → raw_products
        n_rows = load_csv_to_raw(extract_dir, batch_id)

        # Upload images → MinIO
        n_images = upload_images_to_minio(extract_dir, batch_id)

        # Archive ZIP
        archive_zip(key)

        # Cleanup
        cleanup_tmp(zip_path)

        results.append(
            {
                "batch_id": batch_id,
                "rows": n_rows,
                "images": n_images,
            }
        )

    # Push last batch_id to XCom
    last_batch = results[-1]["batch_id"]
    context["ti"].xcom_push(key="batch_id", value=last_batch)
    context["ti"].xcom_push(key="ingestion_results", value=results)

    logger.info(f"Ingestion complete: {len(results)} batch(es) processed")
    return results

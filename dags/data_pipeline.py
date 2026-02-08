"""
Rakuten MLOps Pipeline DAG

Flow:
    sensor (MinIO) → ingest (unzip + raw_products)
        → transform (clean_text + processed_products)
            → export (processed_products → CSV)
                → dvc_snapshot (exec dans container rakuten_dvc)

Trigger: S3KeySensor détecte un ZIP dans MinIO landing/incoming/
"""

import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor

sys.path.insert(0, "/opt/airflow/src")

from export.export import run_export
from ingestion.ingest import run_ingestion
from transformation.transform import run_transformation


def run_dvc_snapshot(**context):
    """Execute DVC snapshot in rakuten_dvc container via Docker SDK."""
    import logging

    import docker

    logger = logging.getLogger(__name__)

    client = docker.from_env()
    container = client.containers.get("rakuten_dvc")

    exit_code, output = container.exec_run(
        "bash /workspace/scripts/dvc_snapshot.sh",
        workdir="/workspace",
    )

    log_output = output.decode("utf-8")
    logger.info(f"DVC snapshot output:\n{log_output}")

    if exit_code != 0:
        raise Exception(f"DVC snapshot failed (exit code {exit_code}):\n{log_output}")

    return {"status": "success", "output": log_output}


# DAG Configuration

default_args = {
    "owner": "rakuten_mlops",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="rakuten_data_pipeline",
    default_args=default_args,
    description="Pipeline MLOps: MinIO → PostgreSQL → DVC",
    schedule_interval=timedelta(hours=1),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["rakuten", "mlops", "ingestion"],
) as dag:
    # Sensor: detect new ZIP in MinIO
    sensor = S3KeySensor(
        task_id="sensor_new_zip",
        bucket_name="landing",
        bucket_key="incoming/*.zip",
        wildcard_match=True,
        aws_conn_id="minio_s3",
        poke_interval=120,
        timeout=3600,
        mode="reschedule",
    )

    # Ingest: download ZIP, unzip, load raw_products, upload images
    ingest = PythonOperator(
        task_id="ingest",
        python_callable=run_ingestion,
    )

    # Transform: clean_text → processed_products
    transform = PythonOperator(
        task_id="transform",
        python_callable=run_transformation,
    )

    # Export: processed_products → CSV
    export = PythonOperator(
        task_id="export_processed",
        python_callable=run_export,
    )

    # DVC: version data + push to MinIO
    dvc_snapshot = PythonOperator(
        task_id="dvc_snapshot",
        python_callable=run_dvc_snapshot,
    )

    # Orchestration
    sensor >> ingest >> transform >> export >> dvc_snapshot

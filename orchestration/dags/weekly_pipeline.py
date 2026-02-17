"""
Weekly ML Pipeline DAG

Orchestrates the complete weekly ML pipeline:
  1. Check current data state
  2. Load next 3% data increment
  3. Validate data integrity
  4. Train model (generate balanced dataset + TF-IDF/LogReg)
  5. Promote model if F1 > threshold and better than current production
  6. Log pipeline summary

Schedule: Every Monday at 2:00 AM (configurable via AIRFLOW_SCHEDULE env var)
"""
from datetime import timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import sys
import os

sys.path.insert(0, "/opt/airflow")

# =============================================================================
# DAG Configuration
# =============================================================================
default_args = {
    "owner": "rakuten_mlops",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

SCHEDULE = os.getenv("AIRFLOW_SCHEDULE", "0 2 * * 1")


# =============================================================================
# Task Functions
# =============================================================================
def check_current_state(**context):
    """Check current data loading state and push info to XCom."""
    from src.data.loader import get_current_state, calculate_next_percentage
    from src.config import PIPELINE_CONFIG

    state = get_current_state()
    current_pct = state["current_percentage"]
    next_pct = calculate_next_percentage(current_pct)
    max_pct = PIPELINE_CONFIG["max_percentage"]

    print(f"Current: {current_pct}%, Next target: {next_pct}%, Max: {max_pct}%")

    context["ti"].xcom_push(key="current_percentage", value=current_pct)
    context["ti"].xcom_push(key="next_percentage", value=next_pct)
    context["ti"].xcom_push(key="at_maximum", value=current_pct >= max_pct)

    if current_pct >= max_pct:
        print(f"Already at maximum ({max_pct}%), pipeline will skip loading")


def load_data(**context):
    """Load next data increment (+3%) into PostgreSQL."""
    from src.data.loader import load_incremental_data

    at_max = context["ti"].xcom_pull(key="at_maximum", task_ids="check_state")
    if at_max:
        print("Skipping load: already at maximum percentage")
        return

    next_pct = context["ti"].xcom_pull(
        key="next_percentage", task_ids="check_state"
    )

    print(f"Loading data to {next_pct}%...")
    success = load_incremental_data(target_percentage=next_pct)

    if not success:
        raise RuntimeError(f"Failed to load data to {next_pct}%")

    print(f"Data loaded successfully to {next_pct}%")


def validate_load(**context):
    """Validate that the data load completed correctly."""
    import psycopg2
    from src.config import POSTGRES_CONFIG

    at_max = context["ti"].xcom_pull(key="at_maximum", task_ids="check_state")
    if at_max:
        print("Skipping validation: no new data loaded")
        return

    next_pct = context["ti"].xcom_pull(
        key="next_percentage", task_ids="check_state"
    )

    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM labels")
        labels_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT percentage, status
            FROM data_loads
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 1
            """
        )
        result = cursor.fetchone()

        if result is None:
            raise RuntimeError("No completed data load found after loading")

        loaded_pct, status = result

        if products_count != labels_count:
            raise RuntimeError(
                f"Products/labels mismatch: {products_count} vs {labels_count}"
            )

        print(
            f"Validation passed: {products_count} products, "
            f"loaded to {loaded_pct}%"
        )
    finally:
        cursor.close()
        conn.close()


def auto_train(**context):
    """Generate balanced dataset and train model."""
    from src.models.auto_trainer import AutoTrainer

    trainer = AutoTrainer()
    result = trainer.run()

    context["ti"].xcom_push(key="run_id", value=result["run_id"])
    context["ti"].xcom_push(key="dataset_run_id", value=result["dataset_run_id"])
    context["ti"].xcom_push(key="model_version", value=result["model_version"])
    context["ti"].xcom_push(key="f1_score", value=result["f1_score"])
    context["ti"].xcom_push(key="accuracy", value=result["accuracy"])
    context["ti"].xcom_push(key="week_number", value=result["week_number"])

    print(
        f"Model trained: v{result['model_version']}, "
        f"F1={result['f1_score']:.4f}, "
        f"Accuracy={result['accuracy']:.4f}"
    )


def auto_promote(**context):
    """Evaluate model and promote to production if criteria are met."""
    from src.models.promotion_engine import PromotionEngine

    run_id = context["ti"].xcom_pull(key="run_id", task_ids="auto_train")
    model_version = context["ti"].xcom_pull(
        key="model_version", task_ids="auto_train"
    )
    f1_score = context["ti"].xcom_pull(key="f1_score", task_ids="auto_train")

    engine = PromotionEngine()
    result = engine.evaluate_and_promote(
        model_version=model_version,
        f1_score=f1_score,
        run_id=run_id,
    )

    context["ti"].xcom_push(key="promoted", value=result["promoted"])
    context["ti"].xcom_push(
        key="promotion_reason", value=result.get("reason", "")
    )

    status = "PROMOTED" if result["promoted"] else "ARCHIVED"
    print(f"Promotion decision: {status} - {result.get('reason')}")


def pipeline_summary(**context):
    """Log the complete pipeline execution summary."""
    ti = context["ti"]

    current_pct = ti.xcom_pull(key="current_percentage", task_ids="check_state")
    next_pct = ti.xcom_pull(key="next_percentage", task_ids="check_state")
    at_max = ti.xcom_pull(key="at_maximum", task_ids="check_state")

    print("=" * 80)
    print("WEEKLY ML PIPELINE - EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Execution date : {context['ds']}")
    print(f"Data percentage: {current_pct}% -> {next_pct}%")

    if not at_max:
        f1 = ti.xcom_pull(key="f1_score", task_ids="auto_train")
        accuracy = ti.xcom_pull(key="accuracy", task_ids="auto_train")
        version = ti.xcom_pull(key="model_version", task_ids="auto_train")
        run_id = ti.xcom_pull(key="run_id", task_ids="auto_train")
        promoted = ti.xcom_pull(key="promoted", task_ids="auto_promote")
        reason = ti.xcom_pull(
            key="promotion_reason", task_ids="auto_promote"
        )

        print(f"Model version  : v{version}")
        print(f"MLflow run ID  : {run_id}")
        print(f"F1 (weighted)  : {f1:.4f}")
        print(f"Accuracy       : {accuracy:.4f}")
        print(
            f"Promotion      : {'YES' if promoted else 'NO'} - {reason}"
        )
    else:
        print("Status         : No new data loaded (at maximum)")

    print("=" * 80)


# =============================================================================
# DAG Definition
# =============================================================================
with DAG(
    dag_id="weekly_ml_pipeline",
    default_args=default_args,
    description="Weekly: Load data -> Train model -> Promote if better",
    schedule_interval=SCHEDULE,
    start_date=days_ago(1),
    catchup=False,
    tags=["ml", "rakuten", "weekly", "auto"],
) as dag:

    t_check = PythonOperator(
        task_id="check_state",
        python_callable=check_current_state,
    )

    t_load = PythonOperator(
        task_id="load_data",
        python_callable=load_data,
    )

    t_validate = PythonOperator(
        task_id="validate_load",
        python_callable=validate_load,
    )

    t_train = PythonOperator(
        task_id="auto_train",
        python_callable=auto_train,
    )

    t_promote = PythonOperator(
        task_id="auto_promote",
        python_callable=auto_promote,
    )

    t_summary = PythonOperator(
        task_id="pipeline_summary",
        python_callable=pipeline_summary,
    )

    # Pipeline flow
    t_check >> t_load >> t_validate >> t_train >> t_promote >> t_summary

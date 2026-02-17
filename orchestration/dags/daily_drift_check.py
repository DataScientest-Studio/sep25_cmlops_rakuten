"""
Daily Drift Check DAG

Runs drift detection daily on production inference logs.

Pipeline:
  1. Load inference log
  2. Run statistical drift analysis
  3. Classify severity (OK / WARNING / ALERT / CRITICAL)
  4. Save report to PostgreSQL drift_reports table
  5. Log summary

Schedule: Every day at 1:00 AM (configurable via DRIFT_CHECK_SCHEDULE env var)
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
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

SCHEDULE = os.getenv("DRIFT_CHECK_SCHEDULE", "0 1 * * *")


# =============================================================================
# Task Functions
# =============================================================================
def check_inference_log(**context):
    """Verify inference log exists and has data."""
    from pathlib import Path

    log_path = os.getenv(
        "INFERENCE_LOG_PATH", "/opt/airflow/data/monitoring/inference_log.csv"
    )

    path = Path(log_path)
    if not path.exists():
        print(f"Inference log not found at {log_path}")
        context["ti"].xcom_push(key="has_data", value=False)
        context["ti"].xcom_push(key="sample_count", value=0)
        return

    import pandas as pd

    df = pd.read_csv(log_path)
    sample_count = len(df)
    has_data = sample_count >= 10

    print(f"Inference log: {sample_count} samples (sufficient: {has_data})")
    context["ti"].xcom_push(key="has_data", value=has_data)
    context["ti"].xcom_push(key="sample_count", value=sample_count)


def run_drift_analysis(**context):
    """Run the full drift analysis."""
    has_data = context["ti"].xcom_pull(key="has_data", task_ids="check_log")
    if not has_data:
        print("Skipping: insufficient data for drift analysis")
        context["ti"].xcom_push(key="severity", value="SKIPPED")
        context["ti"].xcom_push(key="drift_detected", value=False)
        context["ti"].xcom_push(key="overall_score", value=0.0)
        return

    from src.monitoring.drift_monitor import DriftMonitor

    monitor = DriftMonitor(
        inference_log_path=os.getenv(
            "INFERENCE_LOG_PATH",
            "/opt/airflow/data/monitoring/inference_log.csv",
        ),
    )

    report = monitor.run_drift_analysis()

    context["ti"].xcom_push(key="severity", value=report.get("severity", "OK"))
    context["ti"].xcom_push(
        key="drift_detected", value=report.get("drift_detected", False)
    )
    context["ti"].xcom_push(
        key="overall_score", value=report.get("overall_drift_score", 0.0)
    )
    context["ti"].xcom_push(
        key="data_drift", value=report.get("data_drift_score", 0.0)
    )
    context["ti"].xcom_push(
        key="pred_drift", value=report.get("prediction_drift_score", 0.0)
    )
    context["ti"].xcom_push(key="status", value=report.get("status", "error"))

    print(
        f"Analysis complete: severity={report.get('severity')}, "
        f"score={report.get('overall_drift_score', 0):.4f}"
    )


def process_alerts(**context):
    """Create alert if drift severity warrants it."""
    severity = context["ti"].xcom_pull(key="severity", task_ids="run_analysis")
    status = context["ti"].xcom_pull(key="status", task_ids="run_analysis")

    if severity == "SKIPPED" or status != "completed":
        print("Skipping alerting: no drift analysis was run")
        return

    from src.monitoring.alerting import AlertManager

    manager = AlertManager()

    report = {
        "severity": severity,
        "overall_drift_score": context["ti"].xcom_pull(
            key="overall_score", task_ids="run_analysis"
        ),
        "data_drift_score": context["ti"].xcom_pull(
            key="data_drift", task_ids="run_analysis"
        ),
        "prediction_drift_score": context["ti"].xcom_pull(
            key="pred_drift", task_ids="run_analysis"
        ),
    }

    alert = manager.process_drift_report(report)

    if alert:
        print(f"Alert created: severity={severity}, id={alert.get('id')}")
        context["ti"].xcom_push(key="alert_created", value=True)
        context["ti"].xcom_push(key="alert_id", value=alert.get("id"))
    else:
        print("No alert created (severity OK)")
        context["ti"].xcom_push(key="alert_created", value=False)


def drift_summary(**context):
    """Log drift check summary."""
    ti = context["ti"]

    severity = ti.xcom_pull(key="severity", task_ids="run_analysis")
    drift_detected = ti.xcom_pull(key="drift_detected", task_ids="run_analysis")
    overall_score = ti.xcom_pull(key="overall_score", task_ids="run_analysis")
    sample_count = ti.xcom_pull(key="sample_count", task_ids="check_log")
    alert_created = ti.xcom_pull(key="alert_created", task_ids="process_alerts")

    print("=" * 80)
    print("DAILY DRIFT CHECK - SUMMARY")
    print("=" * 80)
    print(f"Date            : {context['ds']}")
    print(f"Samples analysed: {sample_count}")
    print(f"Overall score   : {overall_score:.4f}")
    print(f"Severity        : {severity}")
    print(f"Drift detected  : {drift_detected}")
    print(f"Alert created   : {alert_created}")

    if severity in ("ALERT", "CRITICAL"):
        print("")
        print("ACTION REQUIRED: Drift detected above alert threshold.")
        print("  -> Check Grafana drift dashboard")
        print("  -> Check Streamlit monitoring page for alert actions")
        print("  -> Or run: make trigger-auto-train")

    print("=" * 80)


# =============================================================================
# DAG Definition
# =============================================================================
with DAG(
    dag_id="daily_drift_check",
    default_args=default_args,
    description="Daily: Analyse inference logs for data & prediction drift",
    schedule_interval=SCHEDULE,
    start_date=days_ago(1),
    catchup=False,
    tags=["monitoring", "drift", "rakuten", "daily"],
) as dag:

    t_check_log = PythonOperator(
        task_id="check_log",
        python_callable=check_inference_log,
    )

    t_analysis = PythonOperator(
        task_id="run_analysis",
        python_callable=run_drift_analysis,
    )

    t_alerts = PythonOperator(
        task_id="process_alerts",
        python_callable=process_alerts,
    )

    t_summary = PythonOperator(
        task_id="drift_summary",
        python_callable=drift_summary,
    )

    t_check_log >> t_analysis >> t_alerts >> t_summary

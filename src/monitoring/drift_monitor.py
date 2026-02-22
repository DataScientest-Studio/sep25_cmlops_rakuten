"""
Drift Monitor Module

Orchestrates drift detection by combining:
  - Statistical tests (PSI, KS, Chi-Square) on inference logs
  - Evidently reports (when available)
  - Persistence of drift reports to PostgreSQL

Designed to be run daily by the Airflow daily_drift_check DAG
or manually via `scripts/check_drift.py`.
"""
import sys
from pathlib import Path
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import Json

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.monitoring.statistical_tests import compute_drift_scores
from src.monitoring import thresholds

logger = logging.getLogger(__name__)

# Inference log path (inside API container it's /app/data/monitoring/,
# from host or Airflow it's ./data/monitoring/)
DEFAULT_INFERENCE_LOG = os.getenv(
    "INFERENCE_LOG_PATH", "./data/monitoring/inference_log.csv"
)


class DriftMonitor:
    """
    Monitors model drift by analysing inference logs.

    Computes drift scores using statistical tests, optionally runs Evidently,
    saves drift reports to PostgreSQL, and returns structured results.
    """

    def __init__(
        self,
        inference_log_path: str = None,
        postgres_config: dict = None,
        reference_window_days: int = 30,
        current_window_days: int = 7,
    ):
        self.inference_log_path = inference_log_path or DEFAULT_INFERENCE_LOG
        self.reference_window_days = reference_window_days
        self.current_window_days = current_window_days

        if postgres_config is None:
            self.postgres_config = {
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": int(os.getenv("POSTGRES_PORT", "5432")),
                "database": os.getenv("POSTGRES_DB", "rakuten_db"),
                "user": os.getenv("POSTGRES_USER", "rakuten_user"),
                "password": os.getenv("POSTGRES_PASSWORD", "rakuten_pass"),
            }
        else:
            self.postgres_config = postgres_config

    # -----------------------------------------------------------------
    # Data loading
    # -----------------------------------------------------------------
    def _load_inference_log(self) -> Optional[pd.DataFrame]:
        """Load inference log CSV into a DataFrame."""
        path = Path(self.inference_log_path)
        if not path.exists():
            logger.warning(f"Inference log not found: {path}")
            return None

        try:
            df = pd.read_csv(path)
            if len(df) == 0:
                logger.warning("Inference log is empty")
                return None

            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["timestamp"])
            return df
        except Exception as e:
            logger.error(f"Failed to read inference log: {e}")
            return None

    def _split_windows(
        self, df: pd.DataFrame
    ) -> tuple:
        """
        Split inference data into reference and current windows.

        Primary strategy (time-based):
            Reference window: [now - reference_window_days, now - current_window_days)
            Current window:   [now - current_window_days, now]

        Fallback (proportional, for cold-start):
            When the time-based reference window has fewer than 30 samples but
            total data is sufficient, use first 60 % of records as reference
            and last 40 % as current.  This lets drift analysis run even when
            the system has been deployed for less than reference_window_days.

        Returns:
            (reference_df, current_df)
        """
        now = pd.Timestamp.now(tz="UTC") if df["timestamp"].dt.tz else pd.Timestamp.now()

        current_start = now - timedelta(days=self.current_window_days)
        reference_start = now - timedelta(days=self.reference_window_days)

        reference_df = df[
            (df["timestamp"] >= reference_start) & (df["timestamp"] < current_start)
        ].copy()
        current_df = df[df["timestamp"] >= current_start].copy()

        # -- Fallback: random split for cold-start scenarios --
        # A chronological split would create artificial drift when older
        # and newer predictions happen to have different characteristics
        # (e.g. early testing vs. diverse production traffic). A random
        # split keeps both halves representative of the same distribution.
        min_ref = 30
        min_cur = 10
        if len(reference_df) < min_ref and len(df) >= (min_ref + min_cur):
            logger.warning(
                f"Time-based reference window too small ({len(reference_df)} samples). "
                f"Falling back to random split on {len(df)} total samples."
            )
            df_shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)
            split_idx = int(len(df_shuffled) * 0.6)
            reference_df = df_shuffled.iloc[:split_idx].copy()
            current_df = df_shuffled.iloc[split_idx:].copy()

        logger.info(
            f"Windows: reference={len(reference_df)} samples "
            f"({self.reference_window_days}d), "
            f"current={len(current_df)} samples ({self.current_window_days}d)"
        )

        return reference_df, current_df

    # -----------------------------------------------------------------
    # Core analysis
    # -----------------------------------------------------------------
    def run_drift_analysis(self) -> Dict:
        """
        Run the full drift analysis pipeline.

        Steps:
          1. Load inference log
          2. Split into reference / current windows
          3. Run statistical tests
          4. Classify drift severity (OK / WARNING / ALERT / CRITICAL)
          5. Save report to PostgreSQL

        Returns:
            dict with drift scores, severity, and details
        """
        logger.info("=" * 80)
        logger.info("DRIFT MONITOR: Starting drift analysis")
        logger.info("=" * 80)

        # Load data
        df = self._load_inference_log()
        if df is None:
            report = self._build_report(
                status="error", message="No inference log available"
            )
            self._save_report_to_db(report)
            return report

        # Check minimum samples
        if len(df) < thresholds.MIN_SAMPLES_FOR_DRIFT:
            report = self._build_report(
                status="insufficient_data",
                message=f"Only {len(df)} samples, need {thresholds.MIN_SAMPLES_FOR_DRIFT}",
                total_samples=len(df),
            )
            self._save_report_to_db(report)
            return report

        # Split into windows
        reference_df, current_df = self._split_windows(df)

        if len(reference_df) < 30:
            report = self._build_report(
                status="insufficient_data",
                message=f"Reference window has only {len(reference_df)} samples (need >= 30)",
                total_samples=len(df),
            )
            self._save_report_to_db(report)
            return report

        if len(current_df) < 10:
            report = self._build_report(
                status="insufficient_data",
                message=f"Current window has only {len(current_df)} samples (need >= 10)",
                total_samples=len(df),
            )
            self._save_report_to_db(report)
            return report

        # Run statistical tests
        logger.info("Running statistical tests...")
        drift_scores = compute_drift_scores(reference_df, current_df)

        # Compute summary metrics
        data_drift_score = drift_scores.get("data_drift", {}).get("psi", 0.0)
        prediction_drift_score = drift_scores.get("prediction_drift", {}).get("psi", 0.0)
        confidence_drift = drift_scores.get("confidence_drift", {})
        confidence_mean_delta = abs(confidence_drift.get("mean_delta", 0.0))
        overall_score = drift_scores.get("overall_drift_score", 0.0)

        # Classify severity
        severity = self._classify_severity(overall_score)

        # Build report
        report = self._build_report(
            status="completed",
            data_drift_score=data_drift_score,
            prediction_drift_score=prediction_drift_score,
            performance_drift_score=confidence_mean_delta,
            overall_drift_score=overall_score,
            drift_detected=drift_scores.get("drift_detected", False),
            severity=severity,
            reference_samples=len(reference_df),
            current_samples=len(current_df),
            total_samples=len(df),
            details=drift_scores,
        )

        # Save to PostgreSQL
        self._save_report_to_db(report)

        logger.info("=" * 80)
        logger.info(f"DRIFT MONITOR: Analysis complete")
        logger.info(f"   Overall score: {overall_score:.4f}")
        logger.info(f"   Severity:      {severity}")
        logger.info(f"   Data drift:    {data_drift_score:.4f}")
        logger.info(f"   Pred drift:    {prediction_drift_score:.4f}")
        logger.info("=" * 80)

        return report

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def _classify_severity(self, score: float) -> str:
        """
        Classify drift severity based on configured thresholds.

        Returns one of: OK, WARNING, ALERT, CRITICAL
        """
        warning_t = float(os.getenv("DRIFT_WARNING_THRESHOLD", "0.1"))
        alert_t = float(os.getenv("DRIFT_ALERT_THRESHOLD", "0.2"))
        critical_t = float(os.getenv("DRIFT_CRITICAL_THRESHOLD", "0.3"))

        if score >= critical_t:
            return "CRITICAL"
        elif score >= alert_t:
            return "ALERT"
        elif score >= warning_t:
            return "WARNING"
        return "OK"

    def _build_report(self, status: str, **kwargs) -> Dict:
        """Build a standardized drift report dict."""
        report = {
            "report_date": datetime.now().isoformat(),
            "status": status,
            "data_drift_score": kwargs.get("data_drift_score", 0.0),
            "prediction_drift_score": kwargs.get("prediction_drift_score", 0.0),
            "performance_drift_score": kwargs.get("performance_drift_score", 0.0),
            "overall_drift_score": kwargs.get("overall_drift_score", 0.0),
            "drift_detected": kwargs.get("drift_detected", False),
            "severity": kwargs.get("severity", "OK"),
            "reference_samples": kwargs.get("reference_samples", 0),
            "current_samples": kwargs.get("current_samples", 0),
            "total_samples": kwargs.get("total_samples", 0),
            "message": kwargs.get("message"),
            "details": kwargs.get("details"),
        }
        return report

    # -----------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------
    def _save_report_to_db(self, report: Dict):
        """Save drift report to PostgreSQL drift_reports table."""
        try:
            conn = psycopg2.connect(**self.postgres_config)
            cursor = conn.cursor()

            # Ensure table exists (idempotent)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drift_reports (
                    id SERIAL PRIMARY KEY,
                    report_date TIMESTAMP NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    data_drift_score FLOAT,
                    prediction_drift_score FLOAT,
                    performance_drift_score FLOAT,
                    overall_drift_score FLOAT,
                    drift_detected BOOLEAN,
                    severity VARCHAR(20),
                    reference_samples INTEGER,
                    current_samples INTEGER,
                    details JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Serialise details for JSONB (convert numpy types)
            details_json = json.loads(
                json.dumps(report.get("details"), default=_json_default)
            ) if report.get("details") else None

            cursor.execute(
                """
                INSERT INTO drift_reports
                    (report_date, status, data_drift_score, prediction_drift_score,
                     performance_drift_score, overall_drift_score, drift_detected,
                     severity, reference_samples, current_samples, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    datetime.now(),
                    report["status"],
                    report["data_drift_score"],
                    report["prediction_drift_score"],
                    report["performance_drift_score"],
                    report["overall_drift_score"],
                    report["drift_detected"],
                    report["severity"],
                    report["reference_samples"],
                    report["current_samples"],
                    Json(details_json),
                ),
            )

            conn.commit()
            logger.info("Drift report saved to PostgreSQL")

        except Exception as e:
            logger.error(f"Failed to save drift report to DB: {e}")
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    def get_recent_reports(self, limit: int = 30) -> pd.DataFrame:
        """Retrieve recent drift reports from PostgreSQL."""
        try:
            conn = psycopg2.connect(**self.postgres_config)
            df = pd.read_sql_query(
                """
                SELECT id, report_date, status, data_drift_score,
                       prediction_drift_score, performance_drift_score,
                       overall_drift_score, drift_detected, severity,
                       reference_samples, current_samples, created_at
                FROM drift_reports
                ORDER BY report_date DESC
                LIMIT %s
                """,
                conn,
                params=(limit,),
            )
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Failed to read drift reports: {e}")
            return pd.DataFrame()


def _json_default(obj):
    """JSON serialiser for numpy types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return str(obj)

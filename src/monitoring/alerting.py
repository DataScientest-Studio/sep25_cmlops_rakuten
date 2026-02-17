"""
Alerting Module

Processes drift reports and manages alerts:
  - Evaluates drift severity against thresholds
  - Persists alerts to PostgreSQL
  - Provides query interface for active/historical alerts

Severity levels:
  - OK       : score < 0.1  (no alert created)
  - WARNING  : score >= 0.1 (logged, alert created)
  - ALERT    : score >= 0.2 (alert created, action recommended)
  - CRITICAL : score >= 0.3 (alert created, retrain recommended)
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor, Json

logger = logging.getLogger(__name__)


def _get_postgres_config() -> dict:
    """Build PostgreSQL connection config from environment."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "rakuten_db"),
        "user": os.getenv("POSTGRES_USER", "rakuten_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "rakuten_pass"),
    }


class AlertManager:
    """
    Manages drift alerts lifecycle: creation, querying, and acknowledgement.
    """

    def __init__(self, postgres_config: dict = None):
        self.pg_config = postgres_config or _get_postgres_config()

    # -----------------------------------------------------------------
    # Alert creation
    # -----------------------------------------------------------------
    def process_drift_report(self, report: Dict) -> Optional[Dict]:
        """
        Process a drift report and create an alert if severity >= WARNING.

        Args:
            report: Drift report from DriftMonitor.run_drift_analysis()

        Returns:
            Alert dict if created, None if severity is OK
        """
        severity = report.get("severity", "OK")

        if severity == "OK":
            logger.info("Drift severity OK - no alert created")
            return None

        logger.info(f"Creating alert: severity={severity}")

        alert = {
            "severity": severity,
            "drift_score": report.get("overall_drift_score", 0.0),
            "data_drift_score": report.get("data_drift_score", 0.0),
            "prediction_drift_score": report.get("prediction_drift_score", 0.0),
            "message": self._build_message(report),
            "recommended_action": self._recommend_action(severity),
            "details": report.get("details"),
        }

        alert_id = self._save_alert(alert, report)
        alert["id"] = alert_id

        logger.info(
            f"Alert #{alert_id} created: {severity} "
            f"(score={report.get('overall_drift_score', 0):.4f})"
        )

        return alert

    def _build_message(self, report: Dict) -> str:
        """Build a human-readable alert message."""
        severity = report.get("severity", "UNKNOWN")
        score = report.get("overall_drift_score", 0.0)
        data_d = report.get("data_drift_score", 0.0)
        pred_d = report.get("prediction_drift_score", 0.0)

        return (
            f"[{severity}] Drift detected (overall={score:.4f}). "
            f"Data drift PSI={data_d:.4f}, Prediction drift PSI={pred_d:.4f}."
        )

    def _recommend_action(self, severity: str) -> str:
        """Suggest an action based on severity level."""
        actions = {
            "WARNING": "Monitor closely. No immediate action required.",
            "ALERT": "Investigate drift sources. Consider retraining.",
            "CRITICAL": "Retrain model or rollback to previous version.",
        }
        return actions.get(severity, "No action.")

    def _save_alert(self, alert: Dict, report: Dict) -> Optional[int]:
        """Save alert to drift_reports + return the report id."""
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()

            # The drift report should already be saved by DriftMonitor.
            # Fetch the latest report id to link actions later.
            cursor.execute(
                """
                SELECT id FROM drift_reports
                ORDER BY created_at DESC LIMIT 1
                """
            )
            row = cursor.fetchone()
            alert_id = row[0] if row else None

            conn.close()
            return alert_id

        except Exception as e:
            logger.error(f"Failed to save alert: {e}")
            return None

    # -----------------------------------------------------------------
    # Alert queries
    # -----------------------------------------------------------------
    def get_active_alerts(self, limit: int = 20) -> List[Dict]:
        """
        Get recent drift reports that are WARNING or higher
        and have not been acknowledged yet.
        """
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                SELECT dr.id, dr.report_date, dr.status, dr.severity,
                       dr.overall_drift_score, dr.data_drift_score,
                       dr.prediction_drift_score, dr.drift_detected,
                       dr.reference_samples, dr.current_samples,
                       dr.created_at,
                       CASE WHEN aa.id IS NOT NULL THEN true ELSE false END AS acknowledged
                FROM drift_reports dr
                LEFT JOIN alert_actions aa ON aa.drift_report_id = dr.id
                WHERE dr.severity IN ('WARNING', 'ALERT', 'CRITICAL')
                ORDER BY dr.report_date DESC
                LIMIT %s
                """,
                (limit,),
            )

            alerts = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return alerts

        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []

    def get_all_alerts(self, limit: int = 50) -> List[Dict]:
        """Get all drift reports (including OK) for history view."""
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                SELECT dr.id, dr.report_date, dr.status, dr.severity,
                       dr.overall_drift_score, dr.data_drift_score,
                       dr.prediction_drift_score, dr.performance_drift_score,
                       dr.drift_detected, dr.reference_samples,
                       dr.current_samples, dr.created_at
                FROM drift_reports dr
                ORDER BY dr.report_date DESC
                LIMIT %s
                """,
                (limit,),
            )

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get alert history: {e}")
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # -----------------------------------------------------------------
    # Alert actions
    # -----------------------------------------------------------------
    def acknowledge_alert(
        self,
        drift_report_id: int,
        action_type: str,
        details: dict = None,
        performed_by: str = "user",
    ) -> bool:
        """
        Record a human action on a drift alert.

        Args:
            drift_report_id: ID from drift_reports table
            action_type: One of: acknowledge, retrain, rollback, investigate, adjust_thresholds
            details: Additional context (JSON)
            performed_by: User or system identifier

        Returns:
            True if saved successfully
        """
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO alert_actions
                    (drift_report_id, action_type, action_details, performed_by)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    drift_report_id,
                    action_type,
                    Json(details) if details else None,
                    performed_by,
                ),
            )

            conn.commit()
            conn.close()

            logger.info(
                f"Alert #{drift_report_id} acknowledged: "
                f"action={action_type}, by={performed_by}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False

    def get_action_history(self, limit: int = 50) -> List[Dict]:
        """Get history of actions taken on alerts."""
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                SELECT aa.id, aa.drift_report_id, aa.action_type,
                       aa.action_details, aa.performed_by, aa.created_at,
                       dr.severity, dr.overall_drift_score
                FROM alert_actions aa
                JOIN drift_reports dr ON dr.id = aa.drift_report_id
                ORDER BY aa.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get action history: {e}")
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass

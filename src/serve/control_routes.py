"""
FastAPI Control Routes

Provides endpoints for human-in-the-loop actions:
  - GET  /api/alerts              - List drift alerts
  - POST /api/alerts/{id}/acknowledge - Acknowledge an alert
  - POST /api/trigger-retrain     - Force model retraining
  - POST /api/rollback-model      - Rollback to previous model version
  - GET  /api/drift-reports       - List drift reports
  - GET  /api/action-history      - List actions taken on alerts
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime

import config

logger = logging.getLogger(__name__)

control_router = APIRouter(prefix="/api", tags=["Control"])


# =========================================================================
# Pydantic models
# =========================================================================
class AcknowledgeRequest(BaseModel):
    action_type: str = Field(
        ...,
        description="Action taken: acknowledge, retrain, rollback, investigate, adjust_thresholds",
    )
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional context for the action"
    )
    performed_by: str = Field(
        "user", description="Who performed the action"
    )


class TriggerRetrainResponse(BaseModel):
    status: str
    message: str
    run_id: Optional[str] = None


class RollbackResponse(BaseModel):
    status: str
    message: str
    rolled_back_to: Optional[int] = None


# =========================================================================
# Helper
# =========================================================================
def _get_db_conn():
    """Get a PostgreSQL connection using API config."""
    return psycopg2.connect(
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        database=config.POSTGRES_DB,
        user=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
    )


# =========================================================================
# Alert endpoints
# =========================================================================
@control_router.get("/alerts", summary="List drift alerts")
async def list_alerts(limit: int = 20):
    """Return recent drift alerts (severity >= WARNING)."""
    try:
        conn = _get_db_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT dr.id, dr.report_date, dr.status, dr.severity,
                   dr.overall_drift_score, dr.data_drift_score,
                   dr.prediction_drift_score, dr.drift_detected,
                   dr.reference_samples, dr.current_samples,
                   dr.created_at,
                   CASE WHEN aa.id IS NOT NULL THEN true ELSE false END AS acknowledged,
                   aa.action_type AS action_taken
            FROM drift_reports dr
            LEFT JOIN alert_actions aa ON aa.drift_report_id = dr.id
            WHERE dr.severity IN ('WARNING', 'ALERT', 'CRITICAL')
            ORDER BY dr.report_date DESC
            LIMIT %s
            """,
            (limit,),
        )
        alerts = []
        for row in cursor.fetchall():
            alert = dict(row)
            # Convert datetime to string for JSON
            for k, v in alert.items():
                if isinstance(v, datetime):
                    alert[k] = v.isoformat()
            alerts.append(alert)

        conn.close()
        return {"alerts": alerts, "count": len(alerts)}

    except Exception as e:
        logger.error(f"Failed to list alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@control_router.post(
    "/alerts/{alert_id}/acknowledge",
    summary="Acknowledge a drift alert",
)
async def acknowledge_alert(alert_id: int, request: AcknowledgeRequest):
    """Record a human action on a drift alert."""
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()

        # Verify the alert exists
        cursor.execute("SELECT id FROM drift_reports WHERE id = %s", (alert_id,))
        if cursor.fetchone() is None:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        cursor.execute(
            """
            INSERT INTO alert_actions
                (drift_report_id, action_type, action_details, performed_by)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                alert_id,
                request.action_type,
                Json(request.details) if request.details else None,
                request.performed_by,
            ),
        )
        action_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "action_id": action_id,
            "alert_id": alert_id,
            "action_type": request.action_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# Retrain endpoint
# =========================================================================
@control_router.post(
    "/trigger-retrain",
    response_model=TriggerRetrainResponse,
    summary="Force model retraining",
)
async def trigger_retrain():
    """
    Trigger an immediate model retraining.

    This runs the auto-trainer synchronously (fast since the model is
    TF-IDF + LogReg) and returns the new run ID.
    """
    try:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        from src.models.auto_trainer import AutoTrainer
        from src.models.promotion_engine import PromotionEngine

        logger.info("Manual retrain triggered via API")

        trainer = AutoTrainer()
        result = trainer.run()

        # Also run promotion
        engine = PromotionEngine()
        promo = engine.evaluate_and_promote(
            model_version=result["model_version"],
            f1_score=result["f1_score"],
            run_id=result["run_id"],
        )

        promoted_msg = (
            f"Model v{result['model_version']} promoted to Production"
            if promo["promoted"]
            else f"Model v{result['model_version']} archived: {promo.get('reason')}"
        )

        return TriggerRetrainResponse(
            status="success",
            message=f"Training complete. F1={result['f1_score']:.4f}. {promoted_msg}",
            run_id=result["run_id"],
        )

    except Exception as e:
        logger.error(f"Retrain failed: {e}", exc_info=True)
        return TriggerRetrainResponse(
            status="error",
            message=f"Retraining failed: {str(e)}",
        )


# =========================================================================
# Rollback endpoint
# =========================================================================
@control_router.post(
    "/rollback-model",
    response_model=RollbackResponse,
    summary="Rollback to previous production model",
)
async def rollback_model():
    """
    Rollback the model to the previous Production version.

    Archives the current Production model and promotes the most recent
    Archived version back to Production.
    """
    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
        client = MlflowClient()

        model_name = config.MODEL_NAME

        # Get current production version
        prod_versions = client.get_latest_versions(model_name, stages=["Production"])
        if not prod_versions:
            return RollbackResponse(
                status="error",
                message="No Production model found to rollback from",
            )

        current_prod = prod_versions[0]
        current_version = int(current_prod.version)

        # Get latest archived version
        archived_versions = client.get_latest_versions(
            model_name, stages=["Archived"]
        )
        if not archived_versions:
            return RollbackResponse(
                status="error",
                message="No Archived model to rollback to",
            )

        # Pick the archived version with highest version number
        target = max(archived_versions, key=lambda v: int(v.version))
        target_version = int(target.version)

        # Promote archived back to Production, archive current
        client.transition_model_version_stage(
            name=model_name,
            version=target_version,
            stage="Production",
            archive_existing_versions=True,
        )

        logger.info(
            f"Rollback: v{current_version} -> Archived, "
            f"v{target_version} -> Production"
        )

        return RollbackResponse(
            status="success",
            message=(
                f"Rolled back from v{current_version} to v{target_version}. "
                f"API will pick up the new model within "
                f"{config.MODEL_RELOAD_INTERVAL}s."
            ),
            rolled_back_to=target_version,
        )

    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        return RollbackResponse(
            status="error",
            message=f"Rollback failed: {str(e)}",
        )


# =========================================================================
# Drift reports & action history
# =========================================================================
@control_router.get("/drift-reports", summary="List drift reports")
async def list_drift_reports(limit: int = 30):
    """Return recent drift reports from the database."""
    try:
        conn = _get_db_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT id, report_date, status, severity,
                   overall_drift_score, data_drift_score,
                   prediction_drift_score, performance_drift_score,
                   drift_detected, reference_samples, current_samples,
                   created_at
            FROM drift_reports
            ORDER BY report_date DESC
            LIMIT %s
            """,
            (limit,),
        )
        reports = []
        for row in cursor.fetchall():
            r = dict(row)
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
            reports.append(r)

        conn.close()
        return {"reports": reports, "count": len(reports)}

    except Exception as e:
        logger.error(f"Failed to list drift reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@control_router.get("/action-history", summary="List alert actions")
async def list_action_history(limit: int = 50):
    """Return history of human actions taken on drift alerts."""
    try:
        conn = _get_db_conn()
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
        actions = []
        for row in cursor.fetchall():
            a = dict(row)
            for k, v in a.items():
                if isinstance(v, datetime):
                    a[k] = v.isoformat()
            actions.append(a)

        conn.close()
        return {"actions": actions, "count": len(actions)}

    except Exception as e:
        logger.error(f"Failed to list action history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

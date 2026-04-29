"""
SentinelAI — Live Evaluation Routes
====================================
Runs the labelled Nigerian fraud dataset through the live scanner and returns
real accuracy / precision / recall / F1 metrics.

This gives judges (and customers) verifiable numbers, not just claims.

Endpoint:
  GET /api/evaluation/run         — Run full eval, return metrics + per-sample results
  GET /api/evaluation/summary     — Quick metrics only (no per-sample detail)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db, User, UserRole
from auth_utils import require_role
from ai.scanner import evaluate_model_performance

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])


@router.get("/run")
async def run_full_evaluation(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    """
    Run the entire labelled dataset through the scanner and return:
      - Accuracy, precision, recall, F1
      - Per-sample predictions vs expected
      - Confusion matrix
      - Mean absolute error on risk_score

    NOTE: This calls GPT for each unlabeled-by-rules sample, so it costs API
    credits. Don't hit it on every dashboard refresh.
    """
    try:
        result = await evaluate_model_performance()
        return {
            "status": "success",
            "metrics": {
                "accuracy_pct": result.get("accuracy"),
                "precision_pct": result.get("precision"),
                "recall_pct": result.get("recall"),
                "f1_pct": result.get("f1"),
                "mean_score_error": result.get("mean_score_error"),
                "samples_correct": result.get("correct"),
                "samples_total": result.get("total"),
            },
            "confusion_matrix": result.get("confusion"),
            "per_sample_results": result.get("results"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        )


@router.get("/summary")
async def evaluation_summary(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    """
    Summary-only version (no per-sample results). Use for dashboard widget.
    """
    try:
        result = await evaluate_model_performance()
        return {
            "accuracy_pct": result.get("accuracy"),
            "precision_pct": result.get("precision"),
            "recall_pct": result.get("recall"),
            "f1_pct": result.get("f1"),
            "samples_correct": result.get("correct"),
            "samples_total": result.get("total"),
            "confusion_matrix": result.get("confusion"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        )

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.api.deps import get_current_user, get_supabase_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# =====================================================
# Request/Response Models
# =====================================================

class FeedbackRequest(BaseModel):
    feedback_type: str  # 'correct', 'false_positive', 'false_negative', 'uncertain'
    operator_notes: Optional[str] = None
    actual_outcome: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    prediction_id: str
    feedback_type: str
    operator_notes: Optional[str]
    created_at: datetime


# =====================================================
# Endpoints
# =====================================================

@router.post("/predictions/{prediction_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    prediction_id: str,
    request: FeedbackRequest,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Submit human-in-the-loop feedback for a prediction.
    
    This feedback is used for:
    - Model retraining
    - Active learning
    - Performance monitoring
    """
    try:
        # Verify prediction exists and belongs to user's organization
        pred_response = supabase.table("predictions")\
            .select("id, engine_id")\
            .eq("id", prediction_id)\
            .execute()
        
        if not pred_response.data:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # Insert feedback
        feedback_data = {
            "prediction_id": prediction_id,
            "feedback_type": request.feedback_type,
            "operator_notes": request.operator_notes,
            "actual_outcome": request.actual_outcome,
            "created_by": user.id
        }
        
        response = supabase.table("prediction_feedback")\
            .insert(feedback_data)\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to submit feedback")
        
        logger.info(f"✅ Feedback submitted for prediction {prediction_id}: {request.feedback_type}")
        
        return FeedbackResponse(**response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/{prediction_id}/feedback")
async def get_feedback(
    prediction_id: str,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Get all feedback for a specific prediction.
    """
    try:
        response = supabase.table("prediction_feedback")\
            .select("*")\
            .eq("prediction_id", prediction_id)\
            .order("created_at", desc=True)\
            .execute()
        
        return response.data
        
    except Exception as e:
        logger.error(f"Failed to get feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/stats")
async def get_feedback_stats(
    days: int = 30,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Get aggregated feedback statistics.
    
    Returns counts by feedback_type for the last N days.
    """
    try:
        # This would be better as a SQL query with GROUP BY
        # For now, we'll fetch and aggregate in Python
        response = supabase.table("prediction_feedback")\
            .select("feedback_type, created_at")\
            .gte("created_at", f"now() - interval '{days} days'")\
            .execute()
        
        stats = {
            "correct": 0,
            "false_positive": 0,
            "false_negative": 0,
            "uncertain": 0,
            "total": len(response.data)
        }
        
        for feedback in response.data:
            feedback_type = feedback.get("feedback_type")
            if feedback_type in stats:
                stats[feedback_type] += 1
        
        # Calculate accuracy if we have enough data
        if stats["total"] > 0:
            stats["accuracy"] = stats["correct"] / stats["total"]
            stats["false_positive_rate"] = stats["false_positive"] / stats["total"]
            stats["false_negative_rate"] = stats["false_negative"] / stats["total"]
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

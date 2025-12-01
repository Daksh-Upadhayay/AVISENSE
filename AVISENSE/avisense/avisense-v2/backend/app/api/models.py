from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.api.deps import get_current_user, get_supabase_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# =====================================================
# Request/Response Models
# =====================================================

class ModelRegisterRequest(BaseModel):
    model_family: str
    version: str
    artifact_url: Optional[str] = None
    framework: str
    input_shape: Optional[Dict[str, Any]] = None
    window_length: Optional[int] = None
    sequence_stride: Optional[int] = None
    metrics: Dict[str, float]
    config: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class ModelResponse(BaseModel):
    id: str
    model_family: str
    version: str
    artifact_url: Optional[str]
    framework: str
    status: str
    metrics: Dict[str, float]
    created_at: datetime
    promoted_at: Optional[datetime]


class ModelPromoteRequest(BaseModel):
    notes: Optional[str] = None


# =====================================================
# Endpoints
# =====================================================

@router.post("/models/register", response_model=ModelResponse)
async def register_model(
    request: ModelRegisterRequest,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Register a new model in the model registry.
    
    Models start in 'staging' status and must be promoted to 'production'.
    """
    try:
        model_data = {
            "model_family": request.model_family,
            "version": request.version,
            "artifact_url": request.artifact_url,
            "framework": request.framework,
            "input_shape": request.input_shape,
            "window_length": request.window_length,
            "sequence_stride": request.sequence_stride,
            "metrics": request.metrics,
            "config": request.config,
            "status": "staging",
            "created_by": user.id,
            "notes": request.notes
        }
        
        response = supabase.table("model_registry").insert(model_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to register model")
        
        logger.info(f"✅ Registered model: {request.model_family} v{request.version}")
        
        return ModelResponse(**response.data[0])
        
    except Exception as e:
        logger.error(f"Failed to register model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/active", response_model=List[ModelResponse])
async def get_active_models(
    model_family: Optional[str] = None,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Get all active (production) models.
    
    Optionally filter by model_family.
    """
    try:
        query = supabase.table("model_registry").select("*").eq("status", "production")
        
        if model_family:
            query = query.eq("model_family", model_family)
        
        response = query.execute()
        
        return [ModelResponse(**model) for model in response.data]
        
    except Exception as e:
        logger.error(f"Failed to get active models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=List[ModelResponse])
async def list_models(
    status: Optional[str] = None,
    model_family: Optional[str] = None,
    limit: int = 50,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    List all models with optional filtering.
    """
    try:
        query = supabase.table("model_registry").select("*").order("created_at", desc=True).limit(limit)
        
        if status:
            query = query.eq("status", status)
        if model_family:
            query = query.eq("model_family", model_family)
        
        response = query.execute()
        
        return [ModelResponse(**model) for model in response.data]
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_id}/promote")
async def promote_model(
    model_id: str,
    request: ModelPromoteRequest,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Promote a model from staging to production.
    
    This will:
    1. Set the model status to 'production'
    2. Deprecate the previous production model of the same family
    3. Record who promoted it and when
    """
    try:
        # Get the model to promote
        model_response = supabase.table("model_registry").select("*").eq("id", model_id).execute()
        
        if not model_response.data:
            raise HTTPException(status_code=404, detail="Model not found")
        
        model = model_response.data[0]
        
        if model["status"] == "production":
            raise HTTPException(status_code=400, detail="Model is already in production")
        
        # Deprecate current production model of same family
        supabase.table("model_registry")\
            .update({
                "status": "deprecated",
                "deprecated_at": datetime.now().isoformat()
            })\
            .eq("model_family", model["model_family"])\
            .eq("status", "production")\
            .execute()
        
        # Promote new model
        update_data = {
            "status": "production",
            "promoted_at": datetime.now().isoformat(),
            "promoted_by": user.id
        }
        
        if request.notes:
            update_data["notes"] = request.notes
        
        response = supabase.table("model_registry")\
            .update(update_data)\
            .eq("id", model_id)\
            .execute()
        
        logger.info(f"✅ Promoted model {model['model_family']} v{model['version']} to production")
        
        return {"success": True, "model": response.data[0]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to promote model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_id}/deprecate")
async def deprecate_model(
    model_id: str,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Manually deprecate a model.
    """
    try:
        response = supabase.table("model_registry")\
            .update({
                "status": "deprecated",
                "deprecated_at": datetime.now().isoformat()
            })\
            .eq("id", model_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Model not found")
        
        logger.info(f"✅ Deprecated model {model_id}")
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deprecate model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Get details of a specific model.
    """
    try:
        response = supabase.table("model_registry").select("*").eq("id", model_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Model not found")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

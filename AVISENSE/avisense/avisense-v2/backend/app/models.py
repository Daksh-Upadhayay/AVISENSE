from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime


class PredictionRequest(BaseModel):
    """Request model for prediction endpoint."""
    engine_id: str = Field(..., description="Engine UUID")
    input_data: Dict[str, float] = Field(..., description="Sensor and setting values")
    source: str = Field(default="ui", description="Source of prediction: ui, manual, ingest")
    
    @validator('input_data')
    def validate_features(cls, v):
        """Validate that all required features are present."""
        required_features = [
            'setting_1', 'setting_2', 'setting_3',
            'sensor_2', 'sensor_3', 'sensor_4', 'sensor_7', 'sensor_9',
            'sensor_11', 'sensor_12', 'sensor_14', 'sensor_17', 'sensor_20', 'sensor_21'
        ]
        
        missing = [f for f in required_features if f not in v]
        if missing:
            raise ValueError(f"Missing required features: {', '.join(missing)}")
        
        return v


class Anomaly(BaseModel):
    """Anomaly detection result."""
    sensor: str
    sensor_name: str
    value: float
    threshold: str
    threshold_min: float
    threshold_max: float
    severity: str  # low, medium, high
    description: str


class PredictionResponse(BaseModel):
    """Response model for prediction endpoint."""
    id: str
    prediction: str  # SAFE or PRONE TO FAILURE
    probability: float
    confidence: float
    safe_probability: float
    failure_probability: float
    timestamp: datetime
    engine_id: str
    actions: str
    anomalies: List[Anomaly]
    shap: Optional[Dict[str, Any]] = None
    risk_percent: Optional[float] = None
    correlated_anomalies: Optional[List[Dict[str, Any]]] = None
    model_version: str
    model_type: str
    input_data: Dict[str, float]
    created_by: Optional[str] = None
    created_at: datetime


class HealthResponse(BaseModel):
    """Health check response."""
    ok: bool
    model_loaded: bool
    model_version: str
    timestamp: datetime


class EngineCreate(BaseModel):
    """Request model for creating an engine."""
    engine_id: str = Field(..., description="User-facing engine ID (e.g., ENG-123)")
    model: Optional[str] = Field(None, description="Engine model (e.g., CFM56-7B)")
    serial_number: Optional[str] = None
    aircraft_registration: Optional[str] = None
    metadata: Optional[Dict] = None


class EngineResponse(BaseModel):
    """Response model for engine data."""
    id: str
    engine_id: str
    model: Optional[str]
    serial_number: Optional[str]
    aircraft_registration: Optional[str]
    owner_id: str
    organization_id: Optional[str]
    status: str
    metadata: Optional[Dict]
    created_at: datetime
    updated_at: datetime


class TelemetryBulkUpload(BaseModel):
    """Request model for bulk telemetry upload."""
    engine_id: str
    data: List[Dict[str, float]]
    source: str = "batch_upload"

from pydantic import BaseModel
from typing import Optional, List, Dict,Any

class FaceDetectionResult(BaseModel):
    face_detected: bool
    confidence: float
    bbox: Optional[List[float]] = None
    message: str
    response_time_ms: Optional[float] = None

class FaceVerificationResult(BaseModel):
    is_match: bool
    similarity: float
    threshold: float
    message: str
    response_time_ms: Optional[float] = None

class LivenessDetectionResult(BaseModel):
    is_live: bool
    confidence: float
    checks_passed: Dict[str, float]
    frame_count: int
    message: str
    details: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[float] = None

class LivenessVerificationResult(BaseModel):
    is_live: bool
    is_match: bool
    liveness_confidence: float
    face_similarity: float
    message: str
    response_time_ms: Optional[float] = None

class LivenessVideoVerificationResult(BaseModel):
    is_live_test: bool
    is_live_reference: bool
    is_match: bool
    test_confidence: float
    reference_confidence: float
    face_similarity: float
    message: str
    response_time_ms: Optional[float] = None

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    timestamp: str
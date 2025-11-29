import logging
from insightface.app import FaceAnalysis
from typing import Optional

logger = logging.getLogger(__name__)

face_app: Optional[FaceAnalysis] = None

def load_face_model():
    """Initialize InsightFace model"""
    global face_app
    try:
        logger.info("Loading InsightFace model...")
        
        face_app = FaceAnalysis(
            name='buffalo_l',
            providers=['CPUExecutionProvider']
        )
        face_app.prepare(ctx_id=0, det_size=(640, 640))
        
        logger.info("InsightFace model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load InsightFace model: {str(e)}")
        raise

def get_face_model():
    """Get loaded face model"""
    if face_app is None:
        raise RuntimeError("Face model not loaded")
    return face_app
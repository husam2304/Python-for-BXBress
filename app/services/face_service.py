import logging
import numpy as np
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class FaceService:
    def __init__(self, face_app):
        self.face_app = face_app
    
    def detect_face(self, img, side: str = "unknown") -> Tuple:
        """Detect face in image"""
        try:
            faces = self.face_app.get(img)
            
            if len(faces) == 0:
                return None, False, f"No face detected in {side} image"
            
            if len(faces) > 1:
                logger.warning(f"Multiple faces detected in {side}, using highest confidence")
            
            faces = sorted(faces, key=lambda x: x.det_score, reverse=True)
            best_face = faces[0]
            
            logger.info(f"Face detected in {side} - Confidence: {best_face.det_score:.3f}")
            return best_face, True, "Face detected successfully"
        
        except Exception as e:
            logger.error(f"Error detecting face: {str(e)}")
            return None, False, f"Face detection error: {str(e)}"
    
    def verify_faces(self, embedding1, embedding2, threshold: float = 0.4) -> Tuple:
        """Verify if two face embeddings match"""
        try:
            similarity = float(np.dot(embedding1, embedding2))
            is_match = similarity >= threshold
            
            return is_match, similarity
        
        except Exception as e:
            logger.error(f"Error verifying faces: {str(e)}")
            raise
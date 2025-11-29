import logging
import numpy as np
from typing import List, Dict

logger = logging.getLogger(__name__)

class LivenessService:
    def __init__(self, face_app):
        self.face_app = face_app
    
    def _extract_faces_from_frames(self, frames: List) -> tuple:
        """
        Single-pass face extraction from frames (reusable).
        Returns: (embeddings_list, boxes_list, scores_list, valid_frame_count)
        This method is called once and results are cached to avoid re-detection.
        """
        embeddings = []
        face_boxes = []
        face_scores = []
        
        for frame in frames:
            faces = self.face_app.get(frame)
            
            if len(faces) > 0:
                face = faces[0]
                embeddings.append(face.normed_embedding)
                face_boxes.append(face.bbox)
                face_scores.append(face.det_score)
        
        return embeddings, face_boxes, face_scores, len(embeddings)
    
    def get_embeddings_from_frames(self, frames: List, cached_faces: dict = None) -> tuple:
        """
        Extract and aggregate embeddings from all valid frames.
        If cached_faces provided (from liveness check), reuse instead of re-detecting.
        Returns: (aggregated_embedding, valid_frame_count, embeddings_list)
        """
        if cached_faces:
            embeddings = cached_faces.get('embeddings', [])
            valid_frame_count = len(embeddings)
            logger.info(f"Using cached face data: {valid_frame_count} frames (no re-detection)")
        else:
            embeddings, _, _, valid_frame_count = self._extract_faces_from_frames(frames)
        
        if valid_frame_count == 0:
            return None, 0, []
        
        # Aggregate embeddings by averaging
        aggregated_embedding = np.mean(embeddings, axis=0)
        # Normalize aggregated embedding
        aggregated_embedding = aggregated_embedding / np.linalg.norm(aggregated_embedding)
        
        logger.info(f"Aggregated {valid_frame_count} frame embeddings")
        return aggregated_embedding, valid_frame_count, embeddings
    
    def perform_liveness_checks(self, frames: List) -> Dict:
        """
        Perform liveness detection checks.
        Returns: Dict with is_live, confidence, and checks_passed
        """
        if len(frames) < 5:
            return {
                "is_live": False,
                "confidence": 0.0,
                "checks": {},
                "message": "Not enough frames (minimum 5 required)"
            }
        
        checks = {}
        
        # Single-pass face extraction (cached, no re-detection)
        embeddings, face_boxes, face_scores, valid_frame_count = self._extract_faces_from_frames(frames)
        
        if valid_frame_count < 3:
            return {
                "is_live": False,
                "confidence": 0.0,
                "checks": {"face_detection": False},
                "message": "Face not consistently detected"
            }
        
        # Check 1: Face Consistency
        embedding_similarities = []
        for i in range(len(embeddings) - 1):
            sim = float(np.dot(embeddings[i], embeddings[i + 1]))
            embedding_similarities.append(sim)
        
        avg_similarity = np.mean(embedding_similarities)
        checks["face_consistency"] = avg_similarity > 0.6
        checks["face_consistency_score"] = float(avg_similarity)
        
        # Check 2: Motion Detection
        if len(face_boxes) >= 3:
            box_movements = []
            for i in range(len(face_boxes) - 1):
                center1 = [(face_boxes[i][0] + face_boxes[i][2]) / 2,
                          (face_boxes[i][1] + face_boxes[i][3]) / 2]
                center2 = [(face_boxes[i+1][0] + face_boxes[i+1][2]) / 2,
                          (face_boxes[i+1][1] + face_boxes[i+1][3]) / 2]
                
                movement = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
                box_movements.append(movement)
            
            total_movement = sum(box_movements)
            checks["motion_detected"] = total_movement > 10
            checks["motion_score"] = float(total_movement)
        else:
            checks["motion_detected"] = False
            checks["motion_score"] = 0.0
        
        # Check 3: Size Variation
        if len(face_boxes) >= 3:
            box_sizes = [( box[2] - box[0]) * (box[3] - box[1]) for box in face_boxes]
            size_variation = np.std(box_sizes) / np.mean(box_sizes) if np.mean(box_sizes) > 0 else 0
            checks["size_variation"] = size_variation > 0.05
            checks["size_variation_score"] = float(size_variation)
        else:
            checks["size_variation"] = False
            checks["size_variation_score"] = 0.0
        
        # Check 4: Quality Variation
        score_std = np.std(face_scores)
        checks["quality_variation"] = score_std < 0.15
        checks["quality_score"] = float(np.mean(face_scores))
        
        # Calculate confidence
        passed_checks = sum([
            checks.get("face_consistency", False),
            checks.get("motion_detected", False),
            checks.get("size_variation", False),
            checks.get("quality_variation", False)
        ])
        
        confidence = passed_checks / 4
        is_live = passed_checks >= 3
        
        message = f"Liveness check: {passed_checks}/4 checks passed"
        
        return {
            "is_live": is_live,
            "confidence": confidence,
            "checks": checks,
            "valid_frames": valid_frame_count,
            "message": message,
            "_cached_faces": {
                "embeddings": embeddings,
                "boxes": face_boxes,
                "scores": face_scores
            }
        }
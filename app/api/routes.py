import logging
import tempfile
import os
import numpy as np
import time
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, HTTPException, Form

from app.api.models import (
    HealthResponse, FaceDetectionResult, FaceVerificationResult,
    LivenessDetectionResult, LivenessVerificationResult, LivenessVideoVerificationResult
)
from app.services.face_service import FaceService
from app.services.liveness_service import LivenessService
from app.utils.image_processor import read_image_bytes, Timer
from app.utils.video_processor import extract_frames_from_video
from app.ml_model import get_face_model

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Face Recognition"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        get_face_model()
        model_loaded = True
    except:
        model_loaded = False
    
    return HealthResponse(
        status="healthy" if model_loaded else "unhealthy",
        model_loaded=model_loaded,
        timestamp=datetime.utcnow().isoformat()
    )

@router.post("/face/detect", response_model=FaceDetectionResult)
async def detect_face_endpoint(
    image: UploadFile = File(...),
    side: str = Form(default="unknown"),
    min_confidence: float = Form(default=0.5)
):
    """Detect face in a single image"""
    endpoint_start = time.time()
    try:
        face_model = get_face_model()
        face_service = FaceService(face_model)
        
        image_bytes = await image.read()
        img = read_image_bytes(image_bytes)
        
        face, success, message = face_service.detect_face(img, side)
        
        elapsed_ms = (time.time() - endpoint_start) * 1000
        logger.info(f"POST /api/face/detect: {elapsed_ms:.1f}ms")
        
        if not success:
            return FaceDetectionResult(
                face_detected=False,
                confidence=0.0,
                message=message,
                response_time_ms=elapsed_ms
            )
        
        if face.det_score < min_confidence:
            return FaceDetectionResult(
                face_detected=False,
                confidence=float(face.det_score),
                message=f"Face confidence below threshold {min_confidence}",
                response_time_ms=elapsed_ms
            )
        
        bbox = face.bbox.tolist() if face.bbox is not None else None
        
        return FaceDetectionResult(
            face_detected=True,
            confidence=float(face.det_score),
            bbox=bbox,
            message="Face detected successfully",
            response_time_ms=elapsed_ms
        )
    
    except HTTPException:
        raise
    except Exception as e:
        elapsed_ms = (time.time() - endpoint_start) * 1000
        logger.error(f"Error in face detection after {elapsed_ms:.1f}ms: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/face/verify", response_model=FaceVerificationResult)
async def verify_faces(
    image1: UploadFile = File(...),
    image2: UploadFile = File(...),
    threshold: float = Form(default=0.4)
):
    """Verify if two face images match"""
    endpoint_start = time.time()
    try:
        face_model = get_face_model()
        face_service = FaceService(face_model)
        
        image1_bytes = await image1.read()
        image2_bytes = await image2.read()
        
        img1 = read_image_bytes(image1_bytes)
        img2 = read_image_bytes(image2_bytes)
        
        face1, success1, msg1 = face_service.detect_face(img1, "image1")
        if not success1:
            elapsed_ms = (time.time() - endpoint_start) * 1000
            return FaceVerificationResult(
                is_match=False,
                similarity=0.0,
                threshold=threshold,
                message=f"Image 1: {msg1}",
                response_time_ms=elapsed_ms
            )
        
        face2, success2, msg2 = face_service.detect_face(img2, "image2")
        if not success2:
            elapsed_ms = (time.time() - endpoint_start) * 1000
            return FaceVerificationResult(
                is_match=False,
                similarity=0.0,
                threshold=threshold,
                message=f"Image 2: {msg2}",
                response_time_ms=elapsed_ms
            )
        
        is_match, similarity = face_service.verify_faces(
            face1.normed_embedding,
            face2.normed_embedding,
            threshold
        )
        
        elapsed_ms = (time.time() - endpoint_start) * 1000
        logger.info(f"POST /api/face/verify: {elapsed_ms:.1f}ms")
        
        return FaceVerificationResult(
            is_match=is_match,
            similarity=similarity,
            threshold=threshold,
            message=f"Faces {'match' if is_match else 'do not match'}",
            response_time_ms=elapsed_ms
        )
    
    except HTTPException:
        raise
    except Exception as e:
        elapsed_ms = (time.time() - endpoint_start) * 1000
        logger.error(f"Error in face verification after {elapsed_ms:.1f}ms: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/liveness/detect", response_model=LivenessDetectionResult)
async def detect_liveness(
    video: UploadFile = File(...),
    max_frames: int = Form(default=30)
):
    """Detect liveness from video"""
    temp_video_path = None
    endpoint_start = time.time()
    
    try:
        face_model = get_face_model()
        liveness_service = LivenessService(face_model)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            content = await video.read()
            temp_file.write(content)
            temp_video_path = temp_file.name
        
        frames = extract_frames_from_video(temp_video_path, max_frames)
        
        if len(frames) < 5:
            elapsed_ms = (time.time() - endpoint_start) * 1000
            return LivenessDetectionResult(
                is_live=False,
                confidence=0.0,
                checks_passed={},
                frame_count=len(frames),
                message="Video too short (minimum 5 frames required)",
                response_time_ms=elapsed_ms
            )
        
        liveness_result = liveness_service.perform_liveness_checks(frames)
        
        elapsed_ms = (time.time() - endpoint_start) * 1000
        logger.info(f"POST /api/liveness/detect: {elapsed_ms:.1f}ms")
        
        return LivenessDetectionResult(
            is_live=liveness_result["is_live"],
            confidence=liveness_result["confidence"],
            checks_passed=liveness_result["checks"],
            frame_count=liveness_result.get("valid_frames", len(frames)),
            message=liveness_result["message"],
            details={
                "total_frames_extracted": len(frames),
                "valid_frames": liveness_result.get("valid_frames", 0)
            },
            response_time_ms=elapsed_ms
        )
    
    except Exception as e:
        elapsed_ms = (time.time() - endpoint_start) * 1000
        logger.error(f"Error in liveness detection after {elapsed_ms:.1f}ms: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.unlink(temp_video_path)
            except:
                pass

@router.post("/liveness/verify", response_model=LivenessVerificationResult)
async def liveness_with_verification(
    video: UploadFile = File(...),
    reference_image: UploadFile = File(...),
    face_threshold: float = Form(default=0.4),
    max_frames: int = Form(default=30)
):
    """Complete authentication: Liveness + Face verification"""
    temp_video_path = None
    endpoint_start = time.time()
    
    try:
        face_model = get_face_model()
        face_service = FaceService(face_model)
        liveness_service = LivenessService(face_model)
        
        # Liveness Detection
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            video_content = await video.read()
            temp_file.write(video_content)
            temp_video_path = temp_file.name
        
        frames = extract_frames_from_video(temp_video_path, max_frames)
        liveness_result = liveness_service.perform_liveness_checks(frames)
        
        if not liveness_result["is_live"]:
            elapsed_ms = (time.time() - endpoint_start) * 1000
            return LivenessVerificationResult(
                is_live=False,
                is_match=False,
                liveness_confidence=liveness_result["confidence"],
                face_similarity=0.0,
                message=f"Liveness check failed: {liveness_result['message']}",
                response_time_ms=elapsed_ms
            )
        
        # Face Verification
        best_frame = frames[len(frames) // 2]
        best_face, success, msg = face_service.detect_face(best_frame, "video")
        
        if not success:
            elapsed_ms = (time.time() - endpoint_start) * 1000
            return LivenessVerificationResult(
                is_live=True,
                is_match=False,
                liveness_confidence=liveness_result["confidence"],
                face_similarity=0.0,
                message=f"Face not detected in video: {msg}",
                response_time_ms=elapsed_ms
            )
        
        video_embedding = best_face.normed_embedding
        
        ref_bytes = await reference_image.read()
        ref_img = read_image_bytes(ref_bytes)
        ref_face, ref_success, ref_msg = face_service.detect_face(ref_img, "reference")
        
        if not ref_success:
            elapsed_ms = (time.time() - endpoint_start) * 1000
            return LivenessVerificationResult(
                is_live=True,
                is_match=False,
                liveness_confidence=liveness_result["confidence"],
                face_similarity=0.0,
                message=f"Face not detected in reference image: {ref_msg}",
                response_time_ms=elapsed_ms
            )
        
        ref_embedding = ref_face.normed_embedding
        
        is_match, similarity = face_service.verify_faces(
            video_embedding,
            ref_embedding,
            face_threshold
        )
        
        elapsed_ms = (time.time() - endpoint_start) * 1000
        logger.info(f"POST /api/liveness/verify: {elapsed_ms:.1f}ms")
        
        return LivenessVerificationResult(
            is_live=True,
            is_match=is_match,
            liveness_confidence=liveness_result["confidence"],
            face_similarity=similarity,
            message=f"Authentication {'successful' if is_match else 'failed'}",
            response_time_ms=elapsed_ms
        )
    
    except Exception as e:
        elapsed_ms = (time.time() - endpoint_start) * 1000
        logger.error(f"Error in liveness verification after {elapsed_ms:.1f}ms: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.unlink(temp_video_path)
            except:
                pass

@router.post("/liveness/verify-video", response_model=LivenessVideoVerificationResult)
async def liveness_verify_video(
    test_video: UploadFile = File(...),
    reference_video: UploadFile = File(...),
    face_threshold: float = Form(default=0.4),
    max_frames: int = Form(default=30)
):
    """Complete authentication: Liveness check on both videos + face verification via aggregated embeddings"""
    temp_test_video_path = None
    temp_ref_video_path = None
    endpoint_start = time.time()
    
    try:
        face_model = get_face_model()
        liveness_service = LivenessService(face_model)
        
        # Extract frames from test video
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            test_content = await test_video.read()
            temp_file.write(test_content)
            temp_test_video_path = temp_file.name
        
        test_frames = extract_frames_from_video(temp_test_video_path, max_frames)
        
        if len(test_frames) < 5:
            elapsed_ms = (time.time() - endpoint_start) * 1000
            return LivenessVideoVerificationResult(
                is_live_test=False,
                is_live_reference=False,
                is_match=False,
                test_confidence=0.0,
                reference_confidence=0.0,
                face_similarity=0.0,
                message="Test video too short (minimum 5 frames required)",
                response_time_ms=elapsed_ms
            )
        
        # Perform liveness check on test video
        test_liveness_result = liveness_service.perform_liveness_checks(test_frames)
        
        # Extract frames from reference video
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            ref_content = await reference_video.read()
            temp_file.write(ref_content)
            temp_ref_video_path = temp_file.name
        
        ref_frames = extract_frames_from_video(temp_ref_video_path, max_frames)
        
        if len(ref_frames) < 5:
            elapsed_ms = (time.time() - endpoint_start) * 1000
            return LivenessVideoVerificationResult(
                is_live_test=test_liveness_result["is_live"],
                is_live_reference=False,
                is_match=False,
                test_confidence=test_liveness_result["confidence"],
                reference_confidence=0.0,
                face_similarity=0.0,
                message="Reference video too short (minimum 5 frames required)",
                response_time_ms=elapsed_ms
            )
        
        # Perform liveness check on reference video
        ref_liveness_result = liveness_service.perform_liveness_checks(ref_frames)
        
        # If either video is not live, return early
        if not test_liveness_result["is_live"] or not ref_liveness_result["is_live"]:
            elapsed_ms = (time.time() - endpoint_start) * 1000
            return LivenessVideoVerificationResult(
                is_live_test=test_liveness_result["is_live"],
                is_live_reference=ref_liveness_result["is_live"],
                is_match=False,
                test_confidence=test_liveness_result["confidence"],
                reference_confidence=ref_liveness_result["confidence"],
                face_similarity=0.0,
                message="Liveness check failed on one or both videos",
                response_time_ms=elapsed_ms
            )
        
        # Extract aggregated embeddings from test video (use cached face data - no re-detection!)
        test_embedding, test_valid_frames, _ = liveness_service.get_embeddings_from_frames(
            test_frames,
            cached_faces=test_liveness_result.get("_cached_faces")
        )
        
        if test_embedding is None or test_valid_frames < 3:
            elapsed_ms = (time.time() - endpoint_start) * 1000
            return LivenessVideoVerificationResult(
                is_live_test=True,
                is_live_reference=True,
                is_match=False,
                test_confidence=test_liveness_result["confidence"],
                reference_confidence=ref_liveness_result["confidence"],
                face_similarity=0.0,
                message=f"Insufficient valid frames in test video (got {test_valid_frames}, need 3+)",
                response_time_ms=elapsed_ms
            )
        
        # Extract aggregated embeddings from reference video (use cached face data - no re-detection!)
        ref_embedding, ref_valid_frames, _ = liveness_service.get_embeddings_from_frames(
            ref_frames,
            cached_faces=ref_liveness_result.get("_cached_faces")
        )
        
        if ref_embedding is None or ref_valid_frames < 3:
            elapsed_ms = (time.time() - endpoint_start) * 1000
            return LivenessVideoVerificationResult(
                is_live_test=True,
                is_live_reference=True,
                is_match=False,
                test_confidence=test_liveness_result["confidence"],
                reference_confidence=ref_liveness_result["confidence"],
                face_similarity=0.0,
                message=f"Insufficient valid frames in reference video (got {ref_valid_frames}, need 3+)",
                response_time_ms=elapsed_ms
            )
        
        # Compare aggregated embeddings
        face_similarity = float(np.dot(test_embedding, ref_embedding))
        is_match = face_similarity >= face_threshold
        
        elapsed_ms = (time.time() - endpoint_start) * 1000
        logger.info(f"POST /api/liveness/verify-video: {elapsed_ms:.1f}ms - similarity={face_similarity:.3f}, match={is_match}")
        
        return LivenessVideoVerificationResult(
            is_live_test=True,
            is_live_reference=True,
            is_match=is_match,
            test_confidence=test_liveness_result["confidence"],
            reference_confidence=ref_liveness_result["confidence"],
            face_similarity=face_similarity,
            message=f"Video authentication {'successful' if is_match else 'failed'} (similarity: {face_similarity:.3f})",
            response_time_ms=elapsed_ms
        )
    
    except Exception as e:
        elapsed_ms = (time.time() - endpoint_start) * 1000
        logger.error(f"Error in video-to-video liveness verification after {elapsed_ms:.1f}ms: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if temp_test_video_path and os.path.exists(temp_test_video_path):
            try:
                os.unlink(temp_test_video_path)
            except:
                pass
        if temp_ref_video_path and os.path.exists(temp_ref_video_path):
            try:
                os.unlink(temp_ref_video_path)
            except:
                pass
import cv2
import numpy as np
import logging
from typing import List

logger = logging.getLogger(__name__)

def extract_frames_from_video(video_path: str, max_frames: int = 30, adaptive: bool = True, resize_to: tuple = (640, 480)) -> List[np.ndarray]:
    """Extract frames from video with adaptive sizing and resizing for performance
    
    Args:
        video_path: Path to video file
        max_frames: Maximum frames to extract (default)
        adaptive: If True, reduce frame count for short videos
        resize_to: Target resolution for frames (width, height). Speeds up face detection.
    
    Returns:
        List of numpy arrays (frames) resized to resize_to dimensions
    """
    frames = []
    
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError("Could not open video file")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        
        logger.info(f"Video: {total_frames} frames, {fps:.2f} FPS, {duration:.1f}s duration")
        
        # Adaptive frame count based on video duration
        if adaptive:
            if duration < 2:
                effective_max_frames = 10
                logger.info("Short video detected: reducing to 10 frames")
            elif duration < 5:
                effective_max_frames = 15
                logger.info("Medium video detected: reducing to 15 frames")
            else:
                effective_max_frames = max_frames
        else:
            effective_max_frames = max_frames
        
        if total_frames <= effective_max_frames:
            frame_indices = range(total_frames)
        else:
            frame_indices = np.linspace(0, total_frames - 1, effective_max_frames, dtype=int)
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            
            if ret and frame is not None:
                # Resize frame to improve detection speed
                frame_resized = cv2.resize(frame, resize_to, interpolation=cv2.INTER_LINEAR)
                frames.append(frame_resized)
        
        cap.release()
        
        logger.info(f"Extracted {len(frames)} frames (resized to {resize_to[0]}x{resize_to[1]})")
        return frames
    
    except Exception as e:
        logger.error(f"Error extracting frames: {str(e)}")
        raise
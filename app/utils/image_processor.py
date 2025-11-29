import cv2
import numpy as np
import logging
import time
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class Timer:
    """Context manager for timing code blocks"""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time = None
        self.elapsed_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.elapsed_time = time.time() - self.start_time
        logger.info(f"{self.name} took {self.elapsed_time:.3f}s")
    
    def get_elapsed(self) -> float:
        """Get elapsed time in seconds"""
        if self.elapsed_time is None:
            raise RuntimeError("Timer not stopped yet")
        return self.elapsed_time

def read_image_bytes(file_bytes: bytes) -> np.ndarray:
    """Convert uploaded bytes to OpenCV image"""
    try:
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Failed to decode image")
        
        return img
    except Exception as e:
        logger.error(f"Error reading image bytes: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid image format: {str(e)}")
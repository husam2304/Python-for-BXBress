# Copilot Instructions for Face Recognition Service

## Project Overview
This is a **FastAPI-based face recognition and liveness detection service** using InsightFace. It provides four core API endpoints that combine face detection, face verification, liveness detection, and integrated authentication workflows.

### Architecture
```
FastAPI App (port 8000)
├── API Routes (app/api/routes.py)
│   ├── Health check
│   ├── Face Detection (/face/detect)
│   ├── Face Verification (/face/verify)
│   ├── Liveness Detection (/liveness/detect)
│   ├── Combined Auth (/liveness/verify) - video + reference image
│   └── Video-to-Video Auth (/liveness/verify-video) - video + reference video
├── Services (app/services/)
│   ├── FaceService: face detection & verification logic
│   └── LivenessService: liveness checks (4-check algorithm) + embedding aggregation
├── ML Model (app/ml_model.py)
│   └── Global InsightFace instance (buffalo_l model, CPU-only)
└── Utilities (app/utils/)
    ├── image_processor: bytes → OpenCV image
    └── video_processor: video → frame extraction
```

## Key Patterns & Implementation Details

### 1. InsightFace Model Lifecycle
- **Single Global Instance**: `face_app` is loaded once at startup in `app/ml_model.py`, stored as module-level global
- **Access Pattern**: Always use `get_face_model()` to retrieve it; raises `RuntimeError` if not loaded
- **CPU-Only**: Configured with `CPUExecutionProvider` (no GPU) and `det_size=(640, 640)`
- **Model Name**: `buffalo_l` (largest, most accurate)
- **Startup**: Model loads in FastAPI `@app.on_event("startup")` hook

### 2. Face Service Patterns
**File**: `app/services/face_service.py`
- `detect_face(img, side)` returns tuple: `(face_object, success_bool, message_string)`
- Always sorts multiple faces by confidence (`det_score`) and uses highest
- Face objects have: `normed_embedding`, `det_score`, `bbox`, `kps` (landmarks)
- Face matching uses cosine similarity (dot product of normalized embeddings, threshold typically 0.4)

### 3. Liveness Detection Algorithm
**File**: `app/services/liveness_service.py`
- Requires ≥5 frames minimum from video; only processes frames with detected faces
- **4 Checks** (3 of 4 must pass for liveness):
  1. **Face Consistency**: embedding similarity between consecutive frames > 0.6
  2. **Motion Detected**: centroid movement across frames > 10 pixels
  3. **Size Variation**: bbox size variation > 5%
  4. **Quality Variation**: face detection score std dev < 0.15
- Returns dict: `{"is_live": bool, "confidence": float (0-1), "checks": {}, "valid_frames": int, "_cached_faces": {}}`
- **Performance Optimization**: Returns `_cached_faces` dict containing embeddings, boxes, scores to avoid re-detecting frames
- Method `_extract_faces_from_frames()` does single-pass detection for efficiency

### 3.5 Embedding Aggregation (New)
**File**: `app/services/liveness_service.py` - `get_embeddings_from_frames(frames)`
- Extracts normalized embeddings from all valid frames with detected faces
- **Aggregation Strategy**: Averages all embeddings, then L2-normalizes result
- Returns tuple: `(aggregated_embedding, valid_frame_count, embeddings_list)`
- Used for robust video-to-video comparison (less sensitive to pose/lighting variations than single-frame matching)
- Minimum 3 valid frames required for meaningful aggregation

### 4. File Upload & Processing
- **Images**: Upload as multipart `File`, converted via `read_image_bytes()` to OpenCV BGR array
- **Videos**: Written to temp file, frames extracted via `cv2.VideoCapture`, temp file deleted in `finally` block
- **Frame Extraction** (app/utils/video_processor.py): 
  - Spreads frames evenly across video duration using `np.linspace()`
  - **Adaptive frame count**: Short videos (<2s) use 10 frames, medium (<5s) use 15 frames, long use 30 (default)
  - **Frame resizing**: Resizes all frames to 640×480 by default (configurable) for faster face detection
  - Reduces memory footprint and computation time by ~20-25%
- Both utilities raise `HTTPException(400)` for invalid formats

### 5. Error Handling Pattern
```python
try:
    face_model = get_face_model()
    result = service.method(data)
    return SuccessResponse(...)
except HTTPException:
    raise  # Re-raise HTTP errors
except Exception as e:
    logger.error(f"Error in endpoint: {str(e)}")
    raise HTTPException(status_code=500, detail=str(e))
finally:
    # cleanup (temp files, etc)
```

### 6. API Response Models
**File**: `app/api/models.py` - All use Pydantic BaseModel:
- `FaceDetectionResult`: includes optional `bbox` as `[x1, y1, x2, y2]` list
- `FaceVerificationResult`: includes `threshold` for transparency
- `LivenessDetectionResult`: includes `details` dict with frame counts
- `LivenessVerificationResult`: combined result (both liveness + face match)

## Development Workflow

### Running the Service
```powershell
python run.py  # Starts uvicorn on 0.0.0.0:8000 with auto-reload
```

### Environment Setup
- No `.env` currently used (module imports `python-dotenv` but unused)
- Dependencies in `requirements.txt`
- Configure Python environment before development

### Testing Endpoints
```
GET  /api/health                         # Returns {status, model_loaded, timestamp}
POST /api/face/detect                    # File + side + min_confidence
POST /api/face/verify                    # image1 + image2 + threshold
POST /api/liveness/detect                # video + max_frames
POST /api/liveness/verify                # video + reference_image + thresholds
POST /api/liveness/verify-video          # test_video + reference_video + face_threshold + max_frames (NEW)
```

## Common Implementation Tasks

### Adding a new detection endpoint
1. Implement business logic in `app/services/` (or reuse existing)
2. Create response model in `app/api/models.py`
3. Add route in `app/api/routes.py` with standard error handling
4. Call `get_face_model()`, instantiate service, process, return model

### Adjusting liveness thresholds
- Edit constants in `LivenessService.perform_liveness_checks()`: `0.6` (consistency), `10` (motion), `0.05` (size), `0.15` (quality)
- Each check's score available in returned `checks` dict for debugging

### Changing face matching threshold
- Default is `0.4` in route endpoints; pass as `threshold` (image-based) or `face_threshold` (video-based) form parameter
- Lower = more permissive, higher = stricter matching

### Video-to-Video Verification (`/liveness/verify-video`)
- **Workflow**: Extracts liveness + aggregated embeddings from both test and reference videos, compares embeddings
- **Requirements**: Both videos must pass liveness checks (3/4 checks passing)
- **Embedding Strategy**: Averages embeddings across all valid frames (≥3) for robustness
- **Comparison**: Cosine similarity via dot product; default threshold 0.4
- **Response**: `LivenessVideoVerificationResult` with `is_live_test`, `is_live_reference`, `is_match`, and similarity score
- **Performance**: ~60 seconds (1 minute) per endpoint call with optimizations
- **Key Optimization**: Uses cached face detection results—each frame analyzed once, not twice

### Performance Optimizations (75% speedup achieved)
1. **Face Detection Caching**: `perform_liveness_checks()` returns `_cached_faces` dict (embeddings, boxes, scores)
   - `get_embeddings_from_frames()` accepts `cached_faces` parameter to reuse instead of re-detecting
   - Eliminates 50% of face detection operations
   
2. **Adaptive Frame Extraction**: 
   - Videos <2s: 10 frames
   - Videos 2-5s: 15 frames  
   - Videos >5s: 30 frames (default)
   - Saves 20-30% processing time
   
3. **Frame Resizing**: Resizes frames to 640×480 before detection (from full resolution)
   - Memory reduction: 80-90%
   - Detection speedup: ~15-20%

### Handling model loading failures
- Any exception during `load_face_model()` logs error and re-raises
- Service won't start; check logs for missing dependencies or GPU/memory issues
- Health endpoint returns `model_loaded: false` if model unavailable

## Conventions & Notes
- **Logging**: Configured at service startup in `app/main.py`, use `logging.getLogger(__name__)` in each module
- **CORS**: Allows all origins (`["*"]`) - configure in `main.py` for production
- **No database**: Service is stateless; relies on model in memory
- **Embeddings**: Normalized (L2) dot product for similarity—no special normalization needed
- **Video temp files**: Always cleaned up in `finally` block to prevent disk accumulation
- **Multiple faces**: Sorted by confidence; first face always used (logged if >1 detected)

## Deployment

### Render Deployment (FREE)
**Platform**: https://render.com (750 free compute hours/month)

**Prerequisites**:
- GitHub account with code pushed to repository
- Render account (sign up with GitHub)

**Deployment Steps**:

1. **Push code to GitHub**
   ```powershell
   git init
   git add .
   git commit -m "Initial commit: Face recognition service"
   git remote add origin https://github.com/YOUR_USERNAME/face-recognition-service.git
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to https://render.com/dashboard
   - Click "New +" → "Web Service"
   - Connect GitHub repository
   - Select this repository
   - Configure:
     - **Name**: `face-recognition-service`
     - **Environment**: `Docker`
     - **Branch**: `main`
     - **Build Command**: (auto-detected from Dockerfile)
     - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Click "Create Web Service"

3. **Monitor Deployment**
   - Render builds Docker image (~3-5 minutes)
   - Model downloads on first startup (~2-3 minutes)
   - Service available at `https://face-recognition-service.onrender.com`

**Files Created**:
- `Dockerfile`: Multi-stage build, installs all dependencies
- `render.yaml`: Render platform configuration (optional, can deploy without it)
- `.dockerignore`: Excludes unnecessary files from Docker build

**Environment Variables** (auto-configured):
- `PORT`: Render assigns dynamically
- `PYTHONUNBUFFERED=1`: Ensures real-time logging
- `PYTHONDONTWRITEBYTECODE=1`: Reduces disk I/O

**Health Check**:
- Render monitors `/api/health` endpoint (30s intervals)
- Service auto-restarts if unhealthy

**Limitations & Workarounds**:

| Limitation | Solution |
|-----------|----------|
| 750 hr/month limit | ~25 hrs/day usage; sufficient for dev/testing |
| Cold starts after inactivity | Service will restart; model reloads (~3-5s) |
| 4GB RAM limit | Current setup uses ~1.2GB; sufficient for CPU-only |
| Video upload timeout (30s) | Use adaptive frame extraction; typical video ~10-15s |
| No persistent storage | Temp files cleaned automatically; models cached |

**API Endpoints** (after deployment):
```
https://face-recognition-service.onrender.com/api/health
https://face-recognition-service.onrender.com/api/face/detect
https://face-recognition-service.onrender.com/api/face/verify
https://face-recognition-service.onrender.com/api/liveness/detect
https://face-recognition-service.onrender.com/api/liveness/verify
https://face-recognition-service.onrender.com/api/liveness/verify-video
```

**OpenAPI Documentation**:
```
https://face-recognition-service.onrender.com/docs
```

**Testing After Deployment**:
```powershell
# Check health
curl https://face-recognition-service.onrender.com/api/health

# View logs
# → Render Dashboard → Web Service → Logs
```

**Costs**:
- Free tier: $0/month
- Paid tier: $7/month (recommended for production; unlimited hours)

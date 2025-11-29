# Render Deployment Guide

## Quick Start (5 minutes)

### Step 1: Prepare Your GitHub Repository

```powershell
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Face recognition service with Render deployment files"

# Add remote (replace with your GitHub repo)
git remote add origin https://github.com/YOUR_USERNAME/face-recognition-service.git

# Push to main branch
git push -u origin main
```

### Step 2: Deploy on Render

1. **Create Render Account**
   - Go to https://render.com
   - Click "Sign up" 
   - Connect with GitHub

2. **Create Web Service**
   - Dashboard → New + → Web Service
   - Connect GitHub (authorize Render)
   - Select `face-recognition-service` repository

3. **Configure Service**
   - **Name**: `face-recognition-service`
   - **Environment**: Docker
   - **Branch**: main
   - **Build Command**: (Leave empty - auto-detected)
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. **Review & Deploy**
   - Click "Create Web Service"
   - Wait for build to complete (~5-10 minutes total)

### Step 3: Test Your Service

```powershell
# Get your service URL from Render Dashboard
$url = "https://face-recognition-service.onrender.com"

# Test health endpoint
curl "$url/api/health"

# View API docs
# Open in browser: $url/docs
```

---

## What Gets Deployed

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image definition with all dependencies |
| `render.yaml` | Render platform configuration (auto-detected) |
| `.dockerignore` | Excludes unnecessary files from build |
| `app/` | FastAPI application code |
| `requirements.txt` | Python dependencies |

---

## Build Process

1. **Image Build** (~3-5 minutes)
   - Render pulls Docker image from registry
   - Installs system dependencies (OpenCV, libgomp)
   - Installs Python packages from requirements.txt
   - Compresses image

2. **Service Start** (~2-3 minutes)
   - Container starts
   - InsightFace model downloads (~500MB)
   - Model loads into memory
   - Service becomes available

**Total first deployment**: ~5-10 minutes

---

## Environment Variables

Render automatically provides:
- `PORT`: Dynamic port assignment (8000, 8001, etc.)
- `RENDER`: Set to `true` (useful for runtime detection)

### Add Custom Variables (Optional)

In Render Dashboard:
- Web Service → Environment
- Add variables as needed
- Redeploy after adding

Example:
```
LOG_LEVEL=INFO
MAX_FRAMES=30
FACE_THRESHOLD=0.4
```

---

## Monitoring & Logs

**View Logs**:
- Render Dashboard → Your Service → Logs
- Realtime streaming of service output

**Metrics**:
- Dashboard → Metrics
- CPU, Memory, Network usage

**Restart Service**:
- Dashboard → Manual Restart (if needed)

---

## Limitations & Solutions

### 750 Free Hours/Month
- ~25 hours/day average
- Sufficient for:
  - Development & testing
  - Demo purposes
  - Low-volume production

**Solution for 24/7**: Upgrade to Paid ($7/month)

### Cold Starts
- After ~30 mins inactivity, service spins down
- First request triggers restart (~5-10 seconds)
- Model reloads (~3-5 seconds)

**Solution**: Keep-alive requests using external service (UptimeRobot, free tier)

### 4GB RAM Limit
- Current service: ~1.2GB (model + runtime)
- Sufficient for CPU-only processing
- No scaling concerns for typical workloads

### Video Upload Timeout (30 seconds)
- Default Render timeout
- Typical 5-second video = 10-15 seconds processing
- Safe margin available

**Solution**: For longer videos, use `max_frames=15` or `adaptive=true` (default)

### No Persistent Storage
- Temp files auto-cleaned
- Model files downloaded at startup
- No persistent database

**Solution**: Add PostgreSQL database (free tier available) if needed

---

## API Usage After Deployment

### Health Check
```bash
curl https://YOUR_SERVICE_NAME.onrender.com/api/health
```

### Face Detection
```bash
curl -X POST https://YOUR_SERVICE_NAME.onrender.com/api/face/detect \
  -F "image=@face.jpg" \
  -F "side=selfie" \
  -F "min_confidence=0.5"
```

### Liveness Verification
```bash
curl -X POST https://YOUR_SERVICE_NAME.onrender.com/api/liveness/verify-video \
  -F "test_video=@test.mp4" \
  -F "reference_video=@reference.mp4" \
  -F "face_threshold=0.4"
```

### Interactive Docs
Browse: `https://YOUR_SERVICE_NAME.onrender.com/docs`

---

## Troubleshooting

### Service won't start
1. Check Logs tab in Render Dashboard
2. Common issues:
   - Missing dependencies → Update requirements.txt
   - Port binding error → Check Dockerfile
   - Model download failure → Increase timeout

### Timeouts on video processing
- Reduce `max_frames` parameter (use 15-20)
- Enable `adaptive=true` (default)
- Shorter videos (<5 seconds)

### High memory usage
- Current: ~1.2GB with model loaded
- Normal behavior
- Render free tier: 4GB available

### Deploy fails to build
- Check `.dockerignore` (shouldn't exclude app/)
- Verify requirements.txt syntax
- Check Dockerfile syntax

---

## Upgrade to Paid (Optional)

When ready for production:
1. Render Dashboard → Your Service → Settings
2. Select Paid Plan ($7/month)
3. Benefits:
   - Unlimited compute hours
   - No cold starts
   - Higher resource limits
   - 99.5% uptime SLA

---

## Next Steps

1. ✅ Push code to GitHub
2. ✅ Deploy on Render
3. ✅ Test health endpoint
4. 📝 Update frontend with new API URL
5. 📊 Monitor logs & metrics
6. 🚀 Scale if needed

---

For questions: Check Render docs at https://docs.render.com

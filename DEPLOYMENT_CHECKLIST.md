# Render Deployment Checklist

## Pre-Deployment ✅

- [x] `Dockerfile` created (Python 3.10, all dependencies)
- [x] `render.yaml` created (platform configuration)
- [x] `.dockerignore` created (optimize build size)
- [x] `requirements.txt` verified (all packages listed)
- [x] `app/` directory with all modules
- [x] `.github/copilot-instructions.md` updated
- [x] `RENDER_DEPLOYMENT.md` guide created

## Pre-GitHub Push

- [ ] Create GitHub repository (if not exists)
- [ ] Initialize local git: `git init`
- [ ] Add all files: `git add .`
- [ ] Create initial commit: `git commit -m "Initial commit: Face recognition service"`
- [ ] Add remote: `git remote add origin https://github.com/YOUR_USERNAME/face-recognition-service.git`
- [ ] Push to GitHub: `git push -u origin main`

## Render Deployment

- [ ] Create Render account (https://render.com)
- [ ] Connect GitHub to Render
- [ ] Create new Web Service
- [ ] Select `face-recognition-service` repository
- [ ] Configure service:
  - [ ] Name: `face-recognition-service`
  - [ ] Environment: Docker
  - [ ] Branch: main
  - [ ] Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [ ] Click "Create Web Service"

## Wait for Deployment

- [ ] Build phase (~3-5 minutes)
  - View in Logs tab
  - Should show: "Successfully built Docker image"
- [ ] Startup phase (~2-3 minutes)
  - Should show: "InsightFace model loaded successfully"
  - Should show: "Application startup complete"
- [ ] Service URL assigned
  - Format: `https://face-recognition-service.onrender.com` (or custom name)

## Post-Deployment Testing

- [ ] Health check endpoint working
  ```
  https://YOUR_SERVICE_URL/api/health
  ```
- [ ] Swagger docs accessible
  ```
  https://YOUR_SERVICE_URL/docs
  ```
- [ ] Test a simple endpoint (face/detect or face/verify)
- [ ] Monitor logs for errors
- [ ] Check metrics (CPU, Memory usage)

## Optional Configuration

- [ ] Set environment variables (if needed)
- [ ] Configure custom domain (paid tier)
- [ ] Set up monitoring/alerts
- [ ] Connect database (if needed)
- [ ] Configure CI/CD auto-deploy on push

## Documentation

- [ ] Share API URL with team
- [ ] Document endpoint examples
- [ ] Update frontend config with new API URL
- [ ] Create API documentation/postman collection

## Success Criteria

✅ Health endpoint returns 200 with model_loaded=true
✅ /docs page loads and shows all endpoints
✅ At least one endpoint tested successfully
✅ Logs show no errors or warnings
✅ Service remains stable for 5+ minutes

---

## Troubleshooting

If deployment fails:
1. Check Render Logs tab (Dashboard → Service → Logs)
2. Look for common errors:
   - `ImportError: No module named 'cv2'` → requirements.txt issue
   - `Port already in use` → Dockerfile issue
   - `Model download timeout` → Network/size issue
3. Common fixes:
   - Verify requirements.txt
   - Check Dockerfile syntax
   - Increase build timeout in Render settings
4. Try manual rebuild:
   - Dashboard → Settings → Manual Deploy

---

## First Time Users: Expected Timeline

| Phase | Duration | What to Expect |
|-------|----------|-----------------|
| Code Push | 1 min | Files uploaded to GitHub |
| Build Start | 1 min | Render detects changes, starts build |
| Build Phase | 3-5 min | Docker image building, dependencies installing |
| Container Start | 2-3 min | InsightFace model downloading (~500MB) |
| Model Load | 1-2 min | Model loading into memory |
| Ready | ~10 min | Service available at URL |

**Total**: ~10-15 minutes from push to live

---

## Next Steps After Successful Deployment

1. **Test all endpoints** with your test data
2. **Monitor metrics** daily for first week
3. **Update frontend** with new API URL
4. **Consider upgrade** to paid tier if 24/7 uptime needed
5. **Set up monitoring** using external uptime checker
6. **Create API documentation** for team
7. **Plan scaling** if usage increases

---

Keep this checklist handy for future deployments! 🚀

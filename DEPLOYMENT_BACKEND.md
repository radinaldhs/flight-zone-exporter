# Backend Deployment Guide - Updated for Heavy Dependencies

## ⚠️ Important: Vercel Limitations

**Your FastAPI backend is TOO LARGE for Vercel's serverless functions** due to:
- GeoPandas (geospatial library)
- GDAL, GEOS dependencies
- NumPy, Pandas (data processing)

**Total size**: ~500-800MB unzipped
**Vercel limit**: 250MB unzipped ❌

## ✅ Recommended Platforms

### Option 1: Render.com (Easiest - Recommended)

**Free Tier**: 750 hours/month
**Pros**: No size limits, easy setup, auto-deploy from GitHub

#### Deploy Steps:

1. **Push to GitHub** (if not done):
```bash
cd /Users/radinaldewantara/Projects/PERSONAL/flight-zone-exporter
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/flight-zone-exporter.git
git push -u origin main
```

2. **Go to [Render.com](https://render.com)**:
   - Sign up with GitHub
   - Click "New +" → "Web Service"
   - Connect your repository

3. **Configure**:
   - **Name**: `flight-zone-exporter-api`
   - **Region**: Choose closest
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. **Add Environment Variables**:
   - `GIS_AUTH_USERNAME`: your_username
   - `GIS_AUTH_PASSWORD`: your_password
   - `GIS_USERNAME`: your_gis_username
   - `GIS_PASSWORD`: your_gis_password
   - `CORS_ORIGINS`: `["https://your-frontend.vercel.app"]`

5. **Deploy**: Click "Create Web Service"

6. **Your API URL**: `https://flight-zone-exporter-api.onrender.com`

#### Using render.yaml (Automatic):

We've created `render.yaml` for you! Just:

1. Push to GitHub
2. In Render dashboard: "New" → "Blueprint"
3. Connect your repo
4. Render auto-detects `render.yaml` and deploys!

---

### Option 2: Railway.app

**Free Tier**: $5 credit/month
**Pros**: No sleep time, faster than Render

#### Deploy Steps:

**Method A: GitHub Integration**

1. Push to GitHub
2. Go to [railway.app](https://railway.app)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Add environment variables
6. Deploy!

**Method B: Railway CLI**

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link project
railway init

# Add environment variables
railway variables set GIS_AUTH_USERNAME=your_username
railway variables set GIS_AUTH_PASSWORD=your_password
railway variables set GIS_USERNAME=your_gis_username
railway variables set GIS_PASSWORD=your_gis_password

# Deploy
railway up
```

Your API URL will be provided after deployment.

---

### Option 3: Google Cloud Run (Production Grade)

**Free Tier**: 2M requests/month
**Pros**: Best for production, scales to zero, no size limits

```bash
# Install gcloud CLI first
# Then:

gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Deploy using existing Dockerfile
gcloud run deploy flight-zone-exporter \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GIS_AUTH_USERNAME=your_username,GIS_AUTH_PASSWORD=your_password,GIS_USERNAME=your_gis_username,GIS_PASSWORD=your_gis_password"
```

---

## 📊 Platform Comparison

| Platform | Free Tier | Sleep Time | Size Limit | Setup Difficulty |
|----------|-----------|------------|------------|------------------|
| **Render** | 750h/month | Yes (15 min) | None ✅ | ⭐ Easy |
| **Railway** | $5 credit | No ✅ | None ✅ | ⭐⭐ Easy |
| **Cloud Run** | 2M req/month | No ✅ | None ✅ | ⭐⭐⭐ Medium |
| ~~Vercel~~ | Unlimited | No | ❌ 250MB | ❌ Too small |

---

## 🎯 Complete Deployment Strategy

### 1. Backend → Render.com (or Railway)

Follow Option 1 above.

### 2. Frontend → Vercel

The Vue.js frontend is lightweight and works perfectly on Vercel!

```bash
cd /Users/radinaldewantara/Projects/PERSONAL/flight-zone-exporter-vue

# Update .env with your deployed backend URL
# .env:
# VITE_API_URL=https://flight-zone-exporter-api.onrender.com

# Push to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/flight-zone-exporter-vue.git
git push -u origin main

# Deploy to Vercel
# Go to vercel.com, import repo, set environment variable:
# VITE_API_URL = https://flight-zone-exporter-api.onrender.com
```

### 3. Update CORS in Backend

After deploying frontend to Vercel, update backend CORS:

In `app/core/config.py`:
```python
CORS_ORIGINS: list = ["https://your-frontend.vercel.app"]
```

Or set environment variable in Render:
```
CORS_ORIGINS=["https://your-frontend.vercel.app"]
```

---

## 🚀 Quick Deploy with Render (5 Minutes)

**Fastest way to get your backend online:**

1. **Push to GitHub**:
```bash
cd flight-zone-exporter
git init
git add .
git commit -m "Ready for Render"
git push -u origin main
```

2. **One-Click Deploy**:
   - Go to [render.com](https://render.com)
   - "New Web Service" → Connect GitHub repo
   - Render auto-detects Python
   - Add your 4 environment variables
   - Click "Create Web Service"

3. **Wait 5-10 minutes** for build (GeoPandas takes time to install)

4. **Done!** Your API is live at: `https://your-service.onrender.com`

---

## ⚙️ Environment Variables Needed

For all platforms, you need these 4 variables:

| Variable | Description |
|----------|-------------|
| `GIS_AUTH_USERNAME` | ArcGIS auth username |
| `GIS_AUTH_PASSWORD` | ArcGIS auth password |
| `GIS_USERNAME` | GIS username |
| `GIS_PASSWORD` | GIS password |

Optional:
| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `["*"]` | Allowed frontend URLs |
| `DEBUG` | `False` | Debug mode |

---

## 🐛 Troubleshooting

### Build Takes Too Long
- **Normal**: GeoPandas + dependencies take 5-10 minutes to install
- **Solution**: Wait patiently, it only happens once

### Out of Memory During Build
- **Platform**: Use Railway or Cloud Run (more RAM)
- **Or**: Split into smaller dependencies

### CORS Errors After Deploy
```python
# Update backend CORS settings
# app/main.py:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📝 Deployment Checklist

Backend (Render/Railway):
- [ ] Code pushed to GitHub
- [ ] Environment variables configured
- [ ] Deployment successful
- [ ] API accessible at deployed URL
- [ ] Health check works: `/api/health`

Frontend (Vercel):
- [ ] `VITE_API_URL` updated to backend URL
- [ ] Code pushed to GitHub
- [ ] Deployed to Vercel
- [ ] CORS working (no console errors)
- [ ] Can upload files

---

## 💡 Why Vercel Failed

Vercel's serverless functions have strict limits:

```
Your app:
├── GeoPandas: ~200MB
├── GDAL/GEOS: ~150MB
├── Pandas/NumPy: ~100MB
├── Other deps: ~100MB
└── Total: ~550MB ❌

Vercel limit: 250MB ❌
```

**GeoPandas is meant for servers, not serverless!**

Render/Railway/Cloud Run support full Docker containers with no size limits.

---

## ✅ Recommended: Render.com

For your use case, **Render.com** is perfect:

✅ No size limits
✅ Free tier (750 hours/month)
✅ Auto-deploy from GitHub
✅ Easy environment variables
✅ Free SSL
✅ Works great with GeoPandas

**Only downside**: Sleep after 15 minutes of inactivity (free tier)

To keep it awake: Use a cron job to ping every 14 minutes (optional).

---

## 🎉 Final Architecture

```
User Browser
    ↓
Vue.js Frontend (Vercel) ← Lightweight, fast ✅
    ↓
FastAPI Backend (Render) ← GeoPandas, heavy deps ✅
    ↓
ArcGIS Feature Server
```

This is the optimal setup for your app!

---

## 📞 Need Help?

1. Check build logs in Render/Railway dashboard
2. Test API at: `https://your-service.onrender.com/docs`
3. Verify CORS settings if frontend can't connect

---

© 2025 Radinal Dewantara Husein

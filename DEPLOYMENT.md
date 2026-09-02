# Deployment Guide - CurseForge Mod Downloader

This guide will help you deploy the Flask backend to Railway and connect it to your Cloudflare Pages frontend at mod-depot.pages.dev.

## 🚀 Deployment Steps

### Step 1: Deploy Backend to Railway

1. **Create a Railway Account**
   - Go to [railway.app](https://railway.app)
   - Sign up (free tier available)

2. **Create a New Project**
   - Click "New Project" → "Deploy from GitHub repo"
   - Or select "Deploy via CLI" if you prefer

3. **Connect Your GitHub Repository**
   - Push your ModDepot folder to GitHub
   - Connect the repository to Railway
   - Railway will automatically detect the Python app

4. **Configure Environment Variables** (if needed)
   - Railway will automatically install dependencies from `requirements.txt`
   - The `Procfile` tells Railway how to run the app
   - The `railway.json` provides build configuration

5. **Deploy**
   - Click "Deploy" 
   - Railway will build and deploy your Flask app
   - Wait for the deployment to complete (2-3 minutes)

6. **Get Your Railway URL**
   - Once deployed, Railway will provide a URL like:
   - `https://curseforge-downloader-production.up.railway.app`
   - Copy this URL

### Step 2: Update Cloudflare Pages Frontend

1. **Update API Base URL**
   - Edit `public/index.html` in your Cloudflare Pages project
   - Find the API_BASE configuration (around line 355)
   - Replace the placeholder URL with your Railway URL:
   ```javascript
   const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
       ? 'http://127.0.0.1:5000/api' 
       : 'https://YOUR-RAILWAY-URL.railway.app/api'; // Replace with your actual Railway URL
   ```

2. **Deploy Frontend to Cloudflare Pages**
   - The `public/` folder contains your frontend
   - Deploy this folder to Cloudflare Pages
   - Or use the existing mod-depot.pages.dev

### Step 3: Test the Connection

1. **Test Local Development**
   - Run the Flask app locally: `python app.py`
   - Open `http://127.0.0.1:5000` in your browser
   - Test single mod search and download

2. **Test Production**
   - Visit `https://mod-depot.pages.dev`
   - The frontend should connect to your Railway backend
   - Test the same functionality

## 🔧 Configuration Files

### `Procfile`
Tells Railway how to run the application:
```
web: python app.py
```

### `railway.json`
Railway configuration for build and deployment:
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "healthcheckPath": "/",
    "healthcheckTimeout": 100
  }
}
```

### `requirements.txt`
Python dependencies that Railway will install automatically.

### `app.py` 
Flask application with CORS configured for Cloudflare Pages.

## 🌐 Architecture

```
Cloudflare Pages (Frontend)
    ↓ HTTPS requests
Railway (Flask Backend)
    ↓ CurseForge API
CurseForge (Mod Downloads)
```

## 📝 File Structure

```
ModDepot/
├── app.py                          # Flask backend
├── curseforge_downloader_module.py  # Core download logic
├── requirements.txt                # Python dependencies
├── Procfile                        # Railway deployment config
├── railway.json                    # Railway build config
├── .gitignore                      # Git ignore rules
├── public/                         # Frontend for Cloudflare Pages
│   └── index.html                  # Frontend application
├── downloads/                      # Downloaded mods (auto-created)
└── uploads/                        # Temporary uploads (auto-created)
```

## 🛠️ Troubleshooting

### CORS Errors
- Ensure your Railway URL is correctly set in `public/index.html`
- Check that CORS is properly configured in `app.py`
- Verify the Railway backend is accessible

### Deployment Failures
- Check Railway logs for build errors
- Ensure all dependencies are in `requirements.txt`
- Verify Python version compatibility

### Connection Issues
- Test Railway backend directly: `https://your-railway-url.railway.app/`
- Check Railway logs for runtime errors
- Verify API endpoints are responding

## 💰 Costs

- **Railway**: Free tier available ($5/month after free credits)
- **Cloudflare Pages**: Free hosting
- **CurseForge API**: Free (using provided API key)

## 🎯 Next Steps

1. Deploy backend to Railway
2. Update frontend API URL
3. Test end-to-end functionality
4. Share your mod-depot.pages.dev URL!

---

**Need help?** Check Railway documentation at [docs.railway.app](https://docs.railway.app)
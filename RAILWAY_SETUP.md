# Railway Deployment Setup for Project dd1b014e-9889-4fe0-8e70-b0484b2ba7aa

## 🚀 Quick Deployment Steps

### Option 1: GitHub Deployment (Recommended)

1. **Initialize Git Repository**
   ```bash
   cd "D:\programing\ModDepot"
   git init
   git add .
   git commit -m "Initial commit - CurseForge Mod Downloader"
   ```

2. **Create GitHub Repository**
   - Go to [github.com](https://github.com) and create a new repository
   - Name it something like "curseforge-mod-downloader"
   - Don't initialize with README (we already have files)

3. **Connect to GitHub**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/curseforge-mod-downloader.git
   git branch -M main
   git push -u origin main
   ```

4. **Connect to Railway**
   - Go to your Railway project: https://railway.com/project/dd1b014e-9889-4fe0-8e70-b0484b2ba7aa
   - Click "New Service" → "Deploy from GitHub repo"
   - Select your curseforge-mod-downloader repository
   - Railway will automatically detect the Python app
   - Click "Deploy"

### Option 2: Railway CLI Deployment

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway**
   ```bash
   railway login
   ```

3. **Link to Your Project**
   ```bash
   cd "D:\programing\ModDepot"
   railway link dd1b014e-9889-4fe0-8e70-b0484b2ba7aa
   ```

4. **Deploy**
   ```bash
   railway up
   ```

### Option 3: Manual Upload

1. Go to your Railway project
2. Click "New Service" → "Empty Service"
3. Go to the "Settings" tab of the new service
4. Click "Upload" and upload all files from ModDepot folder
5. Railway will detect the Python app and deploy

## 🔧 After Deployment

### Get Your Railway URL

Once deployed, Railway will provide a URL like:
- `https://curseforge-downloader-production.up.railway.app`
- Or a custom domain if you configured one

### Update Frontend

1. Open `public/index.html`
2. Find line 355 and update the Railway URL:
```javascript
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://127.0.0.1:5000/api' 
    : 'https://YOUR-RAILWAY-URL.railway.app/api'; // Replace with your actual Railway URL
```

### Deploy Frontend to Cloudflare Pages

1. Go to your Cloudflare Pages project (mod-depot.pages.dev)
2. Upload the `public/` folder contents
3. Or connect to the GitHub repository if you used Option 1

## 🧪 Testing

### Test Backend Directly
```
https://your-railway-url.railway.app/
```

### Test Frontend
```
https://mod-depot.pages.dev
```

### Test API Endpoints
```
https://your-railway-url.railway.app/api/search/mods?q=JEI
```

## 📊 Monitoring

- Check Railway logs for any errors
- Monitor usage on Railway dashboard
- Check CORS configuration if frontend can't connect

## 🆘 Troubleshooting

### Build Failures
- Check Railway logs for specific errors
- Ensure all dependencies are in requirements.txt
- Verify Python version compatibility

### Connection Issues
- Verify CORS configuration in app.py
- Check that Railway URL is correct in frontend
- Test Railway backend directly first

### Port Issues
- Railway automatically assigns ports
- The app.py is configured to use the PORT environment variable
- No manual port configuration needed

---

**Your Railway Project ID:** dd1b014e-9889-4fe0-8e70-b0484b2ba7aa
**Environment ID:** 7e60aa7e-7b31-45a9-ad07-947fa04a4421
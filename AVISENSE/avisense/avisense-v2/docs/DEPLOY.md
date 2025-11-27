# Avisense Deployment Guide

## Prerequisites

- Supabase account
- Render/Fly.io account (for backend)
- Vercel account (for frontend)
- GitHub repository

## Step 1: Supabase Setup

### 1.1 Create Project
1. Go to [supabase.com](https://supabase.com)
2. Click "New Project"
3. Choose organization and region
4. Set database password (save securely)
5. Wait for project to provision (~2 minutes)

### 1.2 Run Database Migration
1. Go to SQL Editor in Supabase Dashboard
2. Copy content from `supabase/migrations/0001_initial.sql`
3. Paste and execute
4. Verify tables created in Table Editor

### 1.3 Configure Authentication
1. Go to Authentication → Providers
2. Enable Email provider
3. Go to Authentication → URL Configuration
4. Add your frontend URL to redirect URLs
5. Go to Authentication → Email Templates
6. Customize confirmation email (optional)

### 1.4 Set Password Policy
1. Go to Authentication → Policies
2. Set minimum password length: 10
3. Require at least 1 number
4. Require at least 1 special character

### 1.5 Create Storage Buckets
1. Go to Storage
2. Create bucket: `model-artifacts`
   - Public: No
   - File size limit: 50MB
3. Create bucket: `telemetry-uploads`
   - Public: No
   - File size limit: 10MB

### 1.6 Upload Model Artifacts
1. Go to Storage → model-artifacts
2. Upload:
   - `avisense_model_cmapss.joblib`
   - `avisense_scaler_cmapss.joblib`
   - `avisense_model_cmapss_info.joblib`

### 1.7 Collect Environment Variables
From Settings → API:
- `SUPABASE_URL`: https://xxxxx.supabase.co
- `SUPABASE_ANON_KEY`: eyJhbGc... (safe for frontend)
- `SUPABASE_SERVICE_ROLE_KEY`: eyJhbGc... (SECRET - backend only)

## Step 2: Backend Deployment (Render)

### 2.1 Prepare Repository
```bash
# Push to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

### 2.2 Deploy to Render
1. Go to [render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect GitHub repository
4. Configure:
   - **Name**: avisense-backend
   - **Environment**: Docker
   - **Region**: Choose closest to users
   - **Branch**: main
   - **Root Directory**: backend
   - **Dockerfile Path**: backend/Dockerfile

### 2.3 Set Environment Variables
Add in Render dashboard:
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
MODEL_PATH=/app/models
ALLOWED_ORIGINS=https://your-frontend.vercel.app
LOG_LEVEL=INFO
```

### 2.4 Deploy
1. Click "Create Web Service"
2. Wait for build and deployment (~5 minutes)
3. Note the backend URL: `https://avisense-backend.onrender.com`

### 2.5 Verify Deployment
```bash
curl https://avisense-backend.onrender.com/health
```

Should return:
```json
{
  "ok": true,
  "model_loaded": true,
  "model_version": "v1.0.0"
}
```

## Step 3: Frontend Deployment (Vercel)

### 3.1 Deploy to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Click "Add New" → "Project"
3. Import GitHub repository
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: frontend
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### 3.2 Set Environment Variables
Add in Vercel dashboard:
```
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=<your-anon-key>
VITE_API_BASE_URL=https://avisense-backend.onrender.com
```

### 3.3 Deploy
1. Click "Deploy"
2. Wait for build (~2 minutes)
3. Note the frontend URL: `https://avisense.vercel.app`

### 3.4 Update Supabase Redirect URLs
1. Go to Supabase → Authentication → URL Configuration
2. Add:
   - Site URL: `https://avisense.vercel.app`
   - Redirect URLs: `https://avisense.vercel.app/**`

### 3.5 Update Backend CORS
Update Render environment variable:
```
ALLOWED_ORIGINS=https://avisense.vercel.app
```

## Step 4: Testing

### 4.1 Test Authentication
1. Go to `https://avisense.vercel.app`
2. Click "Sign Up"
3. Create account
4. Verify email (check inbox)
5. Log in
6. Should see Dashboard

### 4.2 Test RLS
1. Create two test accounts
2. Add engine as User A
3. Log in as User B
4. Verify User B cannot see User A's engines

### 4.3 Test Prediction
1. Add an engine
2. Click on engine
3. Make a prediction
4. Verify prediction appears in history

## Step 5: Monitoring

### 5.1 Supabase Monitoring
- Go to Supabase → Database → Logs
- Monitor query performance
- Set up email alerts for errors

### 5.2 Render Monitoring
- Go to Render dashboard
- Monitor logs and metrics
- Set up email alerts for downtime

### 5.3 Vercel Monitoring
- Go to Vercel dashboard
- Monitor deployment logs
- Check Analytics for usage

## Step 6: Optional Enhancements

### 6.1 Custom Domain
**Vercel:**
1. Go to Project Settings → Domains
2. Add custom domain
3. Update DNS records

**Render:**
1. Go to Service Settings → Custom Domain
2. Add domain
3. Update DNS records

### 6.2 Sentry Integration
```bash
# Backend
pip install sentry-sdk[fastapi]

# Add to app/main.py
import sentry_sdk
sentry_sdk.init(dsn="<your-sentry-dsn>")
```

### 6.3 Enable Supabase Realtime
```sql
-- In Supabase SQL Editor
ALTER PUBLICATION supabase_realtime ADD TABLE predictions;
```

## Troubleshooting

### Backend won't start
- Check Render logs
- Verify environment variables
- Ensure model files are accessible

### Frontend can't connect to backend
- Check CORS settings
- Verify API_BASE_URL
- Check browser console for errors

### Authentication fails
- Verify Supabase URL and keys
- Check redirect URLs
- Ensure email confirmation is working

### Predictions fail
- Check backend logs
- Verify model is loaded
- Test /health endpoint

## Security Checklist

- [ ] Service role key is only in backend environment
- [ ] HTTPS enforced on all endpoints
- [ ] RLS policies tested
- [ ] Password policy configured
- [ ] Email verification enabled
- [ ] CORS properly configured
- [ ] Secrets rotated regularly

## Maintenance

### Update Model
1. Upload new model to Supabase Storage
2. Update MODEL_PATH or download in backend
3. Restart backend service

### Database Migrations
1. Create new migration file
2. Test locally
3. Run in Supabase SQL Editor
4. Verify with test queries

### Monitoring
- Check logs daily
- Monitor error rates
- Review performance metrics
- Update dependencies monthly

## Support

For issues:
1. Check logs in Render/Vercel
2. Check Supabase logs
3. Review error messages
4. Consult documentation

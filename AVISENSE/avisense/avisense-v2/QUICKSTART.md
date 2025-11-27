# 🚀 Avisense Quick Start Guide

## ✅ Configuration Complete!

Your environment is now configured with Supabase credentials.

---

## 📋 Step 1: Run Database Migration

**IMPORTANT**: You must run this first before starting the app!

1. Go to: https://supabase.com/dashboard/project/hfstsqtwahzudqpuyvhw/sql/new

2. Open the file: `supabase/migrations/0001_initial.sql`

3. Copy the **entire content** (all ~350 lines)

4. Paste into the Supabase SQL Editor

5. Click **"Run"** to execute

6. Verify success: You should see tables created in the Table Editor

---

## 🖥️ Step 2: Start the Backend

Open a terminal and run:

```bash
cd /Users/dakshupadhayay/Desktop/engine-failure-detection-/AVISENSE/avisense/avisense-v2/backend

# Create virtual environment (first time only)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Start the backend
python3 -m uvicorn app.main:app --reload --port 8000
```

You should see:
```
🚀 Avisense C-MAPSS Prediction API
Model: RandomForest_CMAPSS
Safe Recall: 97.6%
Failure Recall: 86.9%
Starting Flask server on http://localhost:8000
```

**Keep this terminal open!**

---

## 🌐 Step 3: Start the Frontend

Open a **new terminal** and run:

```bash
cd /Users/dakshupadhayay/Desktop/engine-failure-detection-/AVISENSE/avisense/avisense-v2/frontend

# Install dependencies (first time only)
npm install

# Start the frontend
npm run dev
```

You should see:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
```

**Keep this terminal open too!**

---

## 🎉 Step 4: Test the Application

1. Open your browser to: **http://localhost:5173**

2. You should see the Avisense landing page

3. Click **"Sign Up"** in the top right

4. Create an account:
   - Email: your-email@example.com
   - Password: Test123!@# (min 10 chars, 1 number, 1 special char)
   - Organization: Your Company
   - Full Name: Your Name (optional)

5. Click **"Sign Up"**

6. You should be redirected to the **Dashboard**

7. Click **"Add Engine"** to add your first engine

---

## 🔍 Verify Everything Works

### Check Backend Health
```bash
curl http://localhost:8000/health
```

Should return:
```json
{
  "ok": true,
  "model_loaded": true,
  "model_version": "v1.0.0"
}
```

### Check Supabase Connection
1. Go to: https://supabase.com/dashboard/project/hfstsqtwahzudqpuyvhw/editor
2. Click on `profiles` table
3. You should see your user profile after signup

---

## 🐛 Troubleshooting

### Backend won't start
- Make sure you're in the `backend` directory
- Check that virtual environment is activated (you should see `(venv)` in terminal)
- Verify `.env` file exists with correct values
- Make sure models are in `backend/models/` directory

### Frontend won't start
- Make sure you're in the `frontend` directory
- Run `npm install` if you haven't
- Check that `.env` file exists
- Verify port 5173 is not already in use

### Can't sign up
- Make sure database migration ran successfully
- Check backend terminal for errors
- Verify Supabase credentials are correct
- Check browser console (F12) for errors

### "Model not found" error
- Verify model files are in `backend/models/`:
  - `avisense_model_cmapss.joblib`
  - `avisense_scaler_cmapss.joblib`
  - `avisense_model_cmapss_info.joblib`

---

## 📚 Next Steps

Once everything is working:

1. **Add an Engine**: Click "Add Engine" on the dashboard
2. **Make a Prediction**: Use the sample data from `CMAPSS_QUICKSTART.md`
3. **View History**: See your prediction results
4. **Explore**: Check out the different pages

---

## 🎯 Sample Test Data

Use this data to test a **SAFE** engine prediction:

```json
{
  "setting_1": 0.0007,
  "setting_2": 0.0004,
  "setting_3": 100.0,
  "sensor_2": 642.5,
  "sensor_3": 1589.7,
  "sensor_4": 1400.6,
  "sensor_7": 554.4,
  "sensor_9": 2388.0,
  "sensor_11": 47.5,
  "sensor_12": 521.7,
  "sensor_14": 2388.1,
  "sensor_17": 392.0,
  "sensor_20": 38.9,
  "sensor_21": 23.4
}
```

---

## 📞 Need Help?

- Check the `README.md` for detailed documentation
- Review `docs/DEPLOY.md` for deployment instructions
- Look at `walkthrough.md` for implementation details

**Happy coding! 🚀**

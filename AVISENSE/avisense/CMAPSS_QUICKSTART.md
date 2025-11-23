# C-MAPSS Integration - Quick Start Guide

## Starting the Backend

1. Open a terminal in the `avisense` directory
2. Run the Flask backend:
   ```bash
   cd backend
   python3 app.py
   ```
3. You should see:
   ```
   🚀 Avisense C-MAPSS Prediction API
   Model: RandomForest_CMAPSS
   Safe Recall: 97.6%
   Failure Recall: 86.9%
   
   Starting Flask server on http://localhost:5001
   ```

## Starting the Frontend

1. Open another terminal in the `avisense` directory
2. Run the React frontend:
   ```bash
   npm run dev
   ```
3. Open http://localhost:5173 in your browser

## Testing the Integration

1. Fill in the C-MAPSS sensor values in the Quick Check form
2. Click "Analyze Engine"
3. The frontend will call the Flask backend
4. You'll see a prediction with 96%+ accuracy!

## Sample Test Data

Use these values to test a **SAFE** engine:
- Setting 1: 0.0007
- Setting 2: 0.0004  
- Setting 3: 100.0
- Sensor 2: 642.5
- Sensor 3: 1589.7
- Sensor 4: 1400.6
- Sensor 7: 554.4
- Sensor 9: 2388.0
- Sensor 11: 47.5
- Sensor 12: 521.7
- Sensor 14: 2388.1
- Sensor 17: 392.0
- Sensor 20: 38.9
- Sensor 21: 23.4

Use these values to test a **FAILURE** engine (Unit 39, Cycle 123, RUL 5):
- Setting 1: 0.0007
- Setting 2: 0.0002
- Setting 3: 100.0
- Sensor 2: 643.56
- Sensor 3: 1606.05
- Sensor 4: 1429.54
- Sensor 7: 551.8
- Sensor 9: 9033.19
- Sensor 11: 48.0
- Sensor 12: 519.59
- Sensor 14: 8113.65
- Sensor 17: 394.0
- Sensor 20: 38.62
- Sensor 21: 23.17

## Troubleshooting

**Backend not starting?**
- Make sure Flask is installed: `pip3 install flask flask-cors`
- Check that you're in the `backend` directory

**Frontend can't connect?**
- Make sure the backend is running on port 5001
- Check browser console for CORS errors
- Verify API_BASE_URL in `src/services/api.js` is `http://localhost:5001`

**Model not found?**
- Make sure `avisense_model_cmapss.joblib` is in the `avisense` directory
- Run `python3 train_cmapss_model.py` to retrain if needed

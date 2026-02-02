# Avisense - Production-Ready Engine Failure Prediction Platform

Full-stack application for predicting aircraft engine failures using ML models trained on NASA C-MAPSS data.

## 🚀 Features

- **Authentication**: Supabase Auth with email/password, password validation
- **Multi-tenant**: Row-Level Security (RLS) for data isolation
- **ML Predictions**: RandomForest model with 97.6% safe recall, 86.9% failure recall
- **Real-time Updates**: Supabase Realtime for live prediction updates
- **Anomaly Detection**: Sensor threshold-based anomaly detection
- **Rate Limiting**: 10 requests/minute per user
- **Docker Support**: Full containerization for backend
- **Modern UI**: React + Tailwind CSS with responsive design

## 📁 Project Structure

```
avisense-v2/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── ml/             # ML model logic
│   │   ├── config.py       # Configuration
│   │   └── main.py         # FastAPI app
│   ├── tests/              # Unit tests
│   ├── models/             # ML artifacts (.joblib files)
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/               # React + Vite frontend
│   ├── src/
│   │   ├── pages/          # Landing, Signup, Login, Dashboard
│   │   ├── components/     # Reusable components
│   │   ├── hooks/          # useAuth hook
│   │   ├── lib/            # Supabase client
│   │   └── services/       # API service
│   └── tailwind.config.js
├── supabase/
│   └── migrations/
│       └── 0001_initial.sql  # Database schema
└── docs/
    └── DEPLOY.md           # Deployment guide
```

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: Supabase (Postgres)
- **Auth**: Supabase Auth (JWT)
- **ML**: scikit-learn, joblib
- **Containerization**: Docker

### Frontend
- **Framework**: React 19 + Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router
- **State**: React hooks
- **Icons**: Lucide React

## 🏃 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase account
- Docker (optional)

### 1. Supabase Setup

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Run the migration SQL:
   ```bash
   # Copy content from supabase/migrations/0001_initial.sql
   # Paste into Supabase SQL Editor and execute
   ```
3. Configure Auth settings:
   - Enable Email/Password provider
   - Set password policy: min 10 chars, 1 number, 1 special char
4. Create storage buckets:
   - `model-artifacts` (for .joblib files)
   - `telemetry-uploads` (for CSV/JSON)

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your Supabase credentials
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Run backend
python3 -m uvicorn app.main:app --reload --port 8000
```

**Or use Docker:**
```bash
cd backend
docker-compose up --build
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env with your Supabase credentials
# VITE_SUPABASE_URL=https://your-project.supabase.co
# VITE_SUPABASE_ANON_KEY=your-anon-key
# VITE_API_BASE_URL=http://localhost:8000

# Run frontend
npm run dev
```

Frontend will be available at `http://localhost:5173`

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
pytest --cov=app tests/
```

### Frontend (to be implemented)
```bash
cd frontend
npm run test
```

## 📊 API Endpoints

### Health Check
```
GET /health
```

### Prediction
```
POST /predict
Authorization: Bearer <jwt-token>

{
  "engine_id": "<uuid>",
  "input_data": {
    "setting_1": 0.0007,
    "setting_2": 0.0004,
    "setting_3": 100.0,
    "sensor_2": 642.5,
    ...
  }
}
```

## 🔐 Security

- **RLS**: All database tables have Row-Level Security enabled
- **JWT Auth**: Supabase JWT tokens for authentication
- **Rate Limiting**: 10 requests/minute per user
- **Password Policy**: Min 10 chars, 1 number, 1 special char
- **Service Role Key**: Never exposed to frontend

## 🚢 Deployment

See [docs/DEPLOY.md](docs/DEPLOY.md) for detailed deployment instructions.

**Quick Deploy:**
- **Backend**: Deploy to Render/Fly.io using Docker
- **Frontend**: Deploy to Vercel (auto-deploy from GitHub)

## 📝 Environment Variables

### Backend
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Service role key (SECRET)
- `MODEL_PATH` - Path to model artifacts
- `ALLOWED_ORIGINS` - CORS allowed origins

### Frontend
- `VITE_SUPABASE_URL` - Supabase project URL
- `VITE_SUPABASE_ANON_KEY` - Supabase anon key (safe for frontend)
- `VITE_API_BASE_URL` - Backend API URL

## 🎯 Roadmap

- [x] Backend API with FastAPI
- [x] Supabase database schema
- [x] Authentication (Signup/Login)
- [x] Dashboard with engine list
- [ ] Engine detail page
- [ ] Make Prediction modal
- [ ] Telemetry charts
- [ ] Prediction history
- [ ] Realtime updates
- [ ] E2E tests
- [ ] CI/CD pipeline


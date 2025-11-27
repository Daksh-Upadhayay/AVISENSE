# Avisense Backend API

Production-ready FastAPI backend for engine failure prediction with ML model serving.

## Features

- 🤖 ML model serving (RandomForest on NASA C-MAPSS dataset)
- 🔐 JWT authentication with Supabase
- 🛡️ Row-Level Security (RLS) for multi-tenant data isolation
- 📊 Anomaly detection with sensor thresholds
- ⚡ Rate limiting (10 req/min per user)
- 🐳 Docker support
- ✅ Unit and integration tests
- 📝 OpenAPI documentation

## Quick Start

### Prerequisites

- Python 3.11+
- Supabase project (for database and auth)
- Model artifacts (`.joblib` files)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your Supabase credentials
```

### Running Locally

```bash
# Run with uvicorn
python3 -m uvicorn app.main:app --reload --port 8000

# Or use the main script
python3 -m app.main
```

### Running with Docker

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## API Endpoints

### Health Check
```bash
GET /health
```

Returns model status and version.

### Prediction
```bash
POST /predict
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "engine_id": "<engine-uuid>",
  "input_data": {
    "setting_1": 0.0007,
    "setting_2": 0.0004,
    "setting_3": 100.0,
    "sensor_2": 642.5,
    ...
  },
  "source": "ui"
}
```

Returns prediction with anomalies and recommended actions.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_predictor.py
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (SECRET) | Yes |
| `MODEL_PATH` | Path to model artifacts | Yes |
| `API_HOST` | API host (default: 0.0.0.0) | No |
| `API_PORT` | API port (default: 8000) | No |
| `ALLOWED_ORIGINS` | CORS allowed origins | No |
| `SENTRY_DSN` | Sentry DSN for error tracking | No |
| `LOG_LEVEL` | Logging level (default: INFO) | No |

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py          # Auth dependencies
│   │   ├── health.py        # Health endpoint
│   │   └── predict.py       # Prediction endpoint
│   ├── ml/
│   │   ├── model_loader.py  # Model loading
│   │   ├── predictor.py     # Prediction logic
│   │   └── anomaly.py       # Anomaly detection
│   ├── config.py            # Settings
│   ├── models.py            # Pydantic models
│   └── main.py              # FastAPI app
├── tests/
│   ├── test_predictor.py
│   └── test_anomaly.py
├── models/                  # Model artifacts
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Deployment

See [docs/DEPLOY.md](../docs/DEPLOY.md) for deployment instructions.

## License

MIT

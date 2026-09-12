# Avisense

Avisense estimates the **remaining useful life (RUL)** of turbofan engines from their cycle-by-cycle sensor history, and explains every estimate in terms an engineer can check:

- an RUL estimate with a calibrated 80% range,
- the probability of failure within the next 30 cycles,
- exact SHAP contributions showing which sensors moved the estimate, and by how many cycles,
- per-sensor drift from the engine's own starting level, compared with the drift typically seen just before failure.

It is trained and tested on NASA's C-MAPSS turbofan degradation data (all four subsets, FD001–FD004). A demo fleet replays NASA test engines one cycle at a time, so every prediction can be compared with the real outcome.

## Accuracy

Measured on the official C-MAPSS test sets (707 engines never seen in training). RUL is scored at each engine's last recorded cycle, with the truth capped at 125 cycles as in most C-MAPSS papers. Failure metrics cover every test cycle.

| Test set | RMSE (cycles) | MAE | NASA score | 80% range coverage | PR-AUC | Recall | Precision |
|---|---|---|---|---|---|---|---|
| FD001 | 10.86 | 7.48 | 187 | 84% | 0.976 | 93% | 90% |
| FD002 | 10.80 | 7.48 | 548 | 81% | 0.974 | 89% | 93% |
| FD003 | 10.76 | 7.50 | 223 | 83% | 0.982 | 94% | 88% |
| FD004 | 10.98 | 7.18 | 574 | 78% | 0.921 | 86% | 85% |

One model covers all four subsets. Near failure (true RUL under 25 cycles) the mean absolute error is 3.3 cycles. The app's **Model** page shows these numbers live from the deployed model, along with calibration and error charts.

For comparison, the previous version (v2, an LSTM trained on FD001 only) scored an RMSE of 27.8 on FD001 as its API served it, because it repeated a single reading 30 times instead of using the engine's history.

## How it works

1. **Operating-condition normalization.** Every reading is assigned to one of six flight regimes (altitude, Mach, throttle). Each sensor becomes a z-score against the healthy early-life baseline of its regime, which removes the effect of the flight condition.
2. **Features.** For 14 informative sensors: 10- and 30-cycle rolling means, a 20-cycle trend slope, and drift from the engine's own first recorded cycles (engines start with different amounts of wear). Plus cycles in service. Every feature uses only past cycles, and a test guards this.
3. **Models** (LightGBM):
   - RUL regressor, target capped at 125 cycles.
   - Binary classifier for failure within 30 cycles. The alert threshold is set on held-out training engines for 95% recall.
   - The RUL range uses split-conformal calibration per band of predicted RUL on held-out engines, so its coverage is measured, not assumed.
4. **Explanations.** LightGBM's exact TreeSHAP contributions, summed per sensor. They add up exactly to the model output.
5. **Status.** *Critical* when the failure probability is at or above the alert threshold. *Watch* when the low end of the RUL range is 60 cycles or less. *Healthy* otherwise.

Training and evaluation are one script. It saves the models, reloads them through the same class the API uses, and writes the test metrics into the model metadata:

```bash
cd backend
pip install -r requirements-dev.txt
python -m scripts.train      # about 20 seconds
```

## Project layout

```
backend/     FastAPI service, ML pipeline, training script, tests
  app/ml/    dataset catalog, features, model bundle (shared by training and serving)
  models/    trained model + metadata.json (metrics, calibration, policy)
  data/      NASA C-MAPSS files
frontend/    React + Vite + Tailwind + Recharts
supabase/    database schema and row-level security
```

## Running locally

You need Python 3.12, Node 22, and a Supabase project. You can use a hosted project, or run one locally with the [Supabase CLI](https://supabase.com/docs/guides/cli) and Docker.

**1. Database.** Apply `supabase/migrations/20260913000000_avisense_schema.sql`. On a hosted project, paste it into the SQL editor. Locally, `supabase start` applies it. The script is idempotent and also upgrades databases created by v2.

**2. Backend**

```bash
cd backend
cp .env.example .env          # SUPABASE_URL and SUPABASE_ANON_KEY
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:create_app --factory --reload --port 8000
```

**3. Frontend**

```bash
cd frontend
cp .env.example .env          # VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_BASE_URL
npm install
npm run dev
```

Open http://localhost:5180, create an account, and click **Create demo fleet**.

## Security model

The API never uses the Supabase service-role key. It verifies each request's access token with Supabase Auth, then queries the database *as that user*, so Postgres row-level security enforces that users only see their own engines, telemetry and assessments. Keep `.env` files out of git. Only `.env.example` files are committed.

## API

Interactive docs are at `/docs` when the backend is running.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness and model version |
| GET | `/api/model` | Model card: metrics, calibration, policy, limitations |
| GET | `/api/engines` | Your engines with their latest assessment |
| POST | `/api/engines` | Create an engine |
| GET | `/api/engines/{id}` | Engine, live analysis of its full history, saved assessments |
| POST | `/api/engines/{id}/upload` | Upload a CSV or NASA text file of cycles, then assess |
| POST | `/api/engines/{id}/readings` | Append cycles as JSON, then assess |
| POST | `/api/engines/{id}/replay?steps=n` | Advance a demo engine by n cycles, then assess |
| POST | `/api/engines/{id}/assess` | Save an assessment of the current history |
| POST | `/api/fleet/demo` | Create demo engines replayed from NASA test data |
| DELETE | `/api/engines/{id}` | Delete an engine and its data |

Uploads need `cycle`, `setting_1..3` and the 14 model sensors. Column names can be `sensor_N` or the NASA symbol (`T24`, `Ps30`, ...).

## Limitations

- Trained on simulated data. Real engines need retraining on their own run-to-failure records.
- The RUL target is capped at 125 cycles, so engines with no visible degradation read as "125+".
- Drift is measured from the first recorded cycles, so a history that starts mid-life hides earlier wear.
- Only the degradation modes in C-MAPSS (HPC and fan) are represented.

This is a research demonstration, not a certified maintenance tool.

## Data

A. Saxena, K. Goebel, D. Simon, N. Eklund, "Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation", PHM 2008. NASA Prognostics Center of Excellence data repository.

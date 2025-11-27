# Supabase Configuration Guide

## Your Supabase Project

**Project URL**: https://hfstsqtwahzudqpuyvhw.supabase.co

## Required API Keys

You need to get your API keys from the Supabase Dashboard:

1. Go to: https://supabase.com/dashboard/project/hfstsqtwahzudqpuyvhw/settings/api

2. You'll find two keys:
   - **anon (public)** key - Safe to use in frontend
   - **service_role (secret)** key - Only for backend (you provided this)

## Next Steps

### 1. Get Your Anon Key

1. Visit: https://supabase.com/dashboard/project/hfstsqtwahzudqpuyvhw/settings/api
2. Copy the **anon** / **public** key
3. It should start with `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

### 2. Run the Database Migration

1. Go to: https://supabase.com/dashboard/project/hfstsqtwahzudqpuyvhw/sql/new
2. Copy the entire content from: `supabase/migrations/0001_initial.sql`
3. Paste into the SQL Editor
4. Click "Run" to execute the migration
5. Verify tables are created in the Table Editor

### 3. Configure Backend

Update `backend/.env` with your anon key (I've already added the service role key):
```bash
SUPABASE_URL=https://hfstsqtwahzudqpuyvhw.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_tgZa8uzOaJh3VSGugr7zuQ_ATJJrMto
```

### 4. Configure Frontend

Create `frontend/.env`:
```bash
VITE_SUPABASE_URL=https://hfstsqtwahzudqpuyvhw.supabase.co
VITE_SUPABASE_ANON_KEY=<YOUR_ANON_KEY_HERE>
VITE_API_BASE_URL=http://localhost:8000
```

### 5. Start the Application

**Terminal 1 - Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Then visit: http://localhost:5173

## Quick Test

Once both are running:
1. Go to http://localhost:5173
2. Click "Sign Up"
3. Create an account
4. You should be redirected to the Dashboard

## Troubleshooting

If you get errors:
- Make sure the database migration ran successfully
- Verify both .env files have correct values
- Check that both backend and frontend are running
- Look at terminal logs for specific errors

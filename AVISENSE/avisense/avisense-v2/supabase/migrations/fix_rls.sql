-- Fix RLS Policies
-- Run this in Supabase SQL Editor to ensure all policies are correctly applied.

-- 1. Profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles_insert_self" ON public.profiles;
CREATE POLICY "profiles_insert_self" ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "profiles_select_self" ON public.profiles;
CREATE POLICY "profiles_select_self" ON public.profiles FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "profiles_update_self" ON public.profiles;
CREATE POLICY "profiles_update_self" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- 2. Engines
ALTER TABLE public.engines ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "engines_select_owner" ON public.engines;
CREATE POLICY "engines_select_owner" ON public.engines FOR SELECT USING (owner_id = auth.uid());

DROP POLICY IF EXISTS "engines_insert_owner" ON public.engines;
CREATE POLICY "engines_insert_owner" ON public.engines FOR INSERT WITH CHECK (owner_id = auth.uid());

DROP POLICY IF EXISTS "engines_update_owner" ON public.engines;
CREATE POLICY "engines_update_owner" ON public.engines FOR UPDATE USING (owner_id = auth.uid());

DROP POLICY IF EXISTS "engines_delete_owner" ON public.engines;
CREATE POLICY "engines_delete_owner" ON public.engines FOR DELETE USING (owner_id = auth.uid());

-- 3. Telemetry
ALTER TABLE public.telemetry ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "telemetry_select_owner" ON public.telemetry;
CREATE POLICY "telemetry_select_owner" ON public.telemetry FOR SELECT USING (
  engine_id IN (SELECT id FROM public.engines WHERE owner_id = auth.uid())
);

DROP POLICY IF EXISTS "telemetry_insert_owner" ON public.telemetry;
CREATE POLICY "telemetry_insert_owner" ON public.telemetry FOR INSERT WITH CHECK (
  engine_id IN (SELECT id FROM public.engines WHERE owner_id = auth.uid())
);

-- 4. Predictions
ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "predictions_select_owner" ON public.predictions;
CREATE POLICY "predictions_select_owner" ON public.predictions FOR SELECT USING (
  engine_id IN (SELECT id FROM public.engines WHERE owner_id = auth.uid())
);

DROP POLICY IF EXISTS "predictions_insert_owner" ON public.predictions;
CREATE POLICY "predictions_insert_owner" ON public.predictions FOR INSERT WITH CHECK (
  engine_id IN (SELECT id FROM public.engines WHERE owner_id = auth.uid())
);

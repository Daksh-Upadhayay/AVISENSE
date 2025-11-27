-- Migration: 0002_change_org_to_text
-- Description: Change organization_id (UUID) to organization_name (TEXT) in profiles table

ALTER TABLE public.profiles
DROP COLUMN IF EXISTS organization_id,
ADD COLUMN IF NOT EXISTS organization_name TEXT;

-- Update engines table to also use organization_name if needed, or leave as is (it has organization_id too)
-- For now, let's just fix profiles as that's what signup uses.

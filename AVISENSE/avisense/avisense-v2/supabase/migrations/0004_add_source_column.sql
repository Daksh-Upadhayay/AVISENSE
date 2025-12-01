-- Add source column to predictions table
ALTER TABLE public.predictions
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'ui';

-- Add index for filtering by source
CREATE INDEX IF NOT EXISTS idx_predictions_source ON public.predictions(source);

COMMENT ON COLUMN public.predictions.source IS 'Source of the prediction (ui, manual, api, etc.)';

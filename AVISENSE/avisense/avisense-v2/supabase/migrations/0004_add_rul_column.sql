-- Add rul_prediction column to predictions table
ALTER TABLE predictions 
ADD COLUMN IF NOT EXISTS rul_prediction float;

-- Add comment
COMMENT ON COLUMN predictions.rul_prediction IS 'Predicted Remaining Useful Life (RUL) in cycles';

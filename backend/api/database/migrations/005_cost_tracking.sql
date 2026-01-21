-- Migration: Add cost tracking columns
-- Bead: story-csz1 - Implement cost tracking for story generation

-- Add usage_json and cost_usd to stories table
ALTER TABLE stories
ADD COLUMN IF NOT EXISTS usage_json JSONB,
ADD COLUMN IF NOT EXISTS cost_usd DECIMAL(10,6);

-- Add usage_json and cost_usd to spread_regen_jobs table
ALTER TABLE spread_regen_jobs
ADD COLUMN IF NOT EXISTS usage_json JSONB,
ADD COLUMN IF NOT EXISTS cost_usd DECIMAL(10,6);

-- Comments explaining the columns
COMMENT ON COLUMN stories.usage_json IS 'Raw usage data: llm_input_tokens, llm_output_tokens, llm_model, llm_calls, image_count, image_model, image_retries';
COMMENT ON COLUMN stories.cost_usd IS 'Total cost in USD for this generation';
COMMENT ON COLUMN spread_regen_jobs.usage_json IS 'Raw usage data for this regeneration job';
COMMENT ON COLUMN spread_regen_jobs.cost_usd IS 'Cost in USD for this regeneration';

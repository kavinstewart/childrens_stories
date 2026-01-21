-- Migration: Add present_entity_ids column to story_spreads
-- Bead: story-v0qr - Persist present_entity_ids per spread in database

-- Add present_entity_ids column to store entity IDs for each spread
ALTER TABLE story_spreads
ADD COLUMN IF NOT EXISTS present_entity_ids JSONB;

-- Comment explaining the column
COMMENT ON COLUMN story_spreads.present_entity_ids IS 'Entity IDs visually present in this spread (e.g., ["@e1", "@e2"]). NULL = legacy story, [] = no entities.';

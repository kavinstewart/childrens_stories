-- Migration 001: UUID type for IDs and JSONB for JSON columns
-- Run with: psql -f 001_uuid_and_jsonb.sql -d childrens_stories
--
-- This migration:
-- 1. Changes stories.id from VARCHAR(36) to native UUID type
-- 2. Updates all foreign keys to UUID type
-- 3. Changes JSON columns from TEXT to JSONB

-- Drop foreign key constraints first (they reference the VARCHAR id)
ALTER TABLE story_spreads DROP CONSTRAINT IF EXISTS story_spreads_story_id_fkey;
ALTER TABLE character_references DROP CONSTRAINT IF EXISTS character_references_story_id_fkey;
ALTER TABLE vlm_evaluations DROP CONSTRAINT IF EXISTS vlm_evaluations_story_id_fkey;

-- Convert primary key to UUID
ALTER TABLE stories ALTER COLUMN id TYPE UUID USING id::uuid;

-- Convert foreign keys to UUID
ALTER TABLE story_spreads ALTER COLUMN story_id TYPE UUID USING story_id::uuid;
ALTER TABLE character_references ALTER COLUMN story_id TYPE UUID USING story_id::uuid;
ALTER TABLE vlm_evaluations ALTER COLUMN story_id TYPE UUID USING story_id::uuid;

-- Re-add foreign key constraints
ALTER TABLE story_spreads
    ADD CONSTRAINT story_spreads_story_id_fkey
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE;

ALTER TABLE character_references
    ADD CONSTRAINT character_references_story_id_fkey
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE;

ALTER TABLE vlm_evaluations
    ADD CONSTRAINT vlm_evaluations_story_id_fkey
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE SET NULL;

-- Convert JSON columns from TEXT to JSONB
ALTER TABLE stories ALTER COLUMN outline_json TYPE JSONB USING outline_json::jsonb;
ALTER TABLE stories ALTER COLUMN judgment_json TYPE JSONB USING judgment_json::jsonb;
ALTER TABLE stories ALTER COLUMN progress_json TYPE JSONB USING progress_json::jsonb;

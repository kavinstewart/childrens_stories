-- Migration 002: Remove unnecessary surrogate keys
-- Run with: psql -f 002_remove_surrogate_keys.sql -d childrens_stories
--
-- This migration:
-- 1. Removes surrogate key from story_spreads, uses (story_id, spread_number) as PK
-- 2. Removes surrogate key from character_references, uses (story_id, character_name) as PK

-- story_spreads: Drop surrogate key, use composite primary key
-- First drop the existing unique constraint (it will become the PK)
ALTER TABLE story_spreads DROP CONSTRAINT IF EXISTS story_spreads_story_id_spread_number_key;

-- Drop the serial primary key
ALTER TABLE story_spreads DROP CONSTRAINT IF EXISTS story_spreads_pkey;
ALTER TABLE story_spreads DROP COLUMN IF EXISTS id;

-- Add composite primary key
ALTER TABLE story_spreads ADD PRIMARY KEY (story_id, spread_number);

-- character_references: Drop surrogate key, use composite primary key
-- First drop the existing unique constraint (it will become the PK)
ALTER TABLE character_references DROP CONSTRAINT IF EXISTS character_references_story_id_character_name_key;

-- Drop the serial primary key
ALTER TABLE character_references DROP CONSTRAINT IF EXISTS character_references_pkey;
ALTER TABLE character_references DROP COLUMN IF EXISTS id;

-- Add composite primary key
ALTER TABLE character_references ADD PRIMARY KEY (story_id, character_name);

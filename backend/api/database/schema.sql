-- PostgreSQL schema for Children's Story Generator
-- Run with: psql -f schema.sql -d your_database

-- Stories table with JSON for complex nested data
CREATE TABLE IF NOT EXISTS stories (
    id UUID PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending/running/completed/failed
    goal TEXT NOT NULL,
    target_age_range VARCHAR(10) DEFAULT '4-7',
    generation_type VARCHAR(20) NOT NULL,  -- simple/standard/illustrated
    llm_model VARCHAR(100),  -- model used for generation
    title TEXT,
    word_count INTEGER,
    spread_count INTEGER,  -- Number of spreads (typically 12)
    attempts INTEGER,
    is_illustrated BOOLEAN DEFAULT FALSE,
    outline_json JSONB,
    judgment_json JSONB,
    progress_json JSONB,
    usage_json JSONB,  -- Cost tracking: llm tokens, image count, models used
    cost_usd DECIMAL(10,6),  -- Total cost in USD for this generation
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Normalized spreads for efficient queries (a spread = two facing pages)
CREATE TABLE IF NOT EXISTS story_spreads (
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    spread_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    word_count INTEGER,
    was_revised BOOLEAN NOT NULL DEFAULT FALSE,
    page_turn_note TEXT,  -- What makes reader want to turn the page
    illustration_prompt TEXT,
    illustration_path TEXT,
    illustration_updated_at TIMESTAMPTZ,  -- When illustration was last regenerated (for cache busting)
    present_entity_ids JSONB,  -- Entity IDs visually present (e.g., ["@e1", "@e2"]). NULL = legacy, [] = no entities.
    PRIMARY KEY (story_id, spread_number)
);

-- Character references for illustrated stories
CREATE TABLE IF NOT EXISTS character_references (
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    character_name VARCHAR(100) NOT NULL,
    character_description TEXT,
    reference_image_path TEXT,
    bible_json JSONB,  -- Full CharacterBible for editing (story-37l6)
    PRIMARY KEY (story_id, character_name)
);

-- Spread regeneration jobs (for individual illustration regeneration)
CREATE TABLE IF NOT EXISTS spread_regen_jobs (
    id VARCHAR(8) PRIMARY KEY,
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    spread_number INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending/running/completed/failed
    progress_json JSONB,
    usage_json JSONB,  -- Cost tracking: image generations and retries
    cost_usd DECIMAL(10,6),  -- Cost in USD for this regeneration
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (story_id, spread_number) REFERENCES story_spreads(story_id, spread_number) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_stories_status ON stories(status);
CREATE INDEX IF NOT EXISTS idx_stories_created_at ON stories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_story_spreads_story_id ON story_spreads(story_id);
CREATE INDEX IF NOT EXISTS idx_character_refs_story_id ON character_references(story_id);
CREATE INDEX IF NOT EXISTS idx_spread_regen_jobs_story_spread ON spread_regen_jobs(story_id, spread_number);
CREATE INDEX IF NOT EXISTS idx_spread_regen_jobs_status ON spread_regen_jobs(status);

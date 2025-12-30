-- PostgreSQL schema for Children's Story Generator
-- Run with: psql -f schema.sql -d your_database

-- Stories table with JSON for complex nested data
CREATE TABLE IF NOT EXISTS stories (
    id VARCHAR(36) PRIMARY KEY,
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
    outline_json TEXT,
    judgment_json TEXT,
    progress_json TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Normalized spreads for efficient queries (a spread = two facing pages)
CREATE TABLE IF NOT EXISTS story_spreads (
    id SERIAL PRIMARY KEY,
    story_id VARCHAR(36) NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    spread_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    word_count INTEGER,
    was_revised BOOLEAN DEFAULT FALSE,
    page_turn_note TEXT,  -- What makes reader want to turn the page
    illustration_prompt TEXT,
    illustration_path TEXT,
    UNIQUE(story_id, spread_number)
);

-- Character references for illustrated stories
CREATE TABLE IF NOT EXISTS character_references (
    id SERIAL PRIMARY KEY,
    story_id VARCHAR(36) NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    character_name VARCHAR(100) NOT NULL,
    character_description TEXT,
    reference_image_path TEXT,
    UNIQUE(story_id, character_name)
);

-- VLM Judge evaluations for optimization training data
CREATE TABLE IF NOT EXISTS vlm_evaluations (
    id VARCHAR(8) PRIMARY KEY,
    story_id VARCHAR(36) REFERENCES stories(id) ON DELETE SET NULL,
    spread_number INTEGER,

    -- Input context
    prompt TEXT NOT NULL,
    image_path TEXT NOT NULL,
    character_ref_paths TEXT,  -- JSON array of paths
    check_text_free BOOLEAN DEFAULT TRUE,
    check_characters BOOLEAN DEFAULT TRUE,
    check_composition BOOLEAN DEFAULT TRUE,

    -- VLM output
    vlm_model VARCHAR(100) NOT NULL,
    vlm_raw_response TEXT,  -- Raw JSON from VLM
    vlm_overall_pass BOOLEAN,
    vlm_text_free BOOLEAN,
    vlm_character_match_score INTEGER,
    vlm_scene_accuracy_score INTEGER,
    vlm_composition_score INTEGER,
    vlm_style_score INTEGER,
    vlm_issues TEXT,  -- JSON array

    -- Human annotation (null until reviewed)
    human_verdict BOOLEAN,  -- null=not reviewed
    human_notes TEXT,
    annotated_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_stories_status ON stories(status);
CREATE INDEX IF NOT EXISTS idx_stories_created_at ON stories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_story_spreads_story_id ON story_spreads(story_id);
CREATE INDEX IF NOT EXISTS idx_character_refs_story_id ON character_references(story_id);
CREATE INDEX IF NOT EXISTS idx_vlm_evals_story_id ON vlm_evaluations(story_id);
CREATE INDEX IF NOT EXISTS idx_vlm_evals_unannotated ON vlm_evaluations(human_verdict) WHERE human_verdict IS NULL;

-- Stories table with JSON for complex nested data
CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/running/completed/failed
    goal TEXT NOT NULL,
    target_age_range TEXT DEFAULT '4-7',
    generation_type TEXT NOT NULL,  -- simple/standard/illustrated
    llm_model TEXT,  -- model used for generation (e.g., 'claude-opus-4-5-20251101')
    title TEXT,
    word_count INTEGER,
    spread_count INTEGER,  -- Number of spreads (typically 12)
    attempts INTEGER,
    is_illustrated INTEGER DEFAULT 0,
    outline_json TEXT,
    judgment_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT
);

-- Normalized spreads for efficient queries (a spread = two facing pages)
CREATE TABLE IF NOT EXISTS story_spreads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id TEXT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    spread_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    word_count INTEGER,
    was_revised INTEGER DEFAULT 0,
    page_turn_note TEXT,  -- What makes reader want to turn the page
    illustration_prompt TEXT,
    illustration_path TEXT,
    UNIQUE(story_id, spread_number)
);

-- Character references for illustrated stories
CREATE TABLE IF NOT EXISTS character_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id TEXT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    character_name TEXT NOT NULL,
    character_description TEXT,
    reference_image_path TEXT,
    UNIQUE(story_id, character_name)
);

-- VLM Judge evaluations for optimization training data
CREATE TABLE IF NOT EXISTS vlm_evaluations (
    id TEXT PRIMARY KEY,
    story_id TEXT REFERENCES stories(id) ON DELETE SET NULL,
    spread_number INTEGER,

    -- Input context
    prompt TEXT NOT NULL,
    image_path TEXT NOT NULL,
    character_ref_paths TEXT,  -- JSON array of paths
    check_text_free INTEGER DEFAULT 1,
    check_characters INTEGER DEFAULT 1,
    check_composition INTEGER DEFAULT 1,

    -- VLM output
    vlm_model TEXT NOT NULL,
    vlm_raw_response TEXT,  -- Raw JSON from VLM
    vlm_overall_pass INTEGER,  -- 0 or 1
    vlm_text_free INTEGER,
    vlm_character_match_score INTEGER,
    vlm_scene_accuracy_score INTEGER,
    vlm_composition_score INTEGER,
    vlm_style_score INTEGER,
    vlm_issues TEXT,  -- JSON array

    -- Human annotation (null until reviewed)
    human_verdict INTEGER,  -- 0=fail, 1=pass, null=not reviewed
    human_notes TEXT,
    annotated_at TEXT,

    created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_stories_status ON stories(status);
CREATE INDEX IF NOT EXISTS idx_stories_created_at ON stories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_story_spreads_story_id ON story_spreads(story_id);
CREATE INDEX IF NOT EXISTS idx_character_refs_story_id ON character_references(story_id);
CREATE INDEX IF NOT EXISTS idx_vlm_evals_story_id ON vlm_evaluations(story_id);
CREATE INDEX IF NOT EXISTS idx_vlm_evals_unannotated ON vlm_evaluations(human_verdict) WHERE human_verdict IS NULL;

-- Stories table with JSON for complex nested data
CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/running/completed/failed
    goal TEXT NOT NULL,
    target_age_range TEXT DEFAULT '4-7',
    generation_type TEXT NOT NULL,  -- simple/standard/illustrated
    title TEXT,
    word_count INTEGER,
    page_count INTEGER,
    attempts INTEGER,
    is_illustrated INTEGER DEFAULT 0,
    outline_json TEXT,
    judgment_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT
);

-- Normalized pages for efficient queries
CREATE TABLE IF NOT EXISTS story_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id TEXT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    word_count INTEGER,
    was_revised INTEGER DEFAULT 0,
    illustration_prompt TEXT,
    illustration_path TEXT,
    UNIQUE(story_id, page_number)
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

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_stories_status ON stories(status);
CREATE INDEX IF NOT EXISTS idx_stories_created_at ON stories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_story_pages_story_id ON story_pages(story_id);
CREATE INDEX IF NOT EXISTS idx_character_refs_story_id ON character_references(story_id);

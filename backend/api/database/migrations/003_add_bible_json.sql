-- Migration: Add bible_json column to character_references
-- Story: story-37l6 - Store full CharacterBible in database for editing

-- Add bible_json column to store full CharacterBible data
ALTER TABLE character_references
ADD COLUMN IF NOT EXISTS bible_json JSONB;

-- Comment explaining the column
COMMENT ON COLUMN character_references.bible_json IS 'Full CharacterBible data as JSONB for editing (hair, eyes, clothing, signature_item, color_palette, style_tags, etc.)';

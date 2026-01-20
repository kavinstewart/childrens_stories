# Story Database Quick Reference

Supplementary reference for the `/story` skill with additional queries and schema details.

## Database Schema

### stories
Main story records.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `status` | VARCHAR(20) | pending/running/completed/failed |
| `goal` | TEXT | Learning theme or educational objective |
| `target_age_range` | VARCHAR(10) | Default "4-7" |
| `generation_type` | VARCHAR(20) | simple/standard/illustrated |
| `llm_model` | VARCHAR(100) | Model used (e.g., claude-opus-4-5) |
| `title` | TEXT | Generated story title |
| `word_count` | INTEGER | Total words across all spreads |
| `spread_count` | INTEGER | Number of spreads (typically 12) |
| `attempts` | INTEGER | Generation attempts |
| `is_illustrated` | BOOLEAN | Whether illustrations were generated |
| `outline_json` | JSONB | Metadata: title, illustration_style, entity_definitions |
| `progress_json` | JSONB | Progress tracking during generation |
| `error_message` | TEXT | Error details if failed |
| `created_at` | TIMESTAMPTZ | When created |
| `started_at` | TIMESTAMPTZ | When generation started |
| `completed_at` | TIMESTAMPTZ | When completed/failed |

### story_spreads
Individual spreads (two facing pages).

| Column | Type | Description |
|--------|------|-------------|
| `story_id` | UUID | FK to stories |
| `spread_number` | INTEGER | 1-12 typically |
| `text` | TEXT | Story content (35-50 words) |
| `word_count` | INTEGER | Word count for this spread |
| `was_revised` | BOOLEAN | Whether revised during generation |
| `page_turn_note` | TEXT | What makes reader want to turn page |
| `illustration_prompt` | TEXT | Scene description for image generation |
| `illustration_path` | TEXT | Path to saved PNG |
| `illustration_updated_at` | TIMESTAMPTZ | Cache bust timestamp |

### character_references
Character visual descriptions for illustration consistency.

| Column | Type | Description |
|--------|------|-------------|
| `story_id` | UUID | FK to stories |
| `character_name` | VARCHAR(100) | Display name |
| `character_description` | TEXT | Brief description |
| `reference_image_path` | TEXT | Path to reference PNG |
| `bible_json` | JSONB | Full EntityBible |

### spread_regen_jobs
Illustration regeneration jobs.

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(8) | Short job ID |
| `story_id` | UUID | FK to stories |
| `spread_number` | INTEGER | Which spread |
| `status` | VARCHAR(20) | pending/running/completed/failed |
| `progress_json` | JSONB | Job progress |
| `error_message` | TEXT | Error if failed |

---

## Advanced Queries

### Full story export with all data:
```sql
SELECT
    s.*,
    json_agg(DISTINCT jsonb_build_object(
        'spread_number', sp.spread_number,
        'text', sp.text,
        'word_count', sp.word_count,
        'illustration_prompt', sp.illustration_prompt
    ) ORDER BY sp.spread_number) as spreads,
    json_agg(DISTINCT jsonb_build_object(
        'name', cr.character_name,
        'description', cr.character_description,
        'bible', cr.bible_json
    )) FILTER (WHERE cr.character_name IS NOT NULL) as characters
FROM stories s
LEFT JOIN story_spreads sp ON s.id = sp.story_id
LEFT JOIN character_references cr ON s.id = cr.story_id
WHERE s.id = 'STORY_ID'
GROUP BY s.id;
```

### Stories with missing illustrations:
```sql
SELECT s.id, s.title, sp.spread_number, sp.illustration_path
FROM stories s
JOIN story_spreads sp ON s.id = sp.story_id
WHERE s.is_illustrated = true
  AND (sp.illustration_path IS NULL
       OR NOT EXISTS (SELECT 1 FROM pg_stat_file(sp.illustration_path)));
```

### Story statistics:
```sql
SELECT
    status,
    COUNT(*) as count,
    AVG(word_count)::int as avg_words,
    AVG(spread_count)::int as avg_spreads,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))::int as avg_gen_seconds
FROM stories
GROUP BY status
ORDER BY count DESC;
```

### Recent generation performance:
```sql
SELECT
    id,
    LEFT(title, 30) as title,
    EXTRACT(EPOCH FROM (completed_at - started_at))::int as seconds,
    word_count,
    is_illustrated
FROM stories
WHERE status = 'completed'
ORDER BY completed_at DESC
LIMIT 10;
```

### Character bible details:
```sql
SELECT
    character_name,
    bible_json->>'species' as species,
    bible_json->>'age_appearance' as age,
    bible_json->>'body' as body,
    bible_json->>'clothing' as clothing,
    bible_json->>'signature_item' as signature_item,
    bible_json->'color_palette' as colors
FROM character_references
WHERE story_id = 'STORY_ID';
```

### Spreads with full illustration prompts:
```sql
SELECT
    spread_number,
    text,
    page_turn_note,
    illustration_prompt
FROM story_spreads
WHERE story_id = 'STORY_ID'
ORDER BY spread_number;
```

### Find stories by goal keyword:
```sql
SELECT id, title, goal, status, created_at::date
FROM stories
WHERE goal ILIKE '%friendship%'
ORDER BY created_at DESC
LIMIT 10;
```

### Find stories by title:
```sql
SELECT id, title, goal, status, created_at::date
FROM stories
WHERE title ILIKE '%adventure%'
ORDER BY created_at DESC
LIMIT 10;
```

### Active regeneration jobs:
```sql
SELECT
    j.id as job_id,
    s.title,
    j.spread_number,
    j.status,
    j.created_at,
    NOW() - j.started_at as running_for
FROM spread_regen_jobs j
JOIN stories s ON j.story_id = s.id
WHERE j.status IN ('pending', 'running')
ORDER BY j.created_at DESC;
```

---

## File System Paths

| Content | Path Pattern |
|---------|--------------|
| Stories root | `/home/kavin/childrens_stories/data/stories/` |
| Story directory | `{stories_root}/{story_uuid}/` |
| Spread images | `{story_dir}/images/spread_01.png` ... `spread_12.png` |
| Character refs | `{story_dir}/character_refs/{safe_name}_reference.png` |

### Check story files exist:
```bash
STORY_ID="uuid-here"
BASE="/home/kavin/childrens_stories/data/stories"

# List all files
find "$BASE/$STORY_ID" -type f -name "*.png" | sort

# Count images
ls "$BASE/$STORY_ID/images/" 2>/dev/null | wc -l
ls "$BASE/$STORY_ID/character_refs/" 2>/dev/null | wc -l

# Check file sizes
du -sh "$BASE/$STORY_ID/images/"
```

---

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stories/` | GET | List stories (params: limit, offset, status) |
| `/stories/{id}` | GET | Get full story |
| `/stories/{id}` | DELETE | Delete story and files |
| `/stories/{id}/spreads/{n}/image` | GET | Get spread PNG |
| `/stories/{id}/characters/{name}/image` | GET | Get character ref PNG |
| `/stories/{id}/spreads/{n}/regenerate` | POST | Start regen job |
| `/stories/{id}/spreads/{n}/regenerate/status` | GET | Check regen status |

### API with jq examples:

```bash
# Pretty print full story
curl -s http://localhost:8000/stories/$STORY_ID | jq

# Just spreads text
curl -s http://localhost:8000/stories/$STORY_ID | jq '.spreads[] | {n: .spread_number, text}'

# Just character names
curl -s http://localhost:8000/stories/$STORY_ID | jq '.character_references[].name'

# List with specific fields
curl -s "http://localhost:8000/stories/?limit=5" | jq '.stories[] | {id, title, status}'
```

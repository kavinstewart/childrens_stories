---
name: story
description: Investigate and understand stories in the database - view spreads, characters, images, and metadata
user-invocable: true
disable-model-invocation: false
argument-hint: [story-id | list | recent | failed | running]
allowed-tools: Read, Bash, Glob, Grep
---

# Story Inspector

Investigate stories in the Children's Story Generator database. Uses the REST API when available, falls back to direct PostgreSQL queries.

## Arguments

Parse `$ARGUMENTS` to determine the action:

| Argument | Action |
|----------|--------|
| `<uuid>` | Inspect specific story by ID |
| `list` | Show recent completed stories |
| `recent` | Show most recently created stories (any status) |
| `failed` | Show failed stories with error messages |
| `running` | Show currently running generation jobs |
| `pending` | Show pending stories |
| (empty) | Same as `list` |

## Hybrid Query Strategy

**Try API first** (faster, cleaner output):
```bash
# Check if API is responding
curl -sf http://localhost:8000/health >/dev/null 2>&1
```

If API is available, use curl commands. If not, fall back to psql.

---

## API Approach (Primary)

### Get story by ID:
```bash
curl -s http://localhost:8000/stories/{story_id} | jq
```

### List stories:
```bash
# Completed (default)
curl -s "http://localhost:8000/stories/?status=completed&limit=10" | jq '.stories[] | {id, title, status, goal}'

# All statuses
curl -s "http://localhost:8000/stories/?status=all&limit=10" | jq '.stories[] | {id, title, status, goal}'

# Failed only
curl -s "http://localhost:8000/stories/?status=failed&limit=10" | jq '.stories[] | {id, title, status, error_message}'

# Running only
curl -s "http://localhost:8000/stories/?status=running&limit=10" | jq '.stories[] | {id, title, status, progress}'
```

### API Response Structure:
The API returns full story data including:
- `id`, `title`, `goal`, `status`
- `word_count`, `spread_count`, `is_illustrated`
- `spreads[]` with text, illustration_prompt, illustration_status
- `character_references[]` with name, description, bible
- `metadata` with illustration_style, entity_definitions

---

## Database Approach (Fallback)

Use when API is unavailable:
```bash
psql -h localhost -U stories -d stories -c "QUERY"
```

### Get story by ID:
```sql
SELECT id, status, title, goal, word_count, spread_count,
       generation_type, is_illustrated, created_at, completed_at, error_message
FROM stories WHERE id = 'STORY_ID';
```

### Get spreads for a story:
```sql
SELECT spread_number,
       LEFT(text, 50) || '...' as text_preview,
       word_count,
       LEFT(page_turn_note, 30) as page_turn,
       illustration_path IS NOT NULL as has_image
FROM story_spreads
WHERE story_id = 'STORY_ID'
ORDER BY spread_number;
```

### Get characters for a story:
```sql
SELECT character_name,
       LEFT(character_description, 50) as description,
       bible_json->>'species' as species,
       bible_json->>'clothing' as clothing,
       reference_image_path IS NOT NULL as has_ref_image
FROM character_references
WHERE story_id = 'STORY_ID';
```

### List recent stories:
```sql
SELECT id, LEFT(title, 40) as title, status, LEFT(goal, 30) as goal,
       created_at::date as created
FROM stories
ORDER BY created_at DESC
LIMIT 10;
```

### List failed stories:
```sql
SELECT id, LEFT(title, 30) as title, LEFT(goal, 25) as goal,
       LEFT(error_message, 50) as error, created_at::date
FROM stories
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 10;
```

### List running stories:
```sql
SELECT id, LEFT(goal, 40) as goal, started_at,
       NOW() - started_at as running_for
FROM stories
WHERE status = 'running';
```

---

## Inspecting Images

Stories store images at:
```
/home/kavin/childrens_stories/data/stories/{story_id}/
├── images/
│   ├── spread_01.png
│   ├── spread_02.png
│   └── ... (up to spread_12.png)
└── character_refs/
    ├── {character_name}_reference.png
    └── ...
```

### Check what images exist:
```bash
ls -la /home/kavin/childrens_stories/data/stories/{story_id}/images/
ls -la /home/kavin/childrens_stories/data/stories/{story_id}/character_refs/
```

### View an image:
Use the Read tool to display PNG files:
```
Read: /home/kavin/childrens_stories/data/stories/{story_id}/images/spread_01.png
```

---

## Output Format

Present findings in a structured, readable format:

```markdown
## Story: {title}

| Field | Value |
|-------|-------|
| **ID** | `{id}` |
| **Status** | {status} |
| **Goal** | {goal} |
| **Words** | {word_count} across {spread_count} spreads |
| **Illustrated** | {is_illustrated} |
| **Created** | {created_at} |
| **Completed** | {completed_at} |

### Spreads ({count})

| # | Text Preview | Words | Page Turn | Image |
|---|--------------|-------|-----------|-------|
| 1 | "Once upon a time..." | 42 | Will she find it? | ✓ |
| 2 | "The brave little..." | 38 | What happens next? | ✓ |

### Characters ({count})

**{Character Name}**
- Description: {brief description}
- Species: {species}
- Clothing: {clothing}
- Reference image: ✓ exists

### Files

- **Spread images**: {count} at `data/stories/{id}/images/`
- **Character refs**: {count} at `data/stories/{id}/character_refs/`
```

---

## Example Usage

User runs: `/story abc12345-...`

1. Check if API is available with health check
2. If yes: `curl -s http://localhost:8000/stories/abc12345-...`
3. If no: Query via psql
4. Check filesystem for images
5. Present formatted summary
6. Ask if user wants to see specific spreads, characters, or images

User runs: `/story failed`

1. Query for failed stories
2. Show table with ID, title, goal, error message
3. Offer to inspect a specific one

User runs: `/story` (no args)

1. List recent completed stories
2. Show ID, title, goal for each

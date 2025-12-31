# R2 Image Storage Migration

## Overview

This document describes migrating illustration storage from local filesystem to Cloudflare R2 (S3-compatible object storage). This enables global CDN distribution, eliminates backend image proxying, and reduces server load.

## Current Architecture

### How Images Are Stored

Images are written to the local filesystem during story generation:

```
data/stories/{story_id}/
├── images/
│   ├── spread_01.png      # ~600-900 KB each
│   ├── spread_02.png
│   └── ...spread_12.png   # 12 spreads per story
└── character_refs/
    ├── {CharacterName}_reference.png  # ~850 KB each
    └── ...
```

**Total per story**: ~9-12 MB (12 spreads + 2-4 character refs)

### How Images Are Saved

**File**: `backend/api/services/story_generation.py`

Lines 176-182 (spread illustrations):
```python
if spread.illustration_image:
    images_dir = story_dir / "images"
    images_dir.mkdir(exist_ok=True)
    img_path = images_dir / f"spread_{spread.spread_number:02d}.png"
    img_path.write_bytes(spread.illustration_image)
    spread_data["illustration_path"] = str(img_path)
```

Lines 188-203 (character references):
```python
if story.reference_sheets:
    char_refs_data = []
    refs_dir = story_dir / "character_refs"
    refs_dir.mkdir(exist_ok=True)

    for name, sheet in story.reference_sheets.character_sheets.items():
        ref_path = refs_dir / f"{_safe_filename(name)}_reference.png"
        ref_path.write_bytes(sheet.reference_image)

        char_refs_data.append(
            {
                "character_name": name,
                "character_description": sheet.character_description,
                "reference_image_path": str(ref_path),
            }
        )
```

### Database Schema

**File**: `backend/api/database/schema.sql`

```sql
-- story_spreads table stores filesystem paths
CREATE TABLE IF NOT EXISTS story_spreads (
    id SERIAL PRIMARY KEY,
    story_id VARCHAR(36) NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    spread_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    word_count INTEGER,
    was_revised BOOLEAN DEFAULT FALSE,
    page_turn_note TEXT,
    illustration_prompt TEXT,
    illustration_path TEXT,  -- Currently: absolute filesystem path
    UNIQUE(story_id, spread_number)
);

-- character_references table stores filesystem paths
CREATE TABLE IF NOT EXISTS character_references (
    id SERIAL PRIMARY KEY,
    story_id VARCHAR(36) NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    character_name VARCHAR(100) NOT NULL,
    character_description TEXT,
    reference_image_path TEXT,  -- Currently: absolute filesystem path
    UNIQUE(story_id, character_name)
);
```

### How Images Are Served

**File**: `backend/api/routes/stories.py`

Lines 106-125 (spread images):
```python
@router.get(
    "/{story_id}/spreads/{spread_number}/image",
    summary="Get spread illustration",
    responses={
        200: {"content": {"image/png": {}}},
        404: {"description": "Image not found"},
    },
)
async def get_spread_image(story_id: str, spread_number: int):
    """Get a spread illustration image (no auth - images accessed via unguessable UUID)."""
    image_path = STORIES_DIR / story_id / "images" / f"spread_{spread_number:02d}.png"

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image for spread {spread_number} not found",
        )

    return FileResponse(image_path, media_type="image/png")
```

Lines 128-155 (character images):
```python
@router.get(
    "/{story_id}/characters/{character_name}/image",
    summary="Get character reference image",
    responses={
        200: {"content": {"image/png": {}}},
        404: {"description": "Image not found"},
    },
)
async def get_character_image(story_id: str, character_name: str):
    """Get a character reference image (no auth - images accessed via unguessable UUID)."""
    refs_dir = STORIES_DIR / story_id / "character_refs"

    if not refs_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character references not found for story {story_id}",
        )

    # Find matching file (case-insensitive, partial match)
    for path in refs_dir.glob("*_reference.png"):
        if character_name.lower() in path.stem.lower():
            return FileResponse(path, media_type="image/png")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Character '{character_name}' not found",
    )
```

### How URLs Are Generated in API Responses

**File**: `backend/api/database/repository.py`

Lines 308-314 (spread URLs):
```python
illustration_url=f"/stories/{story['id']}/spreads/{s['spread_number']}/image"
if s["illustration_path"]
else None,
```

Lines 322-325 (character URLs):
```python
reference_image_url=f"/stories/{story['id']}/characters/{r['character_name']}/image"
if r["reference_image_path"]
else None,
```

### How Frontend Consumes Images

**File**: `frontend/lib/api.ts`

Lines 201-209:
```typescript
// Get spread image URL (a spread = two facing pages)
getSpreadImageUrl: (storyId: string, spreadNumber: number): string => {
  return `${API_BASE_URL}/stories/${storyId}/spreads/${spreadNumber}/image`;
},

// Get character reference image URL
getCharacterImageUrl: (storyId: string, characterName: string): string => {
  return `${API_BASE_URL}/stories/${storyId}/characters/${encodeURIComponent(characterName)}/image`;
},
```

### How Deletion Works

**File**: `backend/api/routes/stories.py`

Lines 158-177:
```python
@router.delete(
    "/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a story",
    description="Delete a story and all associated files.",
)
async def delete_story(story_id: str, repo: Repository, user: CurrentUser):
    """Delete a story and its files."""
    deleted = await repo.delete_story(story_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id} not found",
        )

    # Delete files
    story_dir = STORIES_DIR / story_id
    if story_dir.exists():
        shutil.rmtree(story_dir)
```

### Current Configuration

**File**: `backend/api/config.py`

Lines 23-25:
```python
# Story file storage
STORIES_DIR = DATA_DIR / "stories"
```

---

## Target Architecture (R2)

### Overview

```
[Image Generation]
    → boto3 S3 client
    → Upload to R2 bucket
    → Store public URL in database

[Frontend]
    → Fetch story from API (includes full image URLs)
    → Load images directly from R2 CDN
```

### Benefits

1. **Global CDN**: Images served from Cloudflare's edge network (330+ locations)
2. **Zero backend load**: Backend no longer proxies image bytes
3. **Lower latency**: Edge-served images vs. origin server
4. **Scalability**: R2 handles unlimited concurrent image requests
5. **Cost**: $15/TB storage, zero egress fees

### R2 Object Key Structure

```
{bucket}/
└── stories/
    └── {story_id}/
        ├── images/
        │   ├── spread_01.png
        │   ├── spread_02.png
        │   └── ...spread_12.png
        └── character_refs/
            ├── {CharacterName}_reference.png
            └── ...
```

Example keys:
- `stories/abc123-def456/images/spread_01.png`
- `stories/abc123-def456/character_refs/Otto_reference.png`

### Public URL Format

With a custom domain configured on R2:
```
https://images.yourdomain.com/stories/{story_id}/images/spread_01.png
```

Or using R2.dev public URL:
```
https://{bucket}.{account_id}.r2.dev/stories/{story_id}/images/spread_01.png
```

---

## Implementation Details

### 1. Add Dependencies

```bash
poetry add boto3
```

### 2. Environment Variables

Add to `.env`:

```bash
# Cloudflare R2 Configuration
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET=childrens-stories
R2_PUBLIC_URL=https://images.yourdomain.com
```

To obtain these values:
1. Log into Cloudflare Dashboard
2. Go to R2 Object Storage
3. Create a bucket named `childrens-stories`
4. Go to "Manage R2 API Tokens" → Create API token with read/write permissions
5. (Optional) Set up a custom domain for the bucket under bucket settings

### 3. Create Storage Service

**Create new file**: `backend/api/services/storage.py`

```python
"""Cloudflare R2 storage service for image uploads."""

import os
from typing import Optional

import boto3
from botocore.config import Config


class StorageService:
    """
    S3-compatible storage service for Cloudflare R2.

    Handles uploading, deleting, and URL generation for story images.
    """

    def __init__(self):
        account_id = os.getenv("R2_ACCOUNT_ID")
        access_key = os.getenv("R2_ACCESS_KEY_ID")
        secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

        if not all([account_id, access_key, secret_key]):
            raise RuntimeError(
                "R2 configuration incomplete. Set R2_ACCOUNT_ID, "
                "R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY environment variables."
            )

        self.client = boto3.client(
            's3',
            endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(
                signature_version='s3v4',
                retries={'max_attempts': 3, 'mode': 'adaptive'},
            ),
        )
        self.bucket = os.getenv("R2_BUCKET", "childrens-stories")
        self.public_url = os.getenv("R2_PUBLIC_URL", "").rstrip("/")

        if not self.public_url:
            raise RuntimeError(
                "R2_PUBLIC_URL not configured. Set to your R2 public URL or custom domain."
            )

    def upload_image(self, key: str, data: bytes, content_type: str = "image/png") -> str:
        """
        Upload an image to R2.

        Args:
            key: Object key (e.g., "stories/{story_id}/images/spread_01.png")
            data: Image bytes
            content_type: MIME type (default: image/png)

        Returns:
            Public URL for the uploaded image
        """
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",  # 1 year cache
        )
        return f"{self.public_url}/{key}"

    def delete_object(self, key: str) -> bool:
        """
        Delete a single object from R2.

        Args:
            key: Object key to delete

        Returns:
            True if deleted (or didn't exist), False on error
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def delete_prefix(self, prefix: str) -> int:
        """
        Delete all objects with a given prefix.

        Used for deleting all images when a story is deleted.

        Args:
            prefix: Key prefix (e.g., "stories/{story_id}/")

        Returns:
            Number of objects deleted
        """
        deleted_count = 0

        # List all objects with this prefix
        paginator = self.client.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            objects = page.get('Contents', [])
            if not objects:
                continue

            # Batch delete (up to 1000 at a time per S3 API limits)
            delete_keys = [{'Key': obj['Key']} for obj in objects]

            response = self.client.delete_objects(
                Bucket=self.bucket,
                Delete={'Objects': delete_keys, 'Quiet': True}
            )

            # Count successful deletions
            errors = response.get('Errors', [])
            deleted_count += len(delete_keys) - len(errors)

        return deleted_count

    def object_exists(self, key: str) -> bool:
        """Check if an object exists in R2."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.client.exceptions.ClientError:
            return False


# Global instance - initialized lazily
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create the global storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
```

### 4. Update Configuration

**File**: `backend/api/config.py`

Add after line 25:

```python
# R2 Object Storage (for illustrations)
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET", "childrens-stories")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")
```

### 5. Update Database Schema

**File**: `backend/api/database/schema.sql`

Change column names to reflect that we're storing URLs, not filesystem paths:

```sql
-- story_spreads: rename illustration_path to illustration_url
-- The column now stores full public URLs like:
-- https://images.yourdomain.com/stories/{id}/images/spread_01.png

CREATE TABLE IF NOT EXISTS story_spreads (
    id SERIAL PRIMARY KEY,
    story_id VARCHAR(36) NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    spread_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    word_count INTEGER,
    was_revised BOOLEAN DEFAULT FALSE,
    page_turn_note TEXT,
    illustration_prompt TEXT,
    illustration_url TEXT,  -- CHANGED: was illustration_path
    UNIQUE(story_id, spread_number)
);

-- character_references: rename reference_image_path to reference_image_url
CREATE TABLE IF NOT EXISTS character_references (
    id SERIAL PRIMARY KEY,
    story_id VARCHAR(36) NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    character_name VARCHAR(100) NOT NULL,
    character_description TEXT,
    reference_image_url TEXT,  -- CHANGED: was reference_image_path
    UNIQUE(story_id, character_name)
);
```

**Migration SQL** (run manually or via migration tool):

```sql
-- Migration: Rename columns for R2 storage
ALTER TABLE story_spreads RENAME COLUMN illustration_path TO illustration_url;
ALTER TABLE character_references RENAME COLUMN reference_image_path TO reference_image_url;
```

### 6. Update Story Generation Service

**File**: `backend/api/services/story_generation.py`

Replace the `_save_story` function (lines 153-248):

```python
async def _save_story(
    story_id: str,
    story,
    pool: asyncpg.Pool,
) -> None:
    """Save generated story to database and R2 storage."""
    from .storage import get_storage_service

    storage = get_storage_service()

    # Prepare spreads data
    spreads_data = []
    for spread in story.spreads:
        spread_data = {
            "spread_number": spread.spread_number,
            "text": spread.text,
            "word_count": spread.word_count,
            "was_revised": spread.was_revised,
            "page_turn_note": getattr(spread, "page_turn_note", ""),
            "illustration_prompt": spread.illustration_prompt,
            "illustration_url": None,
        }

        # Upload illustration to R2 if present
        if spread.illustration_image:
            key = f"stories/{story_id}/images/spread_{spread.spread_number:02d}.png"
            url = storage.upload_image(key, spread.illustration_image)
            spread_data["illustration_url"] = url

        spreads_data.append(spread_data)

    # Prepare character refs data
    char_refs_data = None
    if story.reference_sheets:
        char_refs_data = []

        for name, sheet in story.reference_sheets.character_sheets.items():
            # Upload character reference to R2
            safe_name = _safe_filename(name)
            key = f"stories/{story_id}/character_refs/{safe_name}_reference.png"
            url = storage.upload_image(key, sheet.reference_image)

            char_refs_data.append(
                {
                    "character_name": name,
                    "character_description": sheet.character_description,
                    "reference_image_url": url,
                }
            )

    # Serialize outline
    outline_dict = {
        "title": story.outline.title,
        "characters": story.outline.characters,
        "setting": story.outline.setting,
        "plot_summary": story.outline.plot_summary,
        "spread_count": story.outline.spread_count,
    }

    # Serialize judgment if present
    judgment_dict = None
    if story.judgment:
        judgment_dict = {
            "overall_score": story.judgment.overall_score,
            "verdict": story.judgment.verdict,
            "engagement_score": story.judgment.engagement_score,
            "read_aloud_score": story.judgment.read_aloud_score,
            "emotional_truth_score": story.judgment.emotional_truth_score,
            "coherence_score": story.judgment.coherence_score,
            "chekhov_score": story.judgment.chekhov_score,
            "has_critical_failures": story.judgment.has_critical_failures,
            "specific_problems": story.judgment.specific_problems,
        }

    # Save to database
    async with pool.acquire() as conn:
        repo = StoryRepository(conn)
        await repo.save_completed_story(
            story_id=story_id,
            title=story.title,
            word_count=story.word_count,
            spread_count=story.spread_count,
            attempts=story.attempts,
            is_illustrated=story.is_illustrated,
            outline_json=json.dumps(outline_dict),
            judgment_json=json.dumps(judgment_dict) if judgment_dict else None,
            spreads=spreads_data,
            character_refs=char_refs_data,
        )
```

Also remove these imports from the top of the file (no longer needed):
- Remove: `from pathlib import Path` (if only used for image storage)
- Remove: usage of `STORIES_DIR` for image storage

### 7. Update Repository

**File**: `backend/api/database/repository.py`

Update the `save_completed_story` method to use new column names. Find the INSERT statement for `story_spreads` and change:
- `illustration_path` → `illustration_url`

Find the INSERT statement for `character_references` and change:
- `reference_image_path` → `reference_image_url`

Update the `_build_story_response` method (around lines 300-330):

Change lines 308-311 from:
```python
illustration_url=f"/stories/{story['id']}/spreads/{s['spread_number']}/image"
if s["illustration_path"]
else None,
```

To:
```python
illustration_url=s["illustration_url"],  # Now stored as full URL
```

Change lines 322-325 from:
```python
reference_image_url=f"/stories/{story['id']}/characters/{r['character_name']}/image"
if r["reference_image_path"]
else None,
```

To:
```python
reference_image_url=s["reference_image_url"],  # Now stored as full URL
```

### 8. Update Routes

**File**: `backend/api/routes/stories.py`

**Delete these endpoints entirely** (lines 106-155):
- `GET /{story_id}/spreads/{spread_number}/image`
- `GET /{story_id}/characters/{character_name}/image`

These are no longer needed because the frontend will load images directly from R2 URLs.

**Update the delete endpoint** (lines 158-177):

```python
@router.delete(
    "/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a story",
    description="Delete a story and all associated images from R2.",
)
async def delete_story(story_id: str, repo: Repository, user: CurrentUser):
    """Delete a story and its images from R2."""
    from ..services.storage import get_storage_service

    deleted = await repo.delete_story(story_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id} not found",
        )

    # Delete images from R2
    try:
        storage = get_storage_service()
        storage.delete_prefix(f"stories/{story_id}/")
    except Exception as e:
        # Log but don't fail - DB record is already deleted
        # Orphaned R2 objects are acceptable (cheap storage, can clean up later)
        import logging
        logging.getLogger(__name__).warning(
            f"Failed to delete R2 objects for story {story_id}: {e}"
        )
```

Remove import of `shutil` from the top of the file (no longer needed).

Remove import of `STORIES_DIR` from `..config` (no longer needed for images).

### 9. Update Frontend

**File**: `frontend/lib/api.ts`

Remove these helper functions (lines 201-209) as they're no longer needed:
```typescript
// DELETE THESE:
getSpreadImageUrl: (storyId: string, spreadNumber: number): string => {
  return `${API_BASE_URL}/stories/${storyId}/spreads/${spreadNumber}/image`;
},

getCharacterImageUrl: (storyId: string, characterName: string): string => {
  return `${API_BASE_URL}/stories/${storyId}/characters/${encodeURIComponent(characterName)}/image`;
},
```

The `illustration_url` field in the API response now contains the full R2 URL, so the frontend can use it directly:

```typescript
// Before (using helper):
const imageUrl = api.getSpreadImageUrl(story.id, spread.spread_number);

// After (direct from response):
const imageUrl = spread.illustration_url;
```

Update any frontend components that use these helpers to instead use the URL directly from the spread/character object.

**Files to check for usage**:
- `frontend/app/read/[id].tsx` - Story reader component
- Any other components displaying illustrations

---

## Migration of Existing Data

### One-Time Migration Script

Create a script to migrate existing filesystem images to R2:

**Create file**: `scripts/migrate_images_to_r2.py`

```python
#!/usr/bin/env python3
"""
Migrate existing story images from filesystem to R2.

Run with: poetry run python scripts/migrate_images_to_r2.py

This script:
1. Scans the data/stories/ directory for existing images
2. Uploads each image to R2
3. Updates the database with R2 URLs
4. Optionally deletes local files after successful migration
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from dotenv import load_dotenv

load_dotenv()

from backend.api.config import DATABASE_URL, STORIES_DIR
from backend.api.services.storage import get_storage_service


async def migrate_story_images(
    conn: asyncpg.Connection,
    storage,
    story_id: str,
    story_dir: Path,
    dry_run: bool = False,
) -> dict:
    """Migrate images for a single story."""
    stats = {"spreads_migrated": 0, "chars_migrated": 0, "errors": []}

    # Migrate spread images
    images_dir = story_dir / "images"
    if images_dir.exists():
        for img_path in sorted(images_dir.glob("spread_*.png")):
            try:
                # Extract spread number from filename
                spread_num = int(img_path.stem.split("_")[1])

                # Upload to R2
                key = f"stories/{story_id}/images/{img_path.name}"

                if dry_run:
                    print(f"  [DRY RUN] Would upload: {img_path} -> {key}")
                    url = f"https://example.com/{key}"
                else:
                    data = img_path.read_bytes()
                    url = storage.upload_image(key, data)
                    print(f"  Uploaded: {img_path.name} -> {url}")

                # Update database
                if not dry_run:
                    await conn.execute(
                        """
                        UPDATE story_spreads
                        SET illustration_url = $1
                        WHERE story_id = $2 AND spread_number = $3
                        """,
                        url, story_id, spread_num
                    )

                stats["spreads_migrated"] += 1

            except Exception as e:
                stats["errors"].append(f"Spread {img_path}: {e}")

    # Migrate character reference images
    refs_dir = story_dir / "character_refs"
    if refs_dir.exists():
        for ref_path in refs_dir.glob("*_reference.png"):
            try:
                # Extract character name from filename
                char_name = ref_path.stem.replace("_reference", "").replace("_", " ")

                # Upload to R2
                key = f"stories/{story_id}/character_refs/{ref_path.name}"

                if dry_run:
                    print(f"  [DRY RUN] Would upload: {ref_path} -> {key}")
                    url = f"https://example.com/{key}"
                else:
                    data = ref_path.read_bytes()
                    url = storage.upload_image(key, data)
                    print(f"  Uploaded: {ref_path.name} -> {url}")

                # Update database (match on story_id and partial character name)
                if not dry_run:
                    await conn.execute(
                        """
                        UPDATE character_references
                        SET reference_image_url = $1
                        WHERE story_id = $2
                        AND LOWER(REPLACE(character_name, ' ', '_')) = LOWER($3)
                        """,
                        url, story_id, ref_path.stem.replace("_reference", "")
                    )

                stats["chars_migrated"] += 1

            except Exception as e:
                stats["errors"].append(f"Character {ref_path}: {e}")

    return stats


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Migrate story images to R2")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--delete-local", action="store_true", help="Delete local files after successful migration")
    parser.add_argument("--story-id", help="Migrate only a specific story ID")
    args = parser.parse_args()

    if args.dry_run:
        print("=== DRY RUN MODE - No changes will be made ===\n")

    # Initialize storage service
    if not args.dry_run:
        storage = get_storage_service()
    else:
        storage = None

    # Connect to database
    dsn = DATABASE_URL.replace("+asyncpg", "")
    conn = await asyncpg.connect(dsn)

    try:
        # Find all story directories
        if args.story_id:
            story_dirs = [STORIES_DIR / args.story_id]
        else:
            story_dirs = [d for d in STORIES_DIR.iterdir() if d.is_dir()]

        print(f"Found {len(story_dirs)} stories to migrate\n")

        total_stats = {"spreads": 0, "chars": 0, "errors": []}

        for story_dir in story_dirs:
            story_id = story_dir.name
            print(f"Processing story: {story_id}")

            stats = await migrate_story_images(
                conn, storage, story_id, story_dir, dry_run=args.dry_run
            )

            total_stats["spreads"] += stats["spreads_migrated"]
            total_stats["chars"] += stats["chars_migrated"]
            total_stats["errors"].extend(stats["errors"])

            # Optionally delete local files
            if args.delete_local and not args.dry_run and not stats["errors"]:
                import shutil
                shutil.rmtree(story_dir)
                print(f"  Deleted local directory: {story_dir}")

            print()

        # Summary
        print("=" * 50)
        print("MIGRATION SUMMARY")
        print("=" * 50)
        print(f"Spreads migrated: {total_stats['spreads']}")
        print(f"Characters migrated: {total_stats['chars']}")
        print(f"Errors: {len(total_stats['errors'])}")

        if total_stats["errors"]:
            print("\nErrors:")
            for error in total_stats["errors"]:
                print(f"  - {error}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### Migration Steps

1. **Run database migration** to rename columns:
   ```sql
   ALTER TABLE story_spreads RENAME COLUMN illustration_path TO illustration_url;
   ALTER TABLE character_references RENAME COLUMN reference_image_path TO reference_image_url;
   ```

2. **Deploy R2 storage service code** (but keep old FileResponse endpoints temporarily)

3. **Run migration script** in dry-run mode first:
   ```bash
   poetry run python scripts/migrate_images_to_r2.py --dry-run
   ```

4. **Run actual migration**:
   ```bash
   poetry run python scripts/migrate_images_to_r2.py
   ```

5. **Verify** images load from R2 URLs

6. **Remove old FileResponse endpoints** from routes

7. **Delete local files** (optional, after verification):
   ```bash
   poetry run python scripts/migrate_images_to_r2.py --delete-local
   ```

---

## Testing

### Unit Tests

Add tests for the storage service:

**Create file**: `tests/unit/test_storage.py`

```python
"""Tests for R2 storage service."""

import pytest
from unittest.mock import Mock, patch


class TestStorageService:
    """Test StorageService class."""

    @patch.dict('os.environ', {
        'R2_ACCOUNT_ID': 'test_account',
        'R2_ACCESS_KEY_ID': 'test_key',
        'R2_SECRET_ACCESS_KEY': 'test_secret',
        'R2_BUCKET': 'test-bucket',
        'R2_PUBLIC_URL': 'https://images.test.com',
    })
    @patch('boto3.client')
    def test_upload_image(self, mock_boto_client):
        """Test image upload returns correct URL."""
        from backend.api.services.storage import StorageService

        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        service = StorageService()
        url = service.upload_image(
            "stories/abc/images/spread_01.png",
            b"fake image data"
        )

        assert url == "https://images.test.com/stories/abc/images/spread_01.png"
        mock_client.put_object.assert_called_once()

    @patch.dict('os.environ', {
        'R2_ACCOUNT_ID': 'test_account',
        'R2_ACCESS_KEY_ID': 'test_key',
        'R2_SECRET_ACCESS_KEY': 'test_secret',
        'R2_BUCKET': 'test-bucket',
        'R2_PUBLIC_URL': 'https://images.test.com',
    })
    @patch('boto3.client')
    def test_delete_prefix(self, mock_boto_client):
        """Test prefix deletion."""
        from backend.api.services.storage import StorageService

        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock paginator
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {'Contents': [{'Key': 'stories/abc/images/spread_01.png'}]}
        ]
        mock_client.get_paginator.return_value = mock_paginator
        mock_client.delete_objects.return_value = {'Errors': []}

        service = StorageService()
        count = service.delete_prefix("stories/abc/")

        assert count == 1
        mock_client.delete_objects.assert_called_once()
```

### Integration Tests

Test the full flow with a real R2 bucket (use a test bucket):

```python
"""Integration tests for R2 storage (requires R2 credentials)."""

import os
import pytest

# Skip if R2 not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("R2_ACCOUNT_ID"),
    reason="R2 credentials not configured"
)


class TestR2Integration:
    """Integration tests against real R2 bucket."""

    def test_upload_and_delete(self):
        """Test uploading and deleting an image."""
        from backend.api.services.storage import get_storage_service

        storage = get_storage_service()

        # Upload test image
        test_key = "test/integration_test.png"
        test_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Minimal PNG-like data

        url = storage.upload_image(test_key, test_data)
        assert storage.public_url in url
        assert storage.object_exists(test_key)

        # Delete test image
        deleted = storage.delete_object(test_key)
        assert deleted
        assert not storage.object_exists(test_key)
```

---

## Rollback Plan

If issues arise after deployment:

1. **Keep FileResponse endpoints** initially (commented out or behind feature flag)
2. **Database columns** can store either filesystem paths or URLs
3. **To rollback**:
   - Re-enable FileResponse endpoints
   - Run reverse migration to download images from R2 to filesystem
   - Update database URLs back to filesystem paths

---

## Monitoring

### Metrics to Track

1. **R2 upload latency**: Time to upload each image
2. **R2 upload failures**: Count of failed uploads
3. **Storage usage**: Total bytes in R2 bucket
4. **Deletion failures**: Count of failed prefix deletions

### Logging

The storage service should log:
- Successful uploads with key and size
- Failed uploads with error details
- Deletion operations with object count

---

## Cost Estimate

Based on current usage patterns:

| Metric | Estimate |
|--------|----------|
| Stories per month | ~100 |
| Images per story | ~15 (12 spreads + 3 chars) |
| Average image size | 700 KB |
| Monthly new storage | ~1 GB |
| Cumulative storage (1 year) | ~12 GB |
| Monthly cost (storage only) | ~$0.18 |
| Egress | Free (R2 has zero egress fees) |

---

## Summary of Changes

| File | Change |
|------|--------|
| `backend/api/services/storage.py` | **CREATE** - New R2 storage service |
| `backend/api/config.py` | **MODIFY** - Add R2 environment variables |
| `backend/api/database/schema.sql` | **MODIFY** - Rename columns |
| `backend/api/services/story_generation.py` | **MODIFY** - Upload to R2 instead of filesystem |
| `backend/api/database/repository.py` | **MODIFY** - Use stored URLs directly |
| `backend/api/routes/stories.py` | **MODIFY** - Remove image endpoints, update delete |
| `frontend/lib/api.ts` | **MODIFY** - Remove URL helper functions |
| `scripts/migrate_images_to_r2.py` | **CREATE** - Migration script |
| `tests/unit/test_storage.py` | **CREATE** - Unit tests |
| `.env` | **MODIFY** - Add R2 credentials |
| `pyproject.toml` | **MODIFY** - Add boto3 dependency |

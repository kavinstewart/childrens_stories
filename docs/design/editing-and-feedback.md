# Story Editing and GEPA Training Data Collection

## Executive Summary

This document describes the design for:
1. **Story editing as a first-class interface** - allowing users to edit generated stories
2. **GEPA training data collection** - capturing user feedback to improve story generation quality over time

The key insight is that simply logging edit diffs is insufficient. For GEPA optimization to work, we need:
- A **binary signal** that an edit made things better (not just different)
- **Instruction-oriented feedback** explaining why it's better (in terms the DSPy optimizer can act on)

---

## Background: What is GEPA?

GEPA (Reflective Prompt Evolution) is a DSPy optimizer that improves LLM prompts by learning from failures.

### How GEPA Works

```python
optimizer = GEPA(
    metric=metric_with_feedback,  # Returns score + textual feedback
    auto="medium",                 # Optimization intensity
    reflection_lm=strong_model,    # Model that analyzes failures
)

optimized_program = optimizer.compile(
    student_program,               # The DSPy module to optimize
    trainset=training_examples,    # List of dspy.Example objects
    valset=validation_examples,
)
```

### What GEPA Optimizes

GEPA rewrites the **instructions/docstrings** in DSPy Signatures. It:
1. Runs examples through the module
2. Collects failures (low scores)
3. Uses a reflection LM to analyze feedback and propose instruction improvements
4. Tests new instructions on validation set
5. Keeps best-performing version

### Training Example Format

```python
training_examples = [
    dspy.Example(
        goal="teach about sharing",  # Input field
    ).with_inputs("goal"),           # Mark which fields are inputs
]
```

### Metric Function Signature

```python
def metric_with_feedback(
    example: dspy.Example,        # Input (goal, etc.)
    prediction: dspy.Prediction,  # Output (story, spreads, etc.)
    trace=None,
) -> dspy.Prediction:
    return dspy.Prediction(
        score=0.85,               # Float 0-1 (binary 0/1 is fine)
        feedback="..."            # Instruction-oriented text
    )
```

### Critical: Feedback Must Be Instruction-Oriented

**Bad feedback** (useless for GEPA):
```
"User preferred more vivid imagery"
```

**Good feedback** (actionable for GEPA):
```
"Generated: 'The bird flew away fast.'
Edited to: 'The tiny bird darted through the clouds.'

The output violated these instruction principles:
- Used generic verb 'flew' instead of specific action verb
- Used vague adverb 'fast' instead of showing speed through action
- No sensory/visual detail

Suggested instruction improvement: 'Never use generic verbs like flew, went, walked.
Always choose verbs that convey manner and emotion. Show don't tell.'
"
```

The feedback must help the reflection LM understand **what instruction changes would produce better outputs**.

---

## Current Pipeline Architecture

### DSPy Modules in This Project

| Signature | Inputs | Outputs | GEPA Priority |
|-----------|--------|---------|---------------|
| **DirectStorySignature** | `goal`, `reference_examples` | `story` (title + 12 spreads + illustration notes) | **HIGH** |
| **CharacterExtractorSignature** | `story_title`, `story_text` | `characters` (NAME \| DETAILS format) | Medium |
| **CharacterBibleSignature** | `story_title`, `story_text`, `extracted_characters` | `character_bibles` (visual specs) | Medium |
| **StoryJudgeSignature** | `story_text`, `original_goal`, `target_age_range` | Multiple scores + `verdict` | Low (internal) |
| **IllustrationStyleSignature** | `story_summary`, `available_styles` | `selected_style` | Low |

### Current Generation Flow

```
goal
  │
  ▼
DirectStoryGenerator ──────────────────► title + 12 spreads (ONE LLM call)
  │                                        │
  │                                        ▼
  │                              CharacterExtractor ──► character list
  │                                        │
  │                                        ▼
  │                              BibleGenerator ──► character bibles
  │                                        │
  ▼                                        ▼
QualityJudge ◄─────────────────── IllustrationStyleSelector
  │
  ▼
(if score < threshold, retry with feedback)
```

**Important**: The current pipeline generates ALL 12 spreads in a single LLM call. There is no spread-by-spread generation.

### Key Files

- `backend/core/signatures/direct_story.py` - Main story generation signature
- `backend/core/modules/direct_story_generator.py` - Module wrapping the signature
- `backend/core/programs/story_generator.py` - Full pipeline orchestration
- `backend/core/signatures/story_judge.py` - Quality evaluation signature
- `backend/metrics/story_quality.py` - GEPA-compatible metric functions

---

## The Data Collection Challenge

### Why Diffs Alone Are Insufficient

A diff tells us something changed, but not whether it's better:

| Scenario | Diff exists? | Actually better? | GEPA trainable? |
|----------|--------------|------------------|-----------------|
| User fixes typo | Yes | Yes | No (not about instructions) |
| User improves prose | Yes | Yes | **Yes, if we know WHY** |
| User makes lateral change (preference) | Yes | Unknown | No (subjective) |
| User makes it worse | Yes | No | No (wrong direction) |
| User tries something, undoes it | Yes | No | No |

### What We Actually Need for Each Training Example

1. **Version A** - The LLM-generated output
2. **Version B** - The user-edited version (or regenerated version)
3. **B is better than A** - A confirmed signal, not an assumption
4. **Why B is better** - Instruction-oriented explanation for GEPA

---

## Interface Design: Capturing "Better" Signal

### Approach: Implicit Binary Signal via User Actions

**Do NOT ask "was this better?" after every edit.** This interrupts creative flow.

Instead, design the flow so actions imply approval:

| User Action | Implied Signal | Use for Training? |
|-------------|----------------|-------------------|
| Edits spread, clicks "Keep this version" | Positive (edit was intentional improvement) | Yes |
| Edits spread, clicks "Revert" or "Try again" | Negative (edit didn't work) | No |
| Moves to next spread without explicit action | Ambiguous | No |
| Clicks "Regenerate this spread" | Current version unsatisfactory | Yes (original = bad) |
| Finalizes/publishes story | Final version approved | Yes (as positive examples) |

### Implementation: Edit States

Each spread should have explicit states:

```
┌─────────────────────────────────────────────────────────┐
│  Spread 5: "The bird flew away fast."                   │
│                                                         │
│  [Edit] [Regenerate] [Keep] [Revert]                    │
└─────────────────────────────────────────────────────────┘

User clicks [Edit] → enters editing mode
User makes changes → spread enters "draft" state
User clicks [Keep] → POSITIVE signal captured
User clicks [Revert] → NEGATIVE signal, no training data
User clicks [Regenerate] → NEGATIVE signal for current, start fresh
```

---

## Interface Design: Capturing "Why Better" Signal

### Approach: LLM-Generated Reasoning with User Approval

1. When user commits an edit (clicks "Keep"), the system generates reasoning
2. Show the reasoning to the user at a **natural breakpoint** (not immediately)
3. User can approve, modify, or skip

### When to Ask for Reasoning

**Do NOT ask immediately after edit** - user is still in creative flow.

Ask at natural breakpoints:
- When user moves to the next spread
- When user clicks "Save draft"
- When user ends their session
- Batch review: "You made 4 significant changes. Help us learn from them?"

### Reasoning Interface Design

**Do NOT just show "Approve this reasoning?" with a checkbox** - users will rubber-stamp without reading.

Instead, use **multiple choice from LLM-generated options**:

```
┌─────────────────────────────────────────────────────────┐
│  You changed:                                           │
│  "The bird flew away fast."                             │
│  → "The tiny bird darted through the clouds."           │
│                                                         │
│  What made your version better? (select one)            │
│                                                         │
│  ○ More specific, vivid verbs (darted vs flew)          │
│  ○ Added sensory details (through the clouds)           │
│  ○ More specific description (tiny bird)                │
│  ○ Better rhythm when read aloud                        │
│  ○ Other: [________________]                            │
│                                                         │
│  [Skip] [Submit]                                        │
└─────────────────────────────────────────────────────────┘
```

### Two-Layer Reasoning: User-Facing vs GEPA-Facing

The interface shows **user-friendly framing**, but we store **instruction-oriented translation**:

| User sees | GEPA receives |
|-----------|---------------|
| "More specific, vivid verbs" | "Instruction: Replace generic verbs (flew, went, walked, said) with specific action verbs that convey manner and emotion" |
| "Added sensory details" | "Instruction: Each spread should include at least one concrete sensory detail (visual, auditory, tactile)" |
| "Better rhythm when read aloud" | "Instruction: Vary sentence length. Alternate short punchy sentences with slightly longer ones. Read aloud to check rhythm." |

### Filtering: Skip Minor Edits

Not every edit needs reasoning. Automatically skip prompts for:
- Typo fixes (small Levenshtein distance)
- Punctuation-only changes
- Single word substitutions below a threshold
- Changes with high semantic similarity (embedding distance < threshold)

Only prompt for **substantial edits** where there's something meaningful to learn.

---

## Database Schema

### New Tables

#### `story_versions` - Full Story State Snapshots

```sql
CREATE TABLE story_versions (
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,

    -- Full snapshot of editable content
    snapshot_json JSONB NOT NULL,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(50) DEFAULT 'user',  -- 'user', 'llm', 'system'

    PRIMARY KEY (story_id, version_number)
);
```

#### `snapshot_json` Schema (version 1)

```json
{
    "schema_version": 1,
    "outline": {
        "title": "string",
        "characters": "string",
        "setting": "string",
        "plot_summary": "string"
    },
    "spreads": [
        {
            "spread_number": 1,
            "text": "string",
            "word_count": 32,
            "illustration_prompt": "string or null",
            "page_turn_note": "string or null"
        }
        // ... 12 spreads total
    ],
    "character_bibles": [
        {
            "name": "string",
            "visual_description": "string"
        }
    ],
    "illustration_style": "string or null",
    "judgment": {
        "overall_score": 8,
        "verdict": "GOOD"
        // ... other scores if re-evaluated
    }
}
```

#### `edit_actions` - Track Individual User Actions

```sql
CREATE TABLE edit_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,

    -- Version transition
    from_version INTEGER NOT NULL,
    to_version INTEGER NOT NULL,

    -- What was edited
    edit_type VARCHAR(50) NOT NULL,  -- 'spread_text', 'spread_regenerate', 'title', 'character_bible', etc.
    target_identifier VARCHAR(100),   -- e.g., 'spread_5', 'character_Luna'

    -- The diff (for substantial edits)
    old_value TEXT,
    new_value TEXT,

    -- User feedback (captured later, may be NULL)
    is_improvement BOOLEAN,           -- NULL = not yet determined
    user_feedback_choice VARCHAR(100), -- Which option they selected
    user_feedback_text TEXT,          -- Free-form if they chose "Other"
    feedback_captured_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (story_id, from_version) REFERENCES story_versions(story_id, version_number),
    FOREIGN KEY (story_id, to_version) REFERENCES story_versions(story_id, version_number)
);
```

#### `gepa_training_examples` - Processed Training Data

```sql
CREATE TABLE gepa_training_examples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source tracking
    story_id UUID REFERENCES stories(id) ON DELETE SET NULL,
    edit_action_id UUID REFERENCES edit_actions(id) ON DELETE SET NULL,

    -- Which component this trains
    component VARCHAR(100) NOT NULL,  -- 'DirectStorySignature', 'CharacterBibleSignature', etc.

    -- Training example data
    input_json JSONB NOT NULL,        -- The inputs to the DSPy signature
    output_before_json JSONB NOT NULL, -- LLM output (version A)
    output_after_json JSONB NOT NULL,  -- User-improved output (version B)

    -- GEPA metric fields
    score FLOAT NOT NULL,              -- 0.0 or 1.0 typically
    feedback_text TEXT NOT NULL,       -- Instruction-oriented feedback for GEPA

    -- Quality/filtering
    is_approved BOOLEAN DEFAULT FALSE, -- Has this been reviewed?
    is_excluded BOOLEAN DEFAULT FALSE, -- Should this be excluded from training?
    exclusion_reason TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gepa_examples_component ON gepa_training_examples(component);
CREATE INDEX idx_gepa_examples_approved ON gepa_training_examples(is_approved) WHERE is_approved = TRUE;
```

---

## Processing Pipeline: Edit Action → GEPA Training Example

### Step 1: User Makes Edit

```
User edits spread 5:
  Before: "The bird flew away fast."
  After:  "The tiny bird darted through the clouds."

User clicks [Keep]
```

### Step 2: System Creates Edit Action Record

```sql
INSERT INTO edit_actions (
    story_id, from_version, to_version,
    edit_type, target_identifier,
    old_value, new_value,
    is_improvement
) VALUES (
    'uuid...', 3, 4,
    'spread_text', 'spread_5',
    'The bird flew away fast.',
    'The tiny bird darted through the clouds.',
    TRUE  -- Implicit from [Keep] action
);
```

### Step 3: At Natural Breakpoint, Prompt for Reasoning

System generates options via LLM:

```python
prompt = f"""
The user edited this text in a children's story:

Before: "{old_value}"
After: "{new_value}"

Generate 4 possible reasons why the user's version is better,
phrased as writing advice. Be specific to what changed.
Format: One reason per line, 10 words or less each.
"""
```

LLM returns:
```
More specific, vivid verb choice (darted vs flew)
Added concrete visual detail (through the clouds)
More precise description (tiny bird vs just bird)
Removed telling adverb (fast) in favor of showing
```

### Step 4: User Selects Reasoning

User picks: "More specific, vivid verb choice (darted vs flew)"

### Step 5: System Generates Instruction-Oriented Feedback

```python
prompt = f"""
A user edited children's story text:

Before: "{old_value}"
After: "{new_value}"

They indicated the improvement was: "{user_selection}"

Generate instruction-oriented feedback for a prompt optimizer.
The feedback should explain what the original AI instructions
should have said to produce the better version directly.

Format:
1. What was wrong with the original output (specific)
2. What the improved version does better (specific)
3. Suggested instruction text to add to the prompt
"""
```

### Step 6: Create GEPA Training Example

```sql
INSERT INTO gepa_training_examples (
    story_id, edit_action_id, component,
    input_json, output_before_json, output_after_json,
    score, feedback_text, is_approved
) VALUES (
    'uuid...', 'edit-uuid...', 'DirectStorySignature',
    '{"goal": "teach about sharing", "reference_examples": "..."}',
    '{"spread_5_text": "The bird flew away fast."}',
    '{"spread_5_text": "The tiny bird darted through the clouds."}',
    0.0,  -- Original was wrong
    'OUTPUT ISSUE: Used generic verb "flew" with telling adverb "fast".

IMPROVED VERSION: Uses specific action verb "darted" that conveys speed
through the verb itself. Adds concrete visual detail "through the clouds".
Replaces generic "bird" with specific "tiny bird".

SUGGESTED INSTRUCTION ADDITION:
"Never use generic verbs (flew, went, walked, said) with adverbs.
Choose specific verbs that convey manner: darted, trudged, whispered, bellowed.
Show speed/emotion through verb choice, not adverbs."',
    TRUE
);
```

---

## API Endpoints

### Story Versioning

```
POST /stories/{id}/versions
    Create new version from current state
    Returns: version_number

GET /stories/{id}/versions
    List all versions for a story
    Returns: [{ version_number, created_at, created_by }]

GET /stories/{id}/versions/{version_number}
    Get specific version snapshot
    Returns: snapshot_json

POST /stories/{id}/versions/{version_number}/restore
    Restore story to a previous version
    Creates new version with restored content
```

### Editing

```
PATCH /stories/{id}/spreads/{spread_number}
    Edit spread text directly
    Body: { "text": "new text", "action": "keep" | "draft" }
    Creates new version, records edit_action
    Returns: { version_number, edit_action_id }

POST /stories/{id}/spreads/{spread_number}/regenerate
    Regenerate a single spread (requires new capability)
    Creates new version, records edit_action with is_improvement=NULL initially
    Returns: { version_number, new_text, edit_action_id }
```

### Feedback Collection

```
GET /stories/{id}/pending-feedback
    Get edit actions needing feedback
    Returns: [{ edit_action_id, old_value, new_value, suggested_reasons[] }]

POST /edit-actions/{id}/feedback
    Submit feedback for an edit
    Body: { "selected_reason": "...", "custom_reason": "..." }
    Triggers GEPA training example generation
```

### GEPA Training Data

```
GET /admin/gepa-examples?component=DirectStorySignature&approved=true
    List training examples for export
    Returns: [{ input_json, output_before_json, output_after_json, score, feedback_text }]

POST /admin/gepa-examples/{id}/approve
    Mark example as approved for training

POST /admin/gepa-examples/{id}/exclude
    Exclude example from training
    Body: { "reason": "..." }
```

---

## Frontend Implementation Notes

### Edit Mode for Spreads

```typescript
interface SpreadEditorState {
  mode: 'viewing' | 'editing' | 'draft';
  originalText: string;
  currentText: string;
  hasUnsavedChanges: boolean;
}

// Actions
onEdit(): void       // Enter editing mode
onKeep(): void       // Commit edit, create version, record positive signal
onRevert(): void     // Discard changes, no training data
onRegenerate(): void // Request new LLM generation for this spread
```

### Feedback Collection Modal

Show at natural breakpoints. Batch multiple edits if several occurred:

```typescript
interface PendingFeedback {
  editActionId: string;
  spreadNumber: number;
  oldText: string;
  newText: string;
  suggestedReasons: string[];  // LLM-generated
}

interface FeedbackModalProps {
  pendingItems: PendingFeedback[];
  onSubmit: (feedbacks: { editActionId: string; selectedReason: string }[]) => void;
  onSkip: () => void;
}
```

### When to Show Feedback Modal

```typescript
// Triggers for showing feedback collection
const feedbackTriggers = {
  onSpreadNavigation: true,      // Moving to next/prev spread
  onSaveDraft: true,             // Explicit save action
  onSessionEnd: true,            // Leaving the editor
  onPublish: true,               // Finalizing story
  afterNEdits: 3,                // After N substantial edits
};

// Filter: only show for substantial edits
function isSubstantialEdit(oldText: string, newText: string): boolean {
  const charDelta = Math.abs(oldText.length - newText.length);
  const wordDelta = Math.abs(
    oldText.split(/\s+/).length - newText.split(/\s+/).length
  );

  // Substantial if: >20% char change OR >2 word change
  return charDelta / oldText.length > 0.2 || wordDelta > 2;
}
```

---

## Spread-Level Regeneration (New Capability Needed)

The current pipeline generates all 12 spreads in one LLM call. To support "regenerate this spread," we need a new capability.

### Option A: Regenerate Single Spread in Context

Create a new signature:

```python
class SingleSpreadRegenerationSignature(dspy.Signature):
    """
    Regenerate a single spread while maintaining story coherence.

    You are revising ONE spread of a 12-spread children's picture book.
    The surrounding spreads provide context. Your new spread must:
    - Flow naturally from the previous spread
    - Set up the next spread appropriately
    - Maintain consistent characters and tone
    - Keep similar word count (25-35 words)
    """

    story_context: str = dspy.InputField(
        desc="Title, goal, and all 12 spreads with the target spread marked"
    )

    spread_number: int = dspy.InputField(
        desc="Which spread to regenerate (1-12)"
    )

    feedback: str = dspy.InputField(
        desc="Optional: what was wrong with the previous version"
    )

    new_spread: str = dspy.OutputField(
        desc="The regenerated spread text (25-35 words) with [Illustration: ...] note"
    )
```

### Option B: Regenerate Full Story with Constraints

Pass the current story as a constraint:

```python
current_goal = f"""
{original_goal}

IMPORTANT: Keep spreads 1-4, 6-12 exactly as shown below.
Only rewrite spread 5 to be better.

Current story:
{full_story_text}

Problem with spread 5: {user_feedback_if_any}
"""
```

This is simpler but more expensive (full generation) and less reliable.

**Recommendation**: Implement Option A for better control and lower cost.

---

## GEPA Training Pipeline

### Export Training Data

```python
def export_gepa_training_set(component: str) -> list[dspy.Example]:
    """Export approved training examples for a specific component."""

    examples = db.query("""
        SELECT input_json, output_after_json, score, feedback_text
        FROM gepa_training_examples
        WHERE component = $1
          AND is_approved = TRUE
          AND is_excluded = FALSE
    """, component)

    return [
        dspy.Example(
            **example.input_json,
            _output=example.output_after_json,
            _score=example.score,
            _feedback=example.feedback_text,
        ).with_inputs(*example.input_json.keys())
        for example in examples
    ]
```

### Run GEPA Optimization

```python
from dspy import GEPA

def optimize_component(component_name: str, student_module: dspy.Module):
    # Load training data from database
    trainset = export_gepa_training_set(component_name)

    # Split for validation
    train, val = trainset[:int(len(trainset)*0.8)], trainset[int(len(trainset)*0.8):]

    # Configure optimizer
    optimizer = GEPA(
        metric=make_metric_from_stored_feedback,
        auto="medium",
        reflection_lm=dspy.LM("claude-opus-4-5-20251101"),
        track_stats=True,
    )

    # Run optimization
    optimized = optimizer.compile(
        student_module,
        trainset=train,
        valset=val,
    )

    return optimized

def make_metric_from_stored_feedback(example, prediction, trace=None):
    """Metric that uses pre-computed feedback from database."""
    # The feedback was already computed and stored when the training
    # example was created, so we just return it
    return dspy.Prediction(
        score=example._score,
        feedback=example._feedback,
    )
```

---

## Implementation Phases

### Phase 1: Story Versioning (Backend)
- Create `story_versions` table
- Add `snapshot_json` schema validation
- Implement version creation on story save
- API endpoints for version listing and retrieval

### Phase 2: Edit Tracking (Backend)
- Create `edit_actions` table
- Instrument spread editing to record actions
- Track implicit signals (Keep/Revert)

### Phase 3: Edit Interface (Frontend)
- Spread editing mode with Keep/Revert/Regenerate buttons
- Version history UI
- State management for edit flow

### Phase 4: Feedback Collection (Full Stack)
- LLM-generated reasoning options
- Feedback modal at natural breakpoints
- Store user selections

### Phase 5: GEPA Pipeline (Backend)
- Create `gepa_training_examples` table
- Processing job: edit_action → training_example
- Export endpoints for training data
- Admin UI for reviewing/approving examples

### Phase 6: Single-Spread Regeneration (Backend)
- New DSPy signature for contextual regeneration
- API endpoint for spread regeneration
- Integration with edit tracking

---

## Open Questions

1. **Regeneration approach**: Option A (new signature) vs Option B (constrained full generation)?

2. **Feedback batching**: Collect after each edit, or batch at session end?

3. **Minimum training examples**: How many examples needed before running GEPA?

4. **Feedback generation model**: Which model generates the reasoning options and instruction-oriented feedback?

5. **Version retention**: Keep all versions forever, or prune old drafts?

6. **Multi-user**: If multiple users can edit, how do we attribute feedback?

---

## References

- [DSPy GEPA Documentation](https://dspy.ai/api/optimizers/GEPA/overview/)
- [Hugging Face GEPA Cookbook](https://huggingface.co/learn/cookbook/en/dspy_gepa)
- [GEPA Paper](https://arxiv.org/abs/2507.19457) - "Reflective Prompt Evolution Can Outperform Reinforcement Learning"
- Current DSPy signatures: `backend/core/signatures/`
- Current story generator: `backend/core/programs/story_generator.py`

# Inline entity tagging workflow
from .direct_story_generator import DirectStoryGenerator
from .bible_generator import BibleGenerator

# Illustration
from .spread_illustrator import SpreadIllustrator
from .vlm_judge import VLMJudge, DetailedCheckResult

# DEPRECATED: CharacterExtractor is no longer used in the main pipeline.
# It's replaced by inline entity tagging in DirectStoryGenerator.
# Kept for backwards compatibility with existing tests and legacy code.
# Will be removed in a future version after migration is complete.
from .character_extractor import CharacterExtractor, ExtractedCharacter

__all__ = [
    # Inline entity tagging workflow
    "DirectStoryGenerator",
    "BibleGenerator",
    # Illustration
    "SpreadIllustrator",
    "VLMJudge",
    "DetailedCheckResult",
    # DEPRECATED - kept for backwards compatibility
    "CharacterExtractor",
    "ExtractedCharacter",
]

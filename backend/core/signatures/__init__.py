# Story-first workflow (recommended)
from .direct_story import DirectStorySignature
from .character_extractor import CharacterExtractorSignature
from .character_bible import CharacterBibleSignature
from .illustration_style import IllustrationStyleSignature

# Quality judgment
from .story_judge import StoryJudgeSignature

# Legacy outline-first workflow (kept for potential outline editing)
from .story_outline import StoryOutlineSignature
from .full_story import FullStorySignature, FullStoryWithPromptsSignature

__all__ = [
    # Story-first workflow (recommended)
    "DirectStorySignature",
    "CharacterExtractorSignature",
    "CharacterBibleSignature",
    "IllustrationStyleSignature",
    # Quality judgment
    "StoryJudgeSignature",
    # Legacy
    "StoryOutlineSignature",
    "FullStorySignature",
    "FullStoryWithPromptsSignature",
]

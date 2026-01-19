# Story-first workflow
from .direct_story import DirectStorySignature
from .character_extractor import CharacterExtractorSignature
from .entity_bible import EntityBibleSignature
from .illustration_style import IllustrationStyleSignature

# Backwards-compatible alias (deprecated)
CharacterBibleSignature = EntityBibleSignature

__all__ = [
    "DirectStorySignature",
    "CharacterExtractorSignature",
    "EntityBibleSignature",
    "CharacterBibleSignature",  # Deprecated alias
    "IllustrationStyleSignature",
]

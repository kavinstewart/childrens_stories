# Children's Story Generator - Core Domain

# Re-export types for convenient access
from .types import (
    StyleDefinition,
    EntityBible,
    CharacterBible,  # Deprecated alias for EntityBible
    CharacterReferenceSheet,
    StoryReferenceSheets,
    StoryMetadata,
    StorySpread,
    GeneratedStory,
)

__all__ = [
    "StyleDefinition",
    "EntityBible",
    "CharacterBible",  # Deprecated alias
    "CharacterReferenceSheet",
    "StoryReferenceSheets",
    "StoryMetadata",
    "StorySpread",
    "GeneratedStory",
]

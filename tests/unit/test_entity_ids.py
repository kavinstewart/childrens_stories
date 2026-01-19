"""
Tests for inline entity tagging system.

Entity IDs (e.g., @e1, @e2) provide stable, unambiguous references to characters
and other entities throughout a story, eliminating the need for name-based matching.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.core.types import (
    EntityDefinition,
    CharacterBible,
    StoryMetadata,
    StorySpread,
    StoryReferenceSheets,
    CharacterReferenceSheet,
    StyleDefinition,
)
from backend.core.modules.direct_story_generator import DirectStoryGenerator


# =============================================================================
# Test 1: EntityDefinition dataclass
# =============================================================================

class TestEntityDefinition:
    """Tests for EntityDefinition dataclass."""

    def test_entity_definition_fields(self):
        """EntityDefinition should have required fields."""
        entity = EntityDefinition(
            entity_id="@e1",
            display_name="George Washington",
            entity_type="character",
            brief_description="young boy exploring the forest",
        )
        assert entity.entity_id == "@e1"
        assert entity.display_name == "George Washington"
        assert entity.entity_type == "character"
        assert entity.brief_description == "young boy exploring the forest"

    def test_entity_definition_equality(self):
        """EntityDefinition should support equality comparison."""
        e1 = EntityDefinition("@e1", "George", "character", "a boy")
        e2 = EntityDefinition("@e1", "George", "character", "a boy")
        e3 = EntityDefinition("@e2", "Owl", "character", "an owl")

        assert e1 == e2
        assert e1 != e3

    def test_entity_definition_is_character(self):
        """EntityDefinition should have is_character property."""
        char_entity = EntityDefinition("@e1", "George", "character", "a boy")
        location_entity = EntityDefinition("@e2", "Forest", "location", "enchanted forest")

        assert char_entity.is_character is True
        assert location_entity.is_character is False


# =============================================================================
# Test 2: StorySpread with present_entity_ids
# =============================================================================

class TestStorySpreadEntityIds:
    """Tests for StorySpread with entity ID support."""

    def test_spread_has_present_entity_ids(self):
        """StorySpread should have present_entity_ids field."""
        spread = StorySpread(
            spread_number=1,
            text="George walked into the forest.",
            word_count=5,
            present_entity_ids=["@e1", "@e2"],
        )
        assert spread.present_entity_ids == ["@e1", "@e2"]

    def test_spread_present_entity_ids_default_none(self):
        """StorySpread present_entity_ids should default to None."""
        spread = StorySpread(
            spread_number=1,
            text="Test",
            word_count=1,
        )
        assert spread.present_entity_ids is None

    def test_spread_present_entity_ids_empty_list(self):
        """StorySpread should support empty list for no characters visible."""
        spread = StorySpread(
            spread_number=1,
            text="An empty room.",
            word_count=3,
            present_entity_ids=[],
        )
        assert spread.present_entity_ids == []


# =============================================================================
# Test 3: StoryMetadata with entity_definitions and entity_bibles
# =============================================================================

class TestStoryMetadataEntityIds:
    """Tests for StoryMetadata with entity ID support."""

    @pytest.fixture
    def sample_style(self):
        """Sample illustration style for testing."""
        return StyleDefinition(
            name="Watercolor",
            description="Soft watercolor style",
            prompt_prefix="Watercolor illustration",
            best_for=["nature"],
        )

    @pytest.fixture
    def sample_entities(self):
        """Sample entity definitions."""
        return {
            "@e1": EntityDefinition("@e1", "George Washington", "character", "young boy"),
            "@e2": EntityDefinition("@e2", "The Wise Owl", "character", "elderly owl"),
            "@e3": EntityDefinition("@e3", "The Enchanted Forest", "location", "misty woods"),
        }

    @pytest.fixture
    def sample_bibles(self):
        """Sample character bibles keyed by entity ID."""
        return {
            "@e1": CharacterBible(name="George Washington", species="human", age_appearance="young boy"),
            "@e2": CharacterBible(name="The Wise Owl", species="owl", age_appearance="elderly"),
        }

    def test_story_metadata_has_entity_definitions(self, sample_style, sample_entities):
        """StoryMetadata should have entity_definitions field."""
        metadata = StoryMetadata(
            title="Test Story",
            entity_definitions=sample_entities,
            illustration_style=sample_style,
        )
        assert metadata.entity_definitions == sample_entities
        assert "@e1" in metadata.entity_definitions
        assert metadata.entity_definitions["@e1"].display_name == "George Washington"

    def test_story_metadata_has_entity_bibles(self, sample_style, sample_bibles):
        """StoryMetadata should have entity_bibles dict."""
        metadata = StoryMetadata(
            title="Test Story",
            entity_bibles=sample_bibles,
            illustration_style=sample_style,
        )
        assert metadata.entity_bibles == sample_bibles
        assert "@e1" in metadata.entity_bibles
        assert metadata.entity_bibles["@e1"].name == "George Washington"

    def test_story_metadata_get_character_bible_by_entity_id(self, sample_style, sample_bibles, sample_entities):
        """get_character_bible should look up by entity ID."""
        metadata = StoryMetadata(
            title="Test Story",
            entity_bibles=sample_bibles,
            entity_definitions=sample_entities,
            illustration_style=sample_style,
        )

        bible = metadata.get_character_bible("@e1")
        assert bible is not None
        assert bible.name == "George Washington"

    def test_story_metadata_get_character_bible_unknown_id(self, sample_style, sample_bibles, sample_entities):
        """get_character_bible should return None for unknown entity ID."""
        metadata = StoryMetadata(
            title="Test Story",
            entity_bibles=sample_bibles,
            entity_definitions=sample_entities,
            illustration_style=sample_style,
        )

        bible = metadata.get_character_bible("@e99")
        assert bible is None

    def test_story_metadata_defaults_to_empty_dicts(self, sample_style):
        """StoryMetadata should default to empty dicts for new fields."""
        metadata = StoryMetadata(
            title="Test Story",
            illustration_style=sample_style,
        )
        assert metadata.entity_definitions == {}
        assert metadata.entity_bibles == {}


# =============================================================================
# Test 4: CharacterReferenceSheet with entity_id
# =============================================================================

class TestCharacterReferenceSheetEntityId:
    """Tests for CharacterReferenceSheet with entity ID support."""

    def test_reference_sheet_has_entity_id(self):
        """CharacterReferenceSheet should have entity_id field."""
        sheet = CharacterReferenceSheet(
            character_name="George Washington",
            reference_image=b"fake_image",
            entity_id="@e1",
        )
        assert sheet.entity_id == "@e1"

    def test_reference_sheet_entity_id_optional(self):
        """CharacterReferenceSheet entity_id should be optional for backwards compat."""
        sheet = CharacterReferenceSheet(
            character_name="George",
            reference_image=b"fake_image",
        )
        assert sheet.entity_id is None


# =============================================================================
# Test 5: StoryReferenceSheets with entity ID keys
# =============================================================================

class TestStoryReferenceSheetsEntityIds:
    """Tests for StoryReferenceSheets with entity ID keying."""

    @pytest.fixture
    def reference_sheets_with_entity_ids(self):
        """Reference sheets keyed by entity ID."""
        sheets = StoryReferenceSheets(story_title="Test Story")
        sheets.character_sheets["@e1"] = CharacterReferenceSheet(
            character_name="George Washington",
            reference_image=b"george_image",
            entity_id="@e1",
        )
        sheets.character_sheets["@e2"] = CharacterReferenceSheet(
            character_name="The Wise Owl",
            reference_image=b"owl_image",
            entity_id="@e2",
        )
        return sheets

    def test_get_sheet_by_entity_id(self, reference_sheets_with_entity_ids):
        """Should get sheet by direct entity ID lookup."""
        sheets = reference_sheets_with_entity_ids

        sheet = sheets.get_sheet("@e1")
        assert sheet is not None
        assert sheet.character_name == "George Washington"

    def test_get_sheet_unknown_entity_id(self, reference_sheets_with_entity_ids):
        """Should return None for unknown entity ID."""
        sheets = reference_sheets_with_entity_ids

        sheet = sheets.get_sheet("@e99")
        assert sheet is None

    def test_character_sheets_keyed_by_entity_id(self, reference_sheets_with_entity_ids):
        """character_sheets should be keyed by entity ID, not name."""
        sheets = reference_sheets_with_entity_ids

        # Keys should be entity IDs
        assert "@e1" in sheets.character_sheets
        assert "@e2" in sheets.character_sheets

        # Looking up by name should not work (keys are IDs now)
        assert "George Washington" not in sheets.character_sheets


# =============================================================================
# Test 6: DirectStoryGenerator Entity Parsing
# =============================================================================

class TestDirectStoryGeneratorEntityParsing:
    """Tests for DirectStoryGenerator parsing [Entities] block and entity IDs."""

    @pytest.fixture
    def story_generator(self):
        """DirectStoryGenerator instance."""
        return DirectStoryGenerator(include_examples=False)

    def test_parse_entities_block(self, story_generator):
        """Should parse [Entities] block into entity definitions."""
        raw_output = """
[Entities]
@e1: George Washington (character, young boy exploring the forest)
@e2: The Wise Owl (character, elderly owl who gives advice)
@e3: The Enchanted Forest (location, misty magical woods)

TITLE: The Forest Adventure

Spread 1: George walked into the forest.
[Illustration: A young boy entering a misty forest]
[Characters: @e1]

Spread 2: He met the owl.
[Illustration: Boy talking to an owl on a branch]
[Characters: @e1, @e2]
"""
        title, spreads, entity_definitions = story_generator._parse_story_output(raw_output)

        assert len(entity_definitions) == 3

        assert "@e1" in entity_definitions
        e1 = entity_definitions["@e1"]
        assert e1.display_name == "George Washington"
        assert e1.entity_type == "character"
        assert e1.brief_description == "young boy exploring the forest"

        assert "@e2" in entity_definitions
        e2 = entity_definitions["@e2"]
        assert e2.display_name == "The Wise Owl"
        assert e2.entity_type == "character"

        assert "@e3" in entity_definitions
        e3 = entity_definitions["@e3"]
        assert e3.display_name == "The Enchanted Forest"
        assert e3.entity_type == "location"

    def test_parse_characters_with_entity_ids(self, story_generator):
        """Should parse [Characters: @e1, @e2] as entity ID list."""
        raw_output = """
[Entities]
@e1: George (character, a boy)
@e2: Owl (character, a wise owl)

TITLE: Test

Spread 1: George and the owl talked.
[Illustration: Boy and owl]
[Characters: @e1, @e2]

Spread 2: Just George.
[Illustration: Boy alone]
[Characters: @e1]

Spread 3: Empty room.
[Illustration: An empty room]
[Characters: none]
"""
        title, spreads, entity_definitions = story_generator._parse_story_output(raw_output)

        assert len(spreads) == 3

        # Spread 1: Both characters
        assert spreads[0].present_entity_ids == ["@e1", "@e2"]

        # Spread 2: Just George
        assert spreads[1].present_entity_ids == ["@e1"]

        # Spread 3: No characters
        assert spreads[2].present_entity_ids == []

    def test_parse_legacy_format_no_entities_block(self, story_generator):
        """Should still work with legacy format (no [Entities] block)."""
        raw_output = """
TITLE: Old Story

Spread 1: George walked.
[Illustration: A boy walking]
[Characters: George]
"""
        title, spreads, entity_definitions = story_generator._parse_story_output(raw_output)

        # No entities block means empty entity_definitions
        assert entity_definitions == {}

        # Spreads should still work with legacy present_characters
        assert spreads[0].present_characters == ["George"]
        # No entity IDs in legacy format
        assert spreads[0].present_entity_ids is None

    def test_entity_id_format_validation(self, story_generator):
        """Entity IDs should be in @eN format."""
        raw_output = """
[Entities]
@e1: Valid Entity (character, description)
@e10: Also Valid (character, description with number 10)

TITLE: Test

Spread 1: Text
[Illustration: scene]
[Characters: @e1, @e10]
"""
        title, spreads, entity_definitions = story_generator._parse_story_output(raw_output)

        assert "@e1" in entity_definitions
        assert "@e10" in entity_definitions

        assert spreads[0].present_entity_ids == ["@e1", "@e10"]

    def test_distinguishes_entity_ids_from_names(self, story_generator):
        """Should distinguish @eN entity IDs from plain character names."""
        raw_output = """
[Entities]
@e1: George (character, a boy)

TITLE: Test

Spread 1: George walked.
[Illustration: A boy]
[Characters: @e1]
"""
        title, spreads, entity_definitions = story_generator._parse_story_output(raw_output)

        # This should be entity ID, not legacy name
        assert spreads[0].present_entity_ids == ["@e1"]
        # Legacy field should be None when using entity IDs
        assert spreads[0].present_characters is None

    def test_mixed_format_not_allowed(self, story_generator):
        """Should not mix entity IDs and legacy names in same story."""
        # If [Entities] block is present, all [Characters:] should use @eN format
        raw_output = """
[Entities]
@e1: George (character, a boy)

TITLE: Test

Spread 1: George walked.
[Illustration: A boy]
[Characters: George]
"""
        # With entities block, "George" in [Characters:] should trigger warning
        # but still parse (as legacy fallback during transition)
        title, spreads, entity_definitions = story_generator._parse_story_output(raw_output)

        assert len(entity_definitions) == 1
        # Non-@ names go to present_characters for backwards compatibility
        assert spreads[0].present_characters == ["George"]


# =============================================================================
# Test 7: BibleGenerator with Entity IDs
# =============================================================================

class TestBibleGeneratorEntityIds:
    """Tests for BibleGenerator accepting and outputting entity IDs."""

    @pytest.fixture
    def bible_generator(self):
        """BibleGenerator instance."""
        from backend.core.modules.bible_generator import BibleGenerator
        return BibleGenerator()

    @pytest.fixture
    def sample_entity_definitions(self):
        """Sample entity definitions for testing."""
        return {
            "@e1": EntityDefinition("@e1", "George Washington", "character", "young boy exploring"),
            "@e2": EntityDefinition("@e2", "The Wise Owl", "character", "elderly owl advisor"),
            "@e3": EntityDefinition("@e3", "The Enchanted Forest", "location", "magical woods"),
        }

    def test_generate_bibles_for_character_entities(self, bible_generator, sample_entity_definitions):
        """Should generate bibles only for character-type entities."""
        with patch.object(bible_generator, 'generate') as mock_generate:
            mock_generate.return_value = MagicMock(character_bibles="""
CHARACTER: George Washington
SPECIES: human
AGE_APPEARANCE: young boy
BODY: small and curious
FACE: round cheeks

CHARACTER: The Wise Owl
SPECIES: owl
AGE_APPEARANCE: elderly
BODY: large feathered
""")

            story_text = "George walked into the forest and met the wise owl."
            bibles = bible_generator.forward(
                title="Test Story",
                story_text=story_text,
                entity_definitions=sample_entity_definitions,
            )

            # Should be keyed by entity ID, not name
            assert isinstance(bibles, dict)
            assert "@e1" in bibles
            assert "@e2" in bibles
            # Location entity should NOT have a bible
            assert "@e3" not in bibles

    def test_bible_output_keyed_by_entity_id(self, bible_generator, sample_entity_definitions):
        """Bible output should be dict keyed by entity ID."""
        with patch.object(bible_generator, 'generate') as mock_generate:
            mock_generate.return_value = MagicMock(character_bibles="""
CHARACTER: George Washington
SPECIES: human
""")

            # Only character entities
            char_entities = {k: v for k, v in sample_entity_definitions.items() if v.is_character}

            bibles = bible_generator.forward(
                title="Test",
                story_text="Test story",
                entity_definitions=char_entities,
            )

            # Result should be dict, not list
            assert isinstance(bibles, dict)
            # Can look up by entity ID
            if "@e1" in bibles:
                assert bibles["@e1"].name == "George Washington"

    def test_filters_out_non_character_entities(self, bible_generator, sample_entity_definitions):
        """Should only generate bibles for character-type entities."""
        # The input has 2 characters and 1 location
        # BibleGenerator should only process the 2 characters
        with patch.object(bible_generator, 'generate') as mock_generate:
            mock_generate.return_value = MagicMock(character_bibles="""
CHARACTER: George Washington
SPECIES: human

CHARACTER: The Wise Owl
SPECIES: owl
""")

            bibles = bible_generator.forward(
                title="Test",
                story_text="Test story",
                entity_definitions=sample_entity_definitions,
            )

            # Only 2 bibles (characters), not 3 (which includes location)
            assert len(bibles) <= 2

    def test_no_copy_aliases_needed(self, bible_generator):
        """With entity IDs, alias copying is no longer needed."""
        # Entity IDs eliminate the need for name matching/aliases
        # BibleGenerator should not have _copy_aliases anymore
        assert not hasattr(bible_generator, '_copy_aliases')

"""
Tests for inline entity tagging system.

Entity IDs (e.g., @e1, @e2) provide stable, unambiguous references to characters
and other entities throughout a story, eliminating the need for name-based matching.
"""

import pytest

from backend.core.types import (
    EntityDefinition,
    CharacterBible,
    StoryMetadata,
    StorySpread,
    StoryReferenceSheets,
    CharacterReferenceSheet,
    StyleDefinition,
)


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

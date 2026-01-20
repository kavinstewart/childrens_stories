"""
Tests for robust entity-to-bible matching system.

TDD tests for:
- story-cd8g: Add entity_id to EntityBibleSignature output schema
- story-3wpp: Add DSPy assertions for bible completeness
- story-xjl5: Add deterministic fallback matching for bible-entity resolution
- story-qxij: Add validation gate to prevent 0-bible illustrated stories

Root cause: BibleGenerator._match_bibles_to_entity_ids() uses exact string matching,
so "Otto the Otter" != "Otto" causes 0 matches and 0 character references.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.core.types import EntityDefinition, EntityBible


# =============================================================================
# Test 1: Schema Change - Entity ID in Bible Output
# =============================================================================

class TestBibleOutputEntityId:
    """Tests for entity_id field in bible output format."""

    @pytest.fixture
    def bible_generator(self):
        from backend.core.modules.bible_generator import BibleGenerator
        return BibleGenerator()

    def test_parse_entity_bibles_with_entity_id(self, bible_generator):
        """Should parse ENTITY_ID field from bible output."""
        bibles_text = """ENTITY_ID: @e1
CHARACTER: Otto
SPECIES: river otter
AGE_APPEARANCE: young adult
BODY: sleek brown body
FACE: round whiskered face
EYES: dark friendly eyes
CLOTHING: none
SIGNATURE_ITEM: smooth river stone
COLOR_PALETTE: brown, blue, cream
STYLE_TAGS: warm, friendly

ENTITY_ID: @e2
CHARACTER: Wes
SPECIES: weasel
AGE_APPEARANCE: young adult
BODY: small slender body
FACE: pointed snout
EYES: sharp curious eyes
CLOTHING: none
SIGNATURE_ITEM: none
COLOR_PALETTE: brown, tan, white
STYLE_TAGS: warm, friendly"""

        bibles = bible_generator._parse_entity_bibles(bibles_text)

        assert len(bibles) == 2

        # Check first bible has entity_id
        otto = next((b for b in bibles if b.name == "Otto"), None)
        assert otto is not None
        assert otto.entity_id == "@e1"

        # Check second bible has entity_id
        wes = next((b for b in bibles if b.name == "Wes"), None)
        assert wes is not None
        assert wes.entity_id == "@e2"

    def test_parse_entity_bibles_without_entity_id_still_works(self, bible_generator):
        """Should still parse bibles without ENTITY_ID (backwards compat)."""
        bibles_text = """CHARACTER: Otto
SPECIES: river otter
AGE_APPEARANCE: young adult

CHARACTER: Wes
SPECIES: weasel
AGE_APPEARANCE: young adult"""

        bibles = bible_generator._parse_entity_bibles(bibles_text)

        assert len(bibles) == 2
        # entity_id should be None for legacy format
        assert all(b.entity_id is None for b in bibles)

    def test_forward_uses_entity_id_when_present(self, bible_generator):
        """forward() should key by entity_id when present in output."""
        entity_definitions = {
            "@e1": EntityDefinition("@e1", "Otto", "entity", "friendly otter"),
            "@e2": EntityDefinition("@e2", "Wes", "entity", "small weasel"),
        }

        with patch.object(bible_generator, 'generate') as mock_generate:
            mock_generate.return_value = MagicMock(entity_bibles="""ENTITY_ID: @e1
CHARACTER: Otto the Otter
SPECIES: river otter

ENTITY_ID: @e2
CHARACTER: Wes the Weasel
SPECIES: weasel""")

            result = bible_generator.forward(
                title="Test Story",
                story_text="Otto and Wes are friends.",
                entity_definitions=entity_definitions,
            )

            # Should be keyed by entity_id, even though CHARACTER names differ
            assert "@e1" in result
            assert "@e2" in result
            # Name embellishment doesn't matter when entity_id is present
            assert result["@e1"].name == "Otto the Otter"


# =============================================================================
# Test 2: Deterministic Fallback Matching
# =============================================================================

class TestDeterministicFallbackMatching:
    """Tests for deterministic fallback when entity_id is not in output."""

    @pytest.fixture
    def bible_generator(self):
        from backend.core.modules.bible_generator import BibleGenerator
        return BibleGenerator()

    @pytest.fixture
    def entity_definitions(self):
        return {
            "@e1": EntityDefinition("@e1", "Otto", "entity", "friendly river otter"),
            "@e2": EntityDefinition("@e2", "Wes", "entity", "small weasel"),
            "@e3": EntityDefinition("@e3", "The River", "entity", "cool deep river"),
        }

    def test_fallback_exact_match(self, bible_generator, entity_definitions):
        """Fallback should match exact names (case-insensitive)."""
        bibles = [
            EntityBible(name="Otto", species="otter"),
            EntityBible(name="Wes", species="weasel"),
        ]

        result = bible_generator._match_bibles_to_entity_ids(bibles, entity_definitions)

        assert "@e1" in result
        assert "@e2" in result
        assert result["@e1"].name == "Otto"

    def test_fallback_containment_entity_in_bible(self, bible_generator, entity_definitions):
        """Fallback should match when entity name is contained in bible name."""
        bibles = [
            EntityBible(name="Otto the Otter", species="otter"),
            EntityBible(name="Wes the Weasel", species="weasel"),
        ]

        result = bible_generator._match_bibles_to_entity_ids(bibles, entity_definitions)

        # "Otto" is contained in "Otto the Otter"
        assert "@e1" in result
        assert "@e2" in result

    def test_fallback_containment_bible_in_entity(self, bible_generator, entity_definitions):
        """Fallback should match when bible name is contained in entity name."""
        # Edge case: bible has shorter name
        bibles = [
            EntityBible(name="River", species="location"),
        ]

        result = bible_generator._match_bibles_to_entity_ids(bibles, entity_definitions)

        # "River" is contained in "The River"
        assert "@e3" in result

    def test_fallback_token_subset(self, bible_generator, entity_definitions):
        """Fallback should match when entity tokens are subset of bible tokens."""
        bibles = [
            EntityBible(name="Otto the River Otter", species="otter"),
        ]

        result = bible_generator._match_bibles_to_entity_ids(bibles, entity_definitions)

        # {"otto"} is subset of {"otto", "the", "river", "otter"}
        assert "@e1" in result

    def test_fallback_ignores_articles(self, bible_generator, entity_definitions):
        """Fallback should handle articles (the, a, an) gracefully."""
        bibles = [
            EntityBible(name="River", species="location"),
        ]

        result = bible_generator._match_bibles_to_entity_ids(bibles, entity_definitions)

        # "River" matches "The River" (ignoring "The")
        assert "@e3" in result

    def test_fallback_no_match_returns_empty(self, bible_generator, entity_definitions):
        """Fallback should return empty dict for completely different names."""
        bibles = [
            EntityBible(name="Completely Different Name", species="unknown"),
        ]

        result = bible_generator._match_bibles_to_entity_ids(bibles, entity_definitions)

        # No match possible
        assert len(result) == 0

    def test_fallback_ambiguous_match_resolved_by_best_fit(self, bible_generator):
        """When multiple entities could match, prefer best fit."""
        entity_definitions = {
            "@e1": EntityDefinition("@e1", "Big Bear", "entity", "large bear"),
            "@e2": EntityDefinition("@e2", "Baby Bear", "entity", "small bear"),
        }

        bibles = [
            EntityBible(name="Big Bear", species="bear"),
            EntityBible(name="Baby Bear", species="bear"),
        ]

        result = bible_generator._match_bibles_to_entity_ids(bibles, entity_definitions)

        # Each should match its exact counterpart
        assert "@e1" in result
        assert "@e2" in result
        assert result["@e1"].name == "Big Bear"
        assert result["@e2"].name == "Baby Bear"


# =============================================================================
# Test 3: Validation Gate
# =============================================================================

class TestBibleCompletenessValidation:
    """Tests for validation that all entities have bibles."""

    @pytest.fixture
    def bible_generator(self):
        from backend.core.modules.bible_generator import BibleGenerator
        return BibleGenerator()

    def test_validate_completeness_all_present(self, bible_generator):
        """Validation passes when all entities have bibles."""
        entity_definitions = {
            "@e1": EntityDefinition("@e1", "Otto", "entity", "otter"),
            "@e2": EntityDefinition("@e2", "Wes", "entity", "weasel"),
        }

        bibles = {
            "@e1": EntityBible(name="Otto"),
            "@e2": EntityBible(name="Wes"),
        }

        # Should not raise
        missing = bible_generator._validate_bible_completeness(bibles, entity_definitions)
        assert missing == []

    def test_validate_completeness_missing_entity(self, bible_generator):
        """Validation detects missing entity bibles."""
        entity_definitions = {
            "@e1": EntityDefinition("@e1", "Otto", "entity", "otter"),
            "@e2": EntityDefinition("@e2", "Wes", "entity", "weasel"),
            "@e3": EntityDefinition("@e3", "River", "entity", "river"),
        }

        bibles = {
            "@e1": EntityBible(name="Otto"),
            # @e2 and @e3 missing
        }

        missing = bible_generator._validate_bible_completeness(bibles, entity_definitions)
        assert "@e2" in missing
        assert "@e3" in missing
        assert "@e1" not in missing

    def test_validate_completeness_empty_bibles(self, bible_generator):
        """Validation detects completely empty bible dict."""
        entity_definitions = {
            "@e1": EntityDefinition("@e1", "Otto", "entity", "otter"),
        }

        bibles = {}

        missing = bible_generator._validate_bible_completeness(bibles, entity_definitions)
        assert "@e1" in missing


# =============================================================================
# Test 4: Story Generation Validation Gate
# =============================================================================

class TestStoryGenerationValidationGate:
    """Tests for validation gate in story generation pipeline."""

    def test_illustrated_story_requires_character_refs(self):
        """Illustrated story should fail if 0 character refs generated."""
        from backend.core.programs.story_generator import StoryGenerator
        from backend.core.types import StoryMetadata, StorySpread, StyleDefinition

        # This tests the validation logic, not the full pipeline
        # The generator should raise or retry when entity_bibles is empty

        generator = StoryGenerator(lm=MagicMock())

        # Create a story with entity definitions but empty bibles
        # The generate_illustrated method should detect this

        # We'll test the validation helper directly
        entity_definitions = {
            "@e1": EntityDefinition("@e1", "Otto", "entity", "otter"),
        }
        entity_bibles = {}  # Empty - this is the failure case

        # Validation should detect the mismatch
        from backend.core.modules.bible_generator import BibleGenerator
        bg = BibleGenerator()
        missing = bg._validate_bible_completeness(entity_bibles, entity_definitions)

        assert len(missing) > 0, "Should detect missing bibles"


# =============================================================================
# Test 5: Entity ID in EntityBible dataclass
# =============================================================================

class TestEntityBibleEntityIdField:
    """Tests for entity_id field on EntityBible dataclass."""

    def test_entity_bible_has_entity_id_field(self):
        """EntityBible should have optional entity_id field."""
        bible = EntityBible(
            name="Otto",
            species="otter",
            entity_id="@e1",
        )

        assert bible.entity_id == "@e1"

    def test_entity_bible_entity_id_defaults_none(self):
        """EntityBible entity_id should default to None."""
        bible = EntityBible(name="Otto", species="otter")

        assert bible.entity_id is None

    def test_entity_bible_to_dict_includes_entity_id(self):
        """EntityBible.to_dict() should include entity_id."""
        bible = EntityBible(
            name="Otto",
            species="otter",
            entity_id="@e1",
        )

        d = bible.to_dict()

        assert "entity_id" in d
        assert d["entity_id"] == "@e1"

    def test_entity_bible_from_dict_restores_entity_id(self):
        """EntityBible.from_dict() should restore entity_id."""
        data = {
            "name": "Otto",
            "species": "otter",
            "entity_id": "@e1",
        }

        bible = EntityBible.from_dict(data)

        assert bible.entity_id == "@e1"


# =============================================================================
# Test 6: Input Format Change
# =============================================================================

class TestBibleGeneratorInputFormat:
    """Tests for updated input format to bible generator."""

    @pytest.fixture
    def bible_generator(self):
        from backend.core.modules.bible_generator import BibleGenerator
        return BibleGenerator()

    def test_format_entity_definitions_includes_entity_id(self, bible_generator):
        """Input format should include entity_id for LLM to echo back."""
        entity_definitions = {
            "@e1": EntityDefinition("@e1", "Otto", "entity", "friendly otter"),
            "@e2": EntityDefinition("@e2", "Wes", "entity", "small weasel"),
        }

        formatted = bible_generator._format_entity_definitions(entity_definitions)

        # Should include entity IDs
        assert "@e1" in formatted
        assert "@e2" in formatted
        # Format should be: @e1: Otto | DETAILS: friendly otter
        assert "@e1: Otto" in formatted or "@e1 - Otto" in formatted or "ENTITY_ID: @e1" in formatted

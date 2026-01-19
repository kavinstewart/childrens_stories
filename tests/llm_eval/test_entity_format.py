"""
LLM evaluation tests for entity extraction format compliance.

Tests that LLMs correctly produce the [Entities] block with the required format:
    @e1: Character Name (brief description)

Each spread must have an [Entities: @e1, @e2] field listing visible entities.

Usage:
    # Test default model (uses GOOGLE_API_KEY if set)
    poetry run pytest tests/llm_eval/test_entity_format.py -v

    # Test specific model via DSPy
    poetry run pytest tests/llm_eval/test_entity_format.py -v --dspy-model=anthropic/claude-sonnet-4-5-20250929

    # Quick test with fewer goals
    poetry run pytest tests/llm_eval/test_entity_format.py::test_entity_format_quick -v

    # Run all models in sequence
    poetry run pytest tests/llm_eval/test_entity_format.py::test_entity_format_all_models -v
"""

import re
import pytest
import dspy
from dataclasses import dataclass
from typing import Optional

from backend.core.modules.direct_story_generator import DirectStoryGenerator


# Test goals designed to exercise different entity types
TEST_GOALS = [
    # Animal stories - entity names could be confused with species
    "A story about a brave little mouse named Pip who helps a lost butterfly find her way home",
    "A tale of friendship between a grumpy old cat named Whiskers and a cheerful puppy",

    # Human character stories
    "A young girl named Maya discovers she can talk to trees in her grandmother's garden",
    "Two siblings learn to share their toys during a rainy day stuck inside",

    # Stories with locations as key entities
    "The old lighthouse on Seagull Point that helps a fishing boat find its way through fog",
    "A magical treehouse that grants wishes to children who climb its branches",

    # Mixed entities (characters + locations + objects)
    "A baker and her magical oven create cookies that make people smile",
    "A knight must retrieve a golden crown from a dragon's mountain cave",
]

# Subset for quick testing
QUICK_GOALS = TEST_GOALS[:3]


@dataclass
class EntityFormatResult:
    """Results from analyzing entity format compliance."""
    has_entities_block: bool
    raw_entities_block: str
    total_entities: int
    compliant_entities: int
    non_compliant_entities: list[str]
    raw_output: str


def analyze_entity_format(raw_output: str) -> EntityFormatResult:
    """
    Analyze the entity format compliance in LLM output.

    Expected format:
        [Entities]
        @e1: Character Name (brief description)
        @e2: Another Name (brief description)
    """
    # Find [Entities] block
    entities_match = re.search(
        r'\[Entities\]\s*(.*?)(?=\n\s*(?:TITLE:|Spread\s+\d+:))',
        raw_output,
        re.DOTALL | re.IGNORECASE
    )

    if not entities_match:
        return EntityFormatResult(
            has_entities_block=False,
            raw_entities_block="",
            total_entities=0,
            compliant_entities=0,
            non_compliant_entities=[],
            raw_output=raw_output,
        )

    entities_block = entities_match.group(1).strip()

    # Compliant format: @e1: Name (description)
    # Entity ID, display name, and description in parentheses
    entity_pattern = re.compile(r'(@e\d+):\s*(.+?)\s*\((.+?)\)\s*$', re.MULTILINE)

    entity_matches = entity_pattern.findall(entities_block)
    total_entities = len(entity_matches)

    # All entities matching the pattern are compliant
    compliant_entities = total_entities

    # Find lines that look like entity definitions but don't match the pattern
    non_compliant_lines = []
    for line in entities_block.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Lines starting with @e but not matching pattern
        if line.startswith('@e') and not entity_pattern.match(line):
            non_compliant_lines.append(line)

    return EntityFormatResult(
        has_entities_block=True,
        raw_entities_block=entities_block,
        total_entities=total_entities,
        compliant_entities=compliant_entities,
        non_compliant_entities=non_compliant_lines,
        raw_output=raw_output,
    )


def analyze_entities_fields(raw_output: str) -> dict:
    """
    Analyze [Entities: ...] fields in spreads.

    Returns dict with:
        - total_spreads: number of spreads found
        - spreads_with_entities: number with [Entities:] field
        - spreads_using_entity_ids: number using @eN format
        - spreads_using_names: number using plain names
        - spreads_with_none: number with [Entities: none]
    """
    # Find all spread sections
    spread_pattern = re.compile(r'Spread\s+(\d+):', re.IGNORECASE)
    spreads = spread_pattern.findall(raw_output)
    total_spreads = len(spreads)

    # Find [Entities: ...] fields (the per-spread field, not the definition block)
    entities_pattern = re.compile(r'\[Entities:\s*(.+?)\]', re.IGNORECASE)
    entities_matches = entities_pattern.findall(raw_output)

    spreads_with_entities = len(entities_matches)
    spreads_using_entity_ids = 0
    spreads_using_names = 0
    spreads_with_none = 0

    for entities_content in entities_matches:
        content = entities_content.strip().lower()
        if content in ("none", "n/a", "no one", "nobody", ""):
            spreads_with_none += 1
        elif "@e" in entities_content:
            spreads_using_entity_ids += 1
        else:
            spreads_using_names += 1

    return {
        "total_spreads": total_spreads,
        "spreads_with_entities": spreads_with_entities,
        "spreads_using_entity_ids": spreads_using_entity_ids,
        "spreads_using_names": spreads_using_names,
        "spreads_with_none": spreads_with_none,
    }


class TestEntityFormatCompliance:
    """Tests for entity extraction format compliance."""

    @pytest.fixture
    def story_generator(self, dspy_model: Optional[str], dspy_lm: Optional[dspy.LM]):
        """Create a DirectStoryGenerator with the configured LM."""
        if dspy_lm:
            dspy.configure(lm=dspy_lm)
        return DirectStoryGenerator(include_examples=True, example_count=1)

    @pytest.mark.parametrize("goal", TEST_GOALS, ids=lambda g: g[:50])
    def test_entity_format(
        self,
        goal: str,
        story_generator: DirectStoryGenerator,
        dspy_model: Optional[str],
    ):
        """Test that entity format is compliant for each goal."""
        # Generate story
        result = story_generator.generate(goal=goal, reference_examples="")
        raw_output = result.story

        # Analyze entity format
        entity_result = analyze_entity_format(raw_output)
        entities_result = analyze_entities_fields(raw_output)

        # Build detailed failure message
        failure_details = []

        if not entity_result.has_entities_block:
            failure_details.append("[Entities] block is MISSING from output")

        if entity_result.non_compliant_entities:
            failure_details.append(
                f"Non-compliant entity lines ({len(entity_result.non_compliant_entities)}):\n"
                + "\n".join(f"  - {e}" for e in entity_result.non_compliant_entities)
            )

        if entities_result["total_spreads"] > 0:
            if entities_result["spreads_with_entities"] < entities_result["total_spreads"]:
                missing = entities_result["total_spreads"] - entities_result["spreads_with_entities"]
                failure_details.append(f"[Entities:] field missing from {missing} spread(s)")

            if entities_result["spreads_using_names"] > 0:
                failure_details.append(
                    f"{entities_result['spreads_using_names']} spread(s) use character names "
                    "instead of entity IDs (@eN)"
                )

        # Assert compliance
        assert entity_result.has_entities_block, (
            f"[Entities] block missing\n"
            f"Model: {dspy_model}\n"
            f"Goal: {goal}\n"
            f"First 500 chars of output:\n{raw_output[:500]}"
        )

        assert entity_result.compliant_entities > 0, (
            f"No compliant entities found\n"
            f"Model: {dspy_model}\n"
            f"Goal: {goal}\n"
            f"Raw entities block:\n{entity_result.raw_entities_block}\n"
            f"Issues:\n" + "\n".join(failure_details)
        )

    @pytest.mark.parametrize("goal", QUICK_GOALS, ids=lambda g: g[:50])
    def test_entity_format_quick(
        self,
        goal: str,
        story_generator: DirectStoryGenerator,
        dspy_model: Optional[str],
    ):
        """Quick test with subset of goals for fast validation."""
        result = story_generator.generate(goal=goal, reference_examples="")
        raw_output = result.story

        entity_result = analyze_entity_format(raw_output)

        assert entity_result.has_entities_block, f"[Entities] block missing for model {dspy_model}"
        assert entity_result.compliant_entities > 0, (
            f"No compliant entities for model {dspy_model}\n"
            f"Raw block: {entity_result.raw_entities_block}"
        )


# Models to test (DSPy format)
MODELS_TO_TEST = [
    ("gemini/gemini-3-pro-preview", "GOOGLE_API_KEY"),
    ("anthropic/claude-opus-4-5-20251101", "ANTHROPIC_API_KEY"),
    ("anthropic/claude-sonnet-4-5-20250929", "ANTHROPIC_API_KEY"),
]


def test_entity_format_all_models():
    """
    Run entity format test against all models and print comparison.

    This is a single test that runs all models for comparison,
    rather than separate parametrized tests.

    Results are written to tests/llm_eval/results/entity_results.md
    """
    import os
    from datetime import datetime
    from pathlib import Path

    results = {}
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    results_file = results_dir / "entity_results.md"

    for model_id, env_key in MODELS_TO_TEST:
        api_key = os.getenv(env_key)
        if not api_key:
            results[model_id] = {"status": "SKIPPED", "reason": f"{env_key} not set"}
            continue

        try:
            # Configure DSPy with this model
            lm = dspy.LM(
                model_id,
                api_key=api_key,
                max_tokens=4096,
                temperature=1.0,
                timeout=120,
            )
            dspy.configure(lm=lm)

            generator = DirectStoryGenerator(include_examples=True, example_count=1)

            # Test with first 3 goals
            model_results = {
                "stories_tested": 0,
                "entities_block_present": 0,
                "fully_compliant": 0,
                "non_compliant_count": 0,
                "failures": [],
            }

            for goal in QUICK_GOALS:
                try:
                    result = generator.generate(goal=goal, reference_examples="")
                    raw_output = result.story

                    entity_result = analyze_entity_format(raw_output)
                    model_results["stories_tested"] += 1

                    if entity_result.has_entities_block:
                        model_results["entities_block_present"] += 1

                    if (entity_result.has_entities_block and
                        entity_result.compliant_entities > 0 and
                        len(entity_result.non_compliant_entities) == 0):
                        model_results["fully_compliant"] += 1

                    model_results["non_compliant_count"] += len(entity_result.non_compliant_entities)

                    if entity_result.non_compliant_entities:
                        model_results["failures"].append({
                            "goal": goal[:40],
                            "non_compliant": entity_result.non_compliant_entities,
                        })

                except Exception as e:
                    model_results["failures"].append({
                        "goal": goal[:40],
                        "error": str(e),
                    })

            results[model_id] = model_results

        except Exception as e:
            results[model_id] = {"status": "ERROR", "reason": str(e)}

    # Print summary
    print("\n" + "=" * 70)
    print("ENTITY FORMAT COMPLIANCE RESULTS")
    print("=" * 70)

    for model_id, result in results.items():
        print(f"\n{model_id}:")

        if "status" in result:
            print(f"  Status: {result['status']} - {result.get('reason', '')}")
            continue

        tested = result["stories_tested"]
        present = result["entities_block_present"]
        compliant = result["fully_compliant"]
        non_compliant = result["non_compliant_count"]

        print(f"  Stories tested: {tested}")
        print(f"  [Entities] block present: {present}/{tested} ({100*present/tested:.0f}%)")
        print(f"  Fully compliant: {compliant}/{tested} ({100*compliant/tested:.0f}%)")
        print(f"  Non-compliant entities: {non_compliant}")

        if result["failures"]:
            print(f"  Failures ({len(result['failures'])}):")
            for fail in result["failures"][:3]:  # Show first 3
                if "error" in fail:
                    print(f"    - {fail['goal']}: ERROR - {fail['error'][:50]}")
                else:
                    print(f"    - {fail['goal']}: non-compliant: {fail['non_compliant']}")

    print("\n" + "=" * 70)

    # Determine recommendation
    compliant_models = [
        model_id for model_id, result in results.items()
        if isinstance(result, dict) and
        result.get("fully_compliant", 0) == result.get("stories_tested", 0) and
        result.get("stories_tested", 0) > 0
    ]

    if compliant_models:
        print(f"\nRECOMMENDATION: Use one of: {', '.join(compliant_models)}")
    else:
        print("\nWARNING: No model achieved 100% compliance. Parser improvements needed.")

    print("=" * 70 + "\n")

    # Write results to file
    with open(results_file, "w") as f:
        f.write("# Entity Extraction Format Compliance Results\n\n")
        f.write(f"Tests run: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("## Summary\n\n")
        f.write("| Model | [Entities] Block | Fully Compliant | Non-compliant |\n")
        f.write("|-------|------------------|-----------------|---------------|\n")

        for model_id, result in results.items():
            if "status" in result:
                f.write(f"| {model_id} | {result['status']} | - | {result.get('reason', '')} |\n")
            else:
                tested = result["stories_tested"]
                present = result["entities_block_present"]
                compliant = result["fully_compliant"]
                non_compliant = result["non_compliant_count"]
                f.write(
                    f"| {model_id} | {present}/{tested} ({100*present/tested:.0f}%) | "
                    f"**{compliant}/{tested} ({100*compliant/tested:.0f}%)** | {non_compliant} |\n"
                )

        if compliant_models:
            f.write(f"\n**Recommendation:** Use one of: {', '.join(compliant_models)}\n")
        else:
            f.write("\n**Warning:** No model achieved 100% compliance.\n")

    print(f"Results written to: {results_file}")

    # This test passes if we were able to run at least one model
    assert any(
        isinstance(r, dict) and "stories_tested" in r
        for r in results.values()
    ), "No models could be tested - check API keys"

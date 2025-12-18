#!/usr/bin/env python3
"""
Optimize the PageWriter signature using MIPROv2 zero-shot optimization.

This script uses DSPy's MIPROv2 optimizer to automatically generate and test
different prompt instructions for the page writer module.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import dspy
from backend.config import configure_dspy, get_inference_lm, get_reflection_lm
from backend.core.modules.outline_generator import OutlineGenerator
from backend.core.modules.page_generator import PageGenerator
from backend.core.signatures.page_writer import PageWriterSignature


# Training examples - just goals about science topics kids ask about
TRAINING_GOALS = [
    "explain what DNA is and why it makes us who we are",
    "teach how the nervous system sends messages through our body",
    "explain why we need to sleep and what happens when we dream",
    "teach about how plants make their own food from sunlight",
    "explain what germs are and how our body fights them",
    "teach about why the sky is blue and sunsets are orange",
    "explain how our heart pumps blood through our whole body",
    "teach about what dinosaurs were like and why they disappeared",
    "explain why we have seasons and how Earth moves around the sun",
    "teach about how magnets work and why they stick together",
    "explain what happens when we breathe and why we need oxygen",
    "teach about how rainbows form after a storm",
]

# Validation examples - different topics
VALIDATION_GOALS = [
    "explain how our ears hear sounds",
    "teach about why ice floats on water",
    "explain what gravity is and why things fall down",
    "teach about how butterflies transform from caterpillars",
    "explain why we get hungry and how food gives us energy",
]


def page_quality_metric(example, prediction, trace=None):
    """
    Evaluate page quality - returns a score from 0 to 1.

    Checks for:
    - Non-empty output
    - Reasonable word count
    - Engaging language (dialogue, action words)
    - Factual accuracy signals
    """
    page_text = prediction.page_text if hasattr(prediction, 'page_text') else None

    if not page_text:
        return 0.0

    score = 0.0

    # 1. Non-empty and reasonable length (0.3 points)
    word_count = len(page_text.split())
    if 20 <= word_count <= 60:
        score += 0.3
    elif 10 <= word_count <= 80:
        score += 0.15

    # 2. Has dialogue (0.2 points)
    if '"' in page_text or '"' in page_text:
        score += 0.2

    # 3. Has action/sensory words (0.2 points)
    action_words = ['jumped', 'ran', 'looked', 'smiled', 'laughed', 'whispered',
                    'shouted', 'giggled', 'wiggled', 'bounced', 'sparkled', 'glowed']
    if any(word in page_text.lower() for word in action_words):
        score += 0.2

    # 4. Avoids obvious AI-isms (0.15 points)
    ai_isms = ['delve', 'tapestry', 'venture', 'embark', 'journey of']
    if not any(phrase in page_text.lower() for phrase in ai_isms):
        score += 0.15

    # 5. No placeholder text (0.15 points)
    if '[' not in page_text and 'generation failed' not in page_text.lower():
        score += 0.15

    return score


def create_page_writing_task(goal: str):
    """Create a page-writing task from a goal by first generating an outline."""
    try:
        # Generate outline
        outline_gen = OutlineGenerator()
        outline = outline_gen(goal=goal)

        pages = outline.get_pages()
        if not pages:
            print(f"      Warning: No pages parsed for goal '{goal[:30]}...'")
            return None
    except Exception as e:
        print(f"      Warning: Failed to create task for '{goal[:30]}...': {e}")
        return None

    # Pick a middle page (more interesting than page 1)
    page_idx = min(3, len(pages) - 1)
    page_spec = pages[page_idx]["content"]

    # Get previous pages for context
    previous_text = ""
    if page_idx > 0:
        previous_text = pages[page_idx - 1]["content"]

    return dspy.Example(
        story_title=outline.title,
        characters=outline.characters,
        setting=outline.setting,
        page_number=page_idx + 1,
        total_pages=len(pages),
        page_spec=page_spec,
        previous_text=previous_text,
        target_word_count=35,
    ).with_inputs("story_title", "characters", "setting", "page_number",
                   "total_pages", "page_spec", "previous_text", "target_word_count")


def main():
    print("=" * 60)
    print("MIPROv2 Zero-Shot Optimization for PageWriter")
    print("=" * 60)

    # Configure DSPy with inference model
    print("\n1. Configuring DSPy...")
    configure_dspy(use_reflection_lm=False)

    # Create training examples
    print("\n2. Creating training examples from goals...")
    trainset = []
    for goal in TRAINING_GOALS:
        print(f"   - {goal[:50]}...")
        example = create_page_writing_task(goal)
        if example:
            trainset.append(example)
    print(f"   Created {len(trainset)} training examples")

    # Create validation examples
    print("\n3. Creating validation examples...")
    valset = []
    for goal in VALIDATION_GOALS:
        print(f"   - {goal[:50]}...")
        example = create_page_writing_task(goal)
        if example:
            valset.append(example)
    print(f"   Created {len(valset)} validation examples")

    # Create the module to optimize
    print("\n4. Setting up PageWriter module...")
    page_writer = dspy.ChainOfThought(PageWriterSignature)

    # Set up MIPROv2 optimizer
    print("\n5. Configuring MIPROv2 optimizer (zero-shot)...")
    optimizer = dspy.MIPROv2(
        metric=page_quality_metric,
        auto="light",  # Quick optimization (~7 trials)
        max_bootstrapped_demos=0,  # Zero-shot: no examples in prompt
        max_labeled_demos=0,
        num_threads=4,
        prompt_model=get_reflection_lm(),  # Use stronger model for instruction generation
    )

    # Run optimization
    print("\n6. Running optimization (this may take 10-20 minutes)...")
    print("   The optimizer will:")
    print("   - Generate instruction candidates")
    print("   - Test them using Bayesian optimization")
    print("   - Find the best prompt configuration")
    print()

    optimized_page_writer = optimizer.compile(
        page_writer,
        trainset=trainset,
        valset=valset,
    )

    # Save the optimized module
    print("\n7. Saving optimized module...")
    output_path = Path(__file__).parent.parent.parent / "optimized" / "page_writer_optimized.json"
    output_path.parent.mkdir(exist_ok=True)
    optimized_page_writer.save(str(output_path))
    print(f"   Saved to: {output_path}")

    # Test the optimized module
    print("\n8. Testing optimized module...")
    test_example = trainset[0]
    result = optimized_page_writer(
        story_title=test_example.story_title,
        characters=test_example.characters,
        setting=test_example.setting,
        page_number=test_example.page_number,
        total_pages=test_example.total_pages,
        page_spec=test_example.page_spec,
        previous_text=test_example.previous_text,
        target_word_count=test_example.target_word_count,
    )
    print(f"\n   Sample output:\n   {result.page_text}")

    print("\n" + "=" * 60)
    print("Optimization complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

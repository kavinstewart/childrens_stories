"""
GEPA-compatible metrics for story quality evaluation.

These metrics return both score AND textual feedback, which GEPA uses
to reflect on failures and improve prompts.
"""

import dspy
from typing import Optional


def story_quality_metric(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace: Optional[object] = None,
    pred_name: Optional[str] = None,
    pred_trace: Optional[object] = None,
) -> dspy.Prediction:
    """
    Evaluate overall story quality with rich feedback for GEPA.

    Args:
        example: DSPy Example with 'goal' and optionally 'reference_story'
        prediction: DSPy Prediction with generated story fields
        trace: Optional execution trace
        pred_name: Optional predictor name being evaluated
        pred_trace: Optional predictor-specific trace

    Returns:
        dspy.Prediction with 'score' (0-1 float) and 'feedback' (str)
    """
    goal = example.get("goal", "")
    story_text = prediction.get("story_text", "")

    # Calculate component scores
    feedback_parts = []
    scores = []

    # 1. Word count check (target: 400-600 words)
    word_count = len(story_text.split())
    if 400 <= word_count <= 600:
        word_score = 1.0
        feedback_parts.append(f"Word count ({word_count}) is in the ideal range (400-600).")
    elif 300 <= word_count <= 800:
        word_score = 0.7
        feedback_parts.append(
            f"Word count ({word_count}) is acceptable but not ideal. Target 400-600 words."
        )
    else:
        word_score = 0.3
        feedback_parts.append(
            f"Word count ({word_count}) is outside acceptable range. "
            f"{'Too short - add more detail and development.' if word_count < 300 else 'Too long - trim unnecessary content.'}"
        )
    scores.append(word_score)

    # 2. Goal/theme presence check
    goal_keywords = goal.lower().split()
    story_lower = story_text.lower()
    keyword_matches = sum(1 for kw in goal_keywords if kw in story_lower)
    theme_score = min(1.0, keyword_matches / max(len(goal_keywords), 1))

    if theme_score >= 0.5:
        feedback_parts.append("The story appears to address the learning goal.")
    else:
        feedback_parts.append(
            f"The story may not adequately address the goal: '{goal}'. "
            "Ensure the theme is woven throughout the narrative, not just mentioned once."
        )
    scores.append(theme_score)

    # 3. Structure check (beginning, middle, end indicators)
    structure_indicators = {
        "beginning": ["once upon", "one day", "there was", "lived a", "in a"],
        "middle": ["but then", "suddenly", "however", "tried to", "wanted to"],
        "end": ["finally", "at last", "and so", "the end", "happily", "learned"],
    }

    structure_score = 0.0
    structure_feedback = []
    for part, indicators in structure_indicators.items():
        if any(ind in story_lower for ind in indicators):
            structure_score += 0.33
        else:
            structure_feedback.append(part)

    if structure_score >= 0.66:
        feedback_parts.append("Story has clear structure with beginning, middle, and end.")
    else:
        missing = ", ".join(structure_feedback)
        feedback_parts.append(
            f"Story structure needs work. Consider strengthening the: {missing}. "
            "Use clear transitions and ensure a satisfying resolution."
        )
    scores.append(structure_score)

    # 4. Dialogue/engagement check
    has_dialogue = '"' in story_text or "'" in story_text
    has_action_words = any(
        word in story_lower
        for word in ["ran", "jumped", "laughed", "cried", "shouted", "whispered"]
    )

    engagement_score = 0.5
    if has_dialogue:
        engagement_score += 0.25
        feedback_parts.append("Good use of dialogue to bring characters to life.")
    else:
        feedback_parts.append(
            "Consider adding dialogue to make characters more engaging and the story more dynamic."
        )

    if has_action_words:
        engagement_score += 0.25
        feedback_parts.append("Story includes vivid action verbs.")
    else:
        feedback_parts.append(
            "Add more action verbs (ran, jumped, laughed) to make the story more vivid."
        )
    scores.append(engagement_score)

    # Calculate final score
    final_score = sum(scores) / len(scores)

    # Build comprehensive feedback
    feedback = "\n".join([f"- {part}" for part in feedback_parts])

    if final_score >= 0.8:
        verdict = "EXCELLENT: Story meets quality standards."
    elif final_score >= 0.6:
        verdict = "GOOD: Story is acceptable but has room for improvement."
    else:
        verdict = "NEEDS_WORK: Story requires significant revision."

    feedback = f"{verdict}\n\nDetails:\n{feedback}"

    return dspy.Prediction(score=final_score, feedback=feedback)

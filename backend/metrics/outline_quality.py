"""
GEPA-compatible metrics for outline quality evaluation.
"""

import dspy
from typing import Optional


def outline_quality_metric(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace: Optional[object] = None,
    pred_name: Optional[str] = None,
    pred_trace: Optional[object] = None,
) -> dspy.Prediction:
    """
    Evaluate outline quality with rich feedback for GEPA.

    Args:
        example: DSPy Example with 'goal'
        prediction: DSPy Prediction with outline fields
        trace: Optional execution trace
        pred_name: Optional predictor name being evaluated
        pred_trace: Optional predictor-specific trace

    Returns:
        dspy.Prediction with 'score' (0-1 float) and 'feedback' (str)
    """
    goal = example.get("goal", "")
    feedback_parts = []
    scores = []

    # 1. Check title exists and is appropriate
    title = prediction.get("title", "")
    if title and len(title) > 3:
        title_score = 1.0
        feedback_parts.append(f"Title '{title}' is present and appropriate length.")
    else:
        title_score = 0.0
        feedback_parts.append("Title is missing or too short. Create an engaging, memorable title.")
    scores.append(title_score)

    # 2. Check characters
    characters = prediction.get("characters", "")
    char_lines = [line.strip() for line in characters.split("\n") if line.strip()]
    if len(char_lines) >= 2:
        char_score = 1.0
        feedback_parts.append(f"Good character roster with {len(char_lines)} characters.")
    elif len(char_lines) == 1:
        char_score = 0.5
        feedback_parts.append(
            "Only one character defined. Consider adding a supporting character for interaction."
        )
    else:
        char_score = 0.0
        feedback_parts.append(
            "No characters defined. Create at least a protagonist and one supporting character."
        )
    scores.append(char_score)

    # 3. Check setting
    setting = prediction.get("setting", "")
    if len(setting) > 20:
        setting_score = 1.0
        feedback_parts.append("Setting is well-described.")
    elif setting:
        setting_score = 0.5
        feedback_parts.append("Setting needs more detail. Describe it vividly for illustrations.")
    else:
        setting_score = 0.0
        feedback_parts.append("Setting is missing. Define where and when the story takes place.")
    scores.append(setting_score)

    # 4. Check page breakdown
    page_breakdown = prediction.get("page_breakdown", "")
    page_count = page_breakdown.lower().count("page")
    if 12 <= page_count <= 20:
        page_score = 1.0
        feedback_parts.append(f"Good page breakdown with {page_count} pages.")
    elif 8 <= page_count <= 24:
        page_score = 0.7
        feedback_parts.append(
            f"Page count ({page_count}) is acceptable. Ideal range is 12-16 pages."
        )
    else:
        page_score = 0.3
        feedback_parts.append(
            f"Page count ({page_count}) is outside normal range. "
            f"{'Add more pages to develop the story.' if page_count < 8 else 'Consolidate pages to fit picture book format.'}"
        )
    scores.append(page_score)

    # 5. Check theme integration
    theme_integration = prediction.get("theme_integration", "")
    if theme_integration and len(theme_integration) > 30:
        theme_score = 1.0
        feedback_parts.append("Theme integration is well-explained.")
    else:
        theme_score = 0.3
        feedback_parts.append(
            f"Theme integration needs more detail. Explain how '{goal}' will be woven into the narrative."
        )
    scores.append(theme_score)

    # 6. Check plot has three acts
    plot_summary = prediction.get("plot_summary", "").lower()
    has_beginning = any(
        word in plot_summary for word in ["beginning", "start", "act 1", "setup"]
    )
    has_middle = any(
        word in plot_summary for word in ["middle", "conflict", "act 2", "challenge"]
    )
    has_end = any(
        word in plot_summary for word in ["end", "resolution", "act 3", "conclusion"]
    )

    plot_score = (has_beginning + has_middle + has_end) / 3
    if plot_score >= 0.66:
        feedback_parts.append("Plot summary covers all three acts.")
    else:
        missing = []
        if not has_beginning:
            missing.append("beginning/setup")
        if not has_middle:
            missing.append("middle/conflict")
        if not has_end:
            missing.append("end/resolution")
        feedback_parts.append(
            f"Plot summary missing: {', '.join(missing)}. Include all three acts explicitly."
        )
    scores.append(plot_score)

    # Calculate final score
    final_score = sum(scores) / len(scores)

    # Build comprehensive feedback
    feedback = "\n".join([f"- {part}" for part in feedback_parts])

    if final_score >= 0.8:
        verdict = "EXCELLENT: Outline is comprehensive and ready for story generation."
    elif final_score >= 0.6:
        verdict = "GOOD: Outline is usable but could be strengthened."
    else:
        verdict = "NEEDS_WORK: Outline requires significant improvement before proceeding."

    feedback = f"{verdict}\n\nDetails:\n{feedback}"

    return dspy.Prediction(score=final_score, feedback=feedback)

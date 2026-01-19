# DSPy & GEPA Patterns

## Dual-LM Architecture
- **Inference LM**: Qwen3-235B Instruct via Cerebras (fast, high-quality creative writing)
- **Reflection LM**: Strong model for GEPA analysis (gpt-4.1, claude-opus)

## Metric Functions for GEPA

GEPA requires metrics that return both score AND textual feedback. See `backend/metrics/story_quality.py` for the implementation pattern.

Key requirements:
- Return `dspy.Prediction(score=score, feedback=feedback)`
- Score is numeric (0-10)
- Feedback is textual explanation

## Optimization Pattern

See `backend/optimization/` for GEPA optimization scripts. The pattern:
1. Define metric with feedback
2. Create optimizer with `dspy.GEPA(metric=..., auto="medium", reflection_lm=...)`
3. Compile with `optimizer.compile(program, trainset=train, valset=val)`

## Development Workflow
1. Implement baseline - Get end-to-end pipeline working without optimization
2. Create training data - Goals + reference stories for optimization
3. Build metrics - Feedback-rich metrics for each component
4. Run GEPA - Optimize each component separately
5. Compose & test - Integrate optimized modules

# LLM Evaluation for Homograph Disambiguation

This test suite evaluates LLMs on their ability to disambiguate homographs (words spelled the same but pronounced differently based on meaning).

## Setup

1. Get an OpenRouter API key from https://openrouter.ai/
2. Set the environment variable:
   ```bash
   export OPENROUTER_API_KEY=sk-or-...
   ```

## Usage

### Test a single model
```bash
poetry run pytest tests/llm_eval/test_disambiguation.py -v --model=qwen/qwen3-8b
```

### Quick validation (50 cases)
```bash
poetry run pytest tests/llm_eval/test_disambiguation.py::test_disambiguation_quick -v --model=qwen/qwen3-8b
```

### Test with summary only (faster output)
```bash
poetry run pytest tests/llm_eval/test_disambiguation.py --model=qwen/qwen3-8b --tb=no -q
```

### Test specific homograph
```bash
poetry run pytest tests/llm_eval/test_disambiguation.py -v --model=qwen/qwen3-8b -k "read"
```

### View coverage report
```bash
poetry run python tests/llm_eval/test_cases.py
```

## Models to Test (Cheapest First)

### Tier 1: Ultra-Cheap ($0.01-0.04/1M input)
| Model | Input/1M | Output/1M |
|-------|----------|-----------|
| `liquid/lfm2-8b-a1b` | $0.01 | $0.02 |
| `ibm/granite-4.0-h-micro` | $0.017 | $0.11 |
| `google/gemma-3-4b-it` | $0.017 | $0.068 |
| `meta-llama/llama-3.2-3b-instruct` | $0.02 | $0.02 |
| `meta-llama/llama-3.1-8b-instruct` | $0.02 | $0.05 |
| `mistral/mistral-nemo` | $0.02 | $0.04 |
| `mistral/mistral-7b-instruct` | $0.028 | $0.054 |
| `qwen/qwen2.5-coder-7b-instruct` | $0.03 | $0.09 |
| `deepseek/deepseek-r1-distill-llama-70b` | $0.03 | $0.11 |
| `qwen/qwen3-8b` | $0.04 | $0.14 |

### Tier 2: Cheap ($0.05-0.15/1M input)
| Model | Input/1M | Output/1M |
|-------|----------|-----------|
| `qwen/qwen-turbo` | $0.05 | $0.20 |
| `google/gemini-2.0-flash-lite` | $0.075 | $0.30 |
| `mistral/ministral-8b` | $0.10 | $0.10 |
| `google/gemini-2.5-flash-lite` | $0.10 | $0.40 |
| `google/gemini-2.0-flash` | $0.10 | $0.40 |

### Tier 3: Budget Frontier ($0.20-0.50/1M input)
| Model | Input/1M | Output/1M |
|-------|----------|-----------|
| `deepseek/deepseek-chat` | $0.28 | $0.42 |
| `google/gemini-3-flash` | $0.50 | $3.00 |

## Test Cases

- **Standard cases**: 470 (47 homographs × 2 pronunciations × 5 sentences)
- **Edge cases**: 75 (questions, imperatives, negations, complex tenses)
- **Total**: 545 test cases

## Evaluation Strategy

1. Start with the cheapest model (`liquid/lfm2-8b-a1b`)
2. Run full test suite
3. If <100% accuracy, try next cheapest model
4. Continue until finding the cheapest model with 100% accuracy

## Recording Results

After running tests, record results in this format:

| Model | Pass Rate | Notes |
|-------|-----------|-------|
| `liquid/lfm2-8b-a1b` | TBD | |
| `qwen/qwen3-8b` | TBD | |
| ... | ... | |

## Files

- `test_cases.py` - 545 validated test cases
- `homographs.py` - Homograph data and prompt generation
- `test_disambiguation.py` - Pytest test file
- `conftest.py` - Pytest fixtures (model selection, OpenRouter client)

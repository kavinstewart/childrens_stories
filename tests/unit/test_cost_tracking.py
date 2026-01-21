"""Tests for cost tracking module."""

import pytest
from concurrent.futures import ThreadPoolExecutor
import asyncio

from backend.core.cost_tracking import (
    UsageData,
    start_tracking,
    get_current_usage,
    record_llm_usage,
    record_image_generation,
    record_llm_usage_from_history,
    reset_history_tracking,
    clear_tracking,
)


class TestUsageData:
    """Tests for UsageData dataclass."""

    def test_default_values(self):
        """UsageData initializes with zeros."""
        usage = UsageData()
        assert usage.llm_input_tokens == 0
        assert usage.llm_output_tokens == 0
        assert usage.llm_model == ""
        assert usage.llm_calls == 0
        assert usage.image_count == 0
        assert usage.image_model == ""
        assert usage.image_retries == 0

    def test_to_dict(self):
        """UsageData serializes to dict correctly."""
        usage = UsageData(
            llm_input_tokens=1000,
            llm_output_tokens=500,
            llm_model="gemini-3-pro-preview",
            llm_calls=3,
            image_count=12,
            image_model="gemini-3-pro-image-preview",
            image_retries=2,
        )
        result = usage.to_dict()
        assert result == {
            "llm_input_tokens": 1000,
            "llm_output_tokens": 500,
            "llm_model": "gemini-3-pro-preview",
            "llm_calls": 3,
            "image_count": 12,
            "image_model": "gemini-3-pro-image-preview",
            "image_retries": 2,
        }

    def test_from_dict(self):
        """UsageData can be created from dict."""
        data = {
            "llm_input_tokens": 1000,
            "llm_output_tokens": 500,
            "llm_model": "gemini-3-pro-preview",
            "llm_calls": 3,
            "image_count": 12,
            "image_model": "gemini-3-pro-image-preview",
            "image_retries": 2,
        }
        usage = UsageData.from_dict(data)
        assert usage.llm_input_tokens == 1000
        assert usage.llm_output_tokens == 500
        assert usage.llm_model == "gemini-3-pro-preview"


class TestContextVarTracking:
    """Tests for contextvar-based tracking."""

    def setup_method(self):
        """Clear tracking before each test."""
        clear_tracking()

    def teardown_method(self):
        """Clear tracking after each test."""
        clear_tracking()

    def test_no_tracking_by_default(self):
        """get_current_usage returns None when tracking not started."""
        assert get_current_usage() is None

    def test_start_tracking_returns_usage_data(self):
        """start_tracking returns a UsageData instance."""
        usage = start_tracking()
        assert isinstance(usage, UsageData)

    def test_get_current_usage_after_start(self):
        """get_current_usage returns the same instance after start_tracking."""
        usage = start_tracking()
        assert get_current_usage() is usage

    def test_record_llm_usage_accumulates(self):
        """record_llm_usage accumulates tokens across calls."""
        start_tracking()
        record_llm_usage(input_tokens=100, output_tokens=50, model="model-a")
        record_llm_usage(input_tokens=200, output_tokens=100, model="model-a")

        usage = get_current_usage()
        assert usage.llm_input_tokens == 300
        assert usage.llm_output_tokens == 150
        assert usage.llm_calls == 2
        assert usage.llm_model == "model-a"

    def test_record_llm_usage_without_tracking(self):
        """record_llm_usage is a no-op when tracking not started."""
        # Should not raise
        record_llm_usage(input_tokens=100, output_tokens=50, model="model-a")
        assert get_current_usage() is None

    def test_record_image_generation(self):
        """record_image_generation increments count and tracks model."""
        start_tracking()
        record_image_generation(model="image-model")
        record_image_generation(model="image-model")

        usage = get_current_usage()
        assert usage.image_count == 2
        assert usage.image_model == "image-model"
        assert usage.image_retries == 0

    def test_record_image_generation_retry(self):
        """record_image_generation tracks retries separately."""
        start_tracking()
        record_image_generation(model="image-model", was_retry=False)
        record_image_generation(model="image-model", was_retry=True)
        record_image_generation(model="image-model", was_retry=True)

        usage = get_current_usage()
        assert usage.image_count == 3
        assert usage.image_retries == 2

    def test_record_image_without_tracking(self):
        """record_image_generation is a no-op when tracking not started."""
        # Should not raise
        record_image_generation(model="image-model")
        assert get_current_usage() is None

    def test_clear_tracking(self):
        """clear_tracking resets the contextvar."""
        start_tracking()
        record_llm_usage(input_tokens=100, output_tokens=50, model="model")
        clear_tracking()
        assert get_current_usage() is None


class TestDSPyHistoryTracking:
    """Tests for DSPy history-based usage tracking."""

    def setup_method(self):
        """Clear tracking before each test."""
        clear_tracking()
        reset_history_tracking()

    def teardown_method(self):
        """Clear tracking after each test."""
        clear_tracking()
        reset_history_tracking()

    def test_record_from_empty_history(self):
        """No-op when LM history is empty."""
        start_tracking()
        mock_lm = MockLM(history=[])
        record_llm_usage_from_history(mock_lm)
        usage = get_current_usage()
        assert usage.llm_calls == 0

    def test_record_from_history_openai_style(self):
        """Extract usage from OpenAI-style response."""
        start_tracking()
        mock_lm = MockLM(
            history=[
                {"response": {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}}
            ],
            model="gpt-5.2"
        )
        record_llm_usage_from_history(mock_lm)
        usage = get_current_usage()
        assert usage.llm_input_tokens == 100
        assert usage.llm_output_tokens == 50
        assert usage.llm_calls == 1
        assert usage.llm_model == "gpt-5.2"

    def test_record_from_history_gemini_style(self):
        """Extract usage from Gemini-style response."""
        start_tracking()
        mock_lm = MockLM(
            history=[
                {"response": {"usage": {"input_tokens": 200, "output_tokens": 100}}}
            ],
            model="gemini/gemini-3-pro-preview"
        )
        record_llm_usage_from_history(mock_lm)
        usage = get_current_usage()
        assert usage.llm_input_tokens == 200
        assert usage.llm_output_tokens == 100
        assert usage.llm_model == "gemini-3-pro-preview"  # Provider prefix stripped

    def test_record_multiple_history_entries(self):
        """Accumulate usage from multiple history entries."""
        start_tracking()
        mock_lm = MockLM(
            history=[
                {"response": {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}},
                {"response": {"usage": {"prompt_tokens": 200, "completion_tokens": 100}}},
            ],
            model="gpt-5.2"
        )
        record_llm_usage_from_history(mock_lm)
        usage = get_current_usage()
        assert usage.llm_input_tokens == 300
        assert usage.llm_output_tokens == 150
        assert usage.llm_calls == 2

    def test_incremental_history_tracking(self):
        """Only record new entries since last check."""
        start_tracking()
        mock_lm = MockLM(
            history=[
                {"response": {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}},
            ],
            model="gpt-5.2"
        )
        record_llm_usage_from_history(mock_lm)

        # Add more history
        mock_lm.history.append(
            {"response": {"usage": {"prompt_tokens": 200, "completion_tokens": 100}}}
        )
        record_llm_usage_from_history(mock_lm)

        usage = get_current_usage()
        assert usage.llm_input_tokens == 300
        assert usage.llm_output_tokens == 150
        assert usage.llm_calls == 2

    def test_no_tracking_returns_none(self):
        """No-op when tracking not started."""
        mock_lm = MockLM(
            history=[
                {"response": {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}},
            ]
        )
        record_llm_usage_from_history(mock_lm)  # Should not raise
        assert get_current_usage() is None

    def test_lm_without_history(self):
        """No-op when LM has no history attribute."""
        start_tracking()

        class NoHistoryLM:
            pass

        record_llm_usage_from_history(NoHistoryLM())
        usage = get_current_usage()
        assert usage.llm_calls == 0


class MockLM:
    """Mock DSPy LM for testing."""

    def __init__(self, history=None, model="test-model"):
        self.history = history or []
        self.model = model


class TestContextIsolation:
    """Tests for context isolation across threads/tasks."""

    def setup_method(self):
        """Clear tracking before each test."""
        clear_tracking()

    def teardown_method(self):
        """Clear tracking after each test."""
        clear_tracking()

    def test_thread_isolation(self):
        """Each thread has its own tracking context."""
        results = {}

        def worker(name, input_tokens):
            start_tracking()
            record_llm_usage(input_tokens=input_tokens, output_tokens=10, model="model")
            usage = get_current_usage()
            results[name] = usage.llm_input_tokens

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker, "thread1", 100)
            f2 = executor.submit(worker, "thread2", 200)
            f1.result()
            f2.result()

        assert results["thread1"] == 100
        assert results["thread2"] == 200

    def test_async_task_isolation(self):
        """Each async task has its own tracking context."""

        async def worker(name, input_tokens):
            start_tracking()
            record_llm_usage(input_tokens=input_tokens, output_tokens=10, model="model")
            await asyncio.sleep(0)  # Yield to other tasks
            usage = get_current_usage()
            return name, usage.llm_input_tokens

        async def run_tasks():
            task1 = asyncio.create_task(worker("task1", 100))
            task2 = asyncio.create_task(worker("task2", 200))
            return await asyncio.gather(task1, task2)

        results = dict(asyncio.run(run_tasks()))
        assert results["task1"] == 100
        assert results["task2"] == 200

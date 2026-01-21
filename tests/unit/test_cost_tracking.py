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


class TestCopyContextSharing:
    """Tests for copy_context() sharing UsageData across ThreadPoolExecutor workers."""

    def setup_method(self):
        """Clear tracking before each test."""
        clear_tracking()

    def teardown_method(self):
        """Clear tracking after each test."""
        clear_tracking()

    def test_copy_context_shares_usage_across_workers(self):
        """Verify per-submission copy_context() shares UsageData across ThreadPoolExecutor workers."""
        from contextvars import copy_context

        start_tracking()

        def worker():
            record_image_generation(model="test-model")

        # Per-submission copy_context() - each worker gets its own Context but shares UsageData
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(copy_context().run, worker) for _ in range(10)]
            for f in futures:
                f.result()

        usage = get_current_usage()
        assert usage.image_count == 10  # All 10 recorded to shared UsageData

    def test_copy_context_thread_safe_under_contention(self):
        """Verify thread-safe counting under high contention."""
        from contextvars import copy_context

        start_tracking()

        def worker():
            # Multiple operations per worker to increase contention
            for _ in range(10):
                record_image_generation(model="test-model")

        # Per-submission copy_context() avoids Context reentrance issues
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(copy_context().run, worker) for _ in range(20)]
            for f in futures:
                f.result()

        usage = get_current_usage()
        assert usage.image_count == 200  # 20 workers * 10 ops each

    def test_copy_context_with_slow_operations(self):
        """Verify per-submission copy_context works with slow operations.

        Regression test for Context reentrance bug (story-lhyh).
        With a shared Context object, slow operations would cause:
        RuntimeError: cannot enter context: <Context object> is already entered
        """
        from contextvars import copy_context
        import time

        start_tracking()

        def slow_worker():
            time.sleep(0.05)  # 50ms - enough to cause overlap with 4 workers
            record_image_generation(model="test-model")

        # Per-submission copy_context() is REQUIRED for slow operations
        # Using a shared ctx would fail with "cannot enter context" error
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(copy_context().run, slow_worker) for _ in range(8)]
            for f in futures:
                f.result()

        usage = get_current_usage()
        assert usage.image_count == 8


class TestUsageDataThreadSafety:
    """Tests for UsageData thread-safety and serialization."""

    def test_to_dict_excludes_lock(self):
        """to_dict() should not include _lock field."""
        usage = UsageData(
            llm_input_tokens=100,
            image_count=5,
        )
        result = usage.to_dict()
        assert "_lock" not in result
        assert "lock" not in result

    def test_from_dict_creates_lock(self):
        """from_dict() should create a working lock automatically."""
        data = {"llm_input_tokens": 100, "image_count": 5}
        usage = UsageData.from_dict(data)

        # Verify lock exists and is functional
        assert hasattr(usage, "_lock")

        # Verify lock can be acquired and released (proves it's a real lock)
        acquired = usage._lock.acquire(blocking=False)
        assert acquired
        usage._lock.release()

    def test_equality_ignores_lock(self):
        """Two UsageData instances with same values should be equal."""
        u1 = UsageData(llm_input_tokens=100, image_count=5)
        u2 = UsageData(llm_input_tokens=100, image_count=5)

        # They have different lock objects
        assert u1._lock is not u2._lock

        # But should still be equal
        assert u1 == u2

    def test_equality_detects_differences(self):
        """UsageData with different values should not be equal."""
        u1 = UsageData(llm_input_tokens=100, image_count=5)
        u2 = UsageData(llm_input_tokens=100, image_count=6)

        assert u1 != u2

    def test_lock_not_in_repr(self):
        """Lock should not appear in repr output."""
        usage = UsageData(image_count=5)
        repr_str = repr(usage)
        assert "_lock" not in repr_str
        assert "Lock" not in repr_str

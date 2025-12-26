"""Background job manager using ThreadPoolExecutor."""

from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Callable

from ..config import MAX_CONCURRENT_JOBS


class JobManager:
    """Manages background story generation jobs."""

    def __init__(self, max_workers: int = 2):
        """
        Initialize the job manager.

        Args:
            max_workers: Maximum concurrent story generations.
                        Keep low since generation is resource-intensive.
        """
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="story_gen_",
        )
        self._futures: dict[str, Future] = {}
        self._lock = threading.Lock()

    def submit(self, job_id: str, fn: Callable, *args, **kwargs) -> None:
        """
        Submit a job for background execution.

        Args:
            job_id: Unique identifier for the job
            fn: Function to execute
            *args, **kwargs: Arguments to pass to the function
        """
        future = self.executor.submit(fn, *args, **kwargs)

        with self._lock:
            self._futures[job_id] = future

        # Clean up completed future when done
        def cleanup(f):
            with self._lock:
                if job_id in self._futures:
                    del self._futures[job_id]

        future.add_done_callback(cleanup)

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor."""
        self.executor.shutdown(wait=wait)


# Global instance - story generation is resource-intensive, limit concurrency
job_manager = JobManager(max_workers=MAX_CONCURRENT_JOBS)

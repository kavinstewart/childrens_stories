"""Background job manager using ThreadPoolExecutor."""

from concurrent.futures import ThreadPoolExecutor, Future
import threading
from typing import Callable, Optional

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

    def is_running(self, job_id: str) -> bool:
        """Check if a job is currently running."""
        with self._lock:
            future = self._futures.get(job_id)
            return future is not None and future.running()

    def get_future(self, job_id: str) -> Optional[Future]:
        """Get the Future object for a job if it exists."""
        with self._lock:
            return self._futures.get(job_id)

    def cancel(self, job_id: str) -> bool:
        """
        Attempt to cancel a job.

        Returns True if cancelled, False if already running/completed.
        """
        with self._lock:
            future = self._futures.get(job_id)
            if future:
                return future.cancel()
            return False

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor."""
        self.executor.shutdown(wait=wait)


# Global instance - story generation is resource-intensive, limit concurrency
job_manager = JobManager(max_workers=MAX_CONCURRENT_JOBS)

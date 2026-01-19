#!/usr/bin/env python3
"""Run the ARQ worker for background story generation."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from arq import run_worker

from backend.worker import WorkerSettings


def main():
    """Run the ARQ worker."""
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()

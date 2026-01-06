"""Progress bar and ETA utilities."""

import time
from typing import Optional

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)


class ProgressTracker:
    """Single-line progress tracker with ETA."""

    def __init__(self, total: int, description: str = "Processing"):
        """
        Initialize progress tracker.

        Args:
            total: Total number of items
            description: Description text
        """
        self.total = total
        self.description = description
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=None,  # Will use default console
            transient=False,
            refresh_per_second=2,  # Limit refresh rate to reduce flicker
        )
        self.task_id: Optional[int] = None
        self.start_time: Optional[float] = None

    def __enter__(self):
        """Enter context manager."""
        self.progress.__enter__()
        self.task_id = self.progress.add_task(
            self.description, total=self.total
        )
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.progress.__exit__(exc_type, exc_val, exc_tb)

    def update(self, advance: int = 1):
        """Update progress."""
        if self.task_id is not None:
            self.progress.update(self.task_id, advance=advance)

    def set_description(self, description: str):
        """Update description."""
        if self.task_id is not None:
            self.progress.update(
                self.task_id, description=description
            )


"""Output filtering and logging utilities."""

import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

# Global console instance
console = Console(file=sys.stdout, stderr=False)
error_console = Console(file=sys.stderr, stderr=True)


class OutputFilter:
    """Filtered output manager."""

    def __init__(self, verbose: bool = False):
        """
        Initialize output filter.

        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.console = console
        self.error_console = error_console

    def info(self, message: str, verbose_only: bool = False):
        """Print info message."""
        if verbose_only and not self.verbose:
            return
        self.console.print(f"[blue]ℹ[/blue] {message}")

    def success(self, message: str):
        """Print success message."""
        self.console.print(f"[green]✓[/green] {message}")

    def warning(self, message: str):
        """Print warning message."""
        self.error_console.print(f"[yellow]⚠[/yellow] {message}")

    def error(self, message: str):
        """Print error message."""
        self.error_console.print(f"[red]✗[/red] {message}")

    def debug(self, message: str):
        """Print debug message."""
        if self.verbose:
            self.console.print(f"[dim]DEBUG:[/dim] {message}")

    def print(self, *args, **kwargs):
        """Print to console."""
        self.console.print(*args, **kwargs)


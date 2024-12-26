import logging
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, TimeRemainingColumn, TaskProgressColumn


def create_logger(log_level: str) -> logging.Logger:
    """Create rich logger"""
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="%H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    return logging.getLogger("rich")


def create_progress() -> Progress:
    """Create and start rich progress"""
    rich_progress = Progress(
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(elapsed_when_finished=True, compact=True),
        "{task.description}",
    )
    rich_progress.start()
    return rich_progress

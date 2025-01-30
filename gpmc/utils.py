import logging

from rich.logging import RichHandler
import requests
from requests.adapters import HTTPAdapter, Retry


def new_session_with_retries() -> requests.Session:
    """Create a new request session with retry mechanism"""
    # https://stackoverflow.com/questions/23267409/how-to-implement-retry-mechanism-into-python-requests-library
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s


def urlsafe_base64(base64_hash: str) -> str:
    """Convert Base64 str to URL-safe Base64 string."""
    return base64_hash.replace("+", "-").replace("/", "_").rstrip("=")


def create_logger(log_level: str) -> logging.Logger:
    """Create rich logger"""
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="%H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    return logging.getLogger("rich")

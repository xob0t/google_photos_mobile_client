import logging
import binascii
import base64

from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, TimeRemainingColumn, TaskProgressColumn
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


def process_sha1_hash(sha1_hash: str | bytes) -> tuple[bytes, str]:
    """
    Process SHA1 hash in various formats and return both bytes and base64 representations.

    Args:
        sha1_hash: Input hash (str, bytes)

    Returns:
        tuple: (sha1_hash_bytes, sha1_hash_b64)
    """
    match sha1_hash:
        case bytes(sha1_hash):
            return sha1_hash, base64.b64encode(sha1_hash).decode("utf-8")
        case str(sha1_hash):
            return _process_string_hash(sha1_hash)
        case _:
            raise TypeError(f"Expected str or bytes, got {type(sha1_hash)}")


def _process_string_hash(sha1_hash: str) -> tuple[bytes, str]:
    """Process string hash input"""
    try:
        if _is_hash_hexadec(sha1_hash):
            # Convert hex string to bytes
            sha1_hash_bytes = bytes.fromhex(sha1_hash)
            sha1_hash_b64 = base64.b64encode(sha1_hash_bytes).decode("utf-8")
        else:
            # Assume base64 encoded
            sha1_hash_bytes = base64.b64decode(sha1_hash)
            sha1_hash_b64 = sha1_hash
        return sha1_hash_bytes, sha1_hash_b64
    except (ValueError, binascii.Error) as e:
        raise ValueError(f"Invalid SHA1 hash format: {e}") from e


def _is_hash_hexadec(string: str) -> bool:
    """
    Check if the given string is a hexadecimal representation of a SHA-1 hash.
    """
    return len(string) == 40 and all(c in "0123456789abcdefABCDEF" for c in string)

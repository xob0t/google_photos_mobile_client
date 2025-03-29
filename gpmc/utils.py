import logging
import struct

from rich.logging import RichHandler
import requests
from requests.adapters import HTTPAdapter, Retry


def new_session_with_retries() -> requests.Session:
    """Create a new request session with retry mechanism"""
    # https://stackoverflow.com/questions/23267409/how-to-implement-retry-mechanism-into-python-requests-library
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
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


def int64_to_float(num: int) -> float:
    """Converts a 64-bit integer to its IEEE 754 double-precision floating-point representation."""
    # Pack the integer into 8 bytes (big-endian) and unpack as double
    return struct.unpack(">d", num.to_bytes(8, byteorder="big"))[0]


def int32_to_float(num: int) -> float:
    """Converts a 32-bit integer to its IEEE 754 double-precision floating-point representation."""
    # Pack the integer into 4 bytes (big-endian) and unpack as double
    return struct.unpack(">f", num.to_bytes(4, byteorder="big"))[0]


def fixed32_to_float(n: int) -> float:
    """Converts a scaled 32-bit signed integer to its floating-point value.

    Args:
        n: A 32-bit signed integer representing a scaled value (x * 10^7)

    Returns:
        The decoded floating-point value (n / 10^7)
    """
    if n > 2147483647:  # 2^31 - 1 (max positive 32-bit signed integer)
        n -= 4294967296  # 2^32

    return n / 10**7


def parse_email(s: str) -> str:
    """Parse email from auth_data"""
    for line in s.split("&"):
        if "Email" in line:
            value = line.split("=")[1]
            return value.replace("%40", "_")
    raise ValueError("No email value in auth_data")


def parse_language(s: str) -> str:
    """Parse language from auth_data"""
    for line in s.split("&"):
        if "lang" in line:
            return line.split("=")[1]
    raise ValueError("No language value in auth_data")

import binascii
import base64
from typing import Optional, Tuple
from pathlib import Path
import hashlib

from rich.progress import Progress
from rich.progress import TaskID


class HashHandler:
    def __init__(
        self,
        sha1_hash: Optional[str | bytes] = None,
        file_path: Optional[Path] = None,
        progress: Optional[Progress] = None,
        file_progress_id: Optional[TaskID] = None,
        show_progress: Optional[bool] = False,
    ) -> None:
        """
        Initialize the HashHandler with either a SHA1 hash or a file path.

        Args:
            sha1_hash (Optional[Union[str, bytes]]): The SHA1 hash as a string or bytes.
                If None, file_path must be provided.
            file_path (Optional[Path]): The path to the file from which to calculate the SHA1 hash.
                If None, sha1_hash must be provided.
            progress (Optional[Progress]): An optional Progress instance for tracking hash calculation.
            file_progress_id (Optional[TaskID]): An optional TaskID for progress tracking.
            show_progress (Optional[bool]): Whether to show progress during hash calculation.

        Raises:
            ValueError: If both sha1_hash and file_path are None.
        """
        if not sha1_hash and not file_path:
            raise ValueError("`sha1_hash` or `file_path` must be provided")
        self.progress = progress
        self.file_progress_id = file_progress_id
        self.show_progress = show_progress
        self.hash_bytes: bytes = b""
        self.hash_b64: str = ""
        self._process_args(sha1_hash, file_path)

    def _process_args(self, sha1_hash: Optional[str | bytes] = None, file_path: Optional[Path] = None) -> None:
        """
        Process the input SHA1 hash in various formats or calculate it from a file.

        Args:
            sha1_hash (Optional[Union[str, bytes]]): Input SHA1 hash in string or bytes format.
            file_path (Optional[Path]): The file path if the SHA1 hash is not provided.

        Raises:
            ValueError: If the hash format is invalid.
        """
        match sha1_hash:
            case bytes(sha1_hash):
                self.hash_bytes = sha1_hash
                self.hash_b64 = base64.b64encode(sha1_hash).decode("utf-8")
            case str(sha1_hash):
                self.hash_bytes, self.hash_b64 = self._process_string_hash(sha1_hash)
            case _:
                self.hash_bytes = self._calculate_sha1_hash(file_path, self.progress, self.file_progress_id, self.show_progress)
                self.hash_b64 = base64.b64encode(self.hash_bytes).decode("utf-8")

    def _calculate_sha1_hash(self, file_path: Path, progress: Optional[Progress] = None, file_progress_id: Optional[TaskID] = None, show_progress: Optional[bool] = False) -> bytes:
        """
        Calculate the SHA1 hash of a file in chunks, with optional progress tracking.

        Args:
            file_path (Path): The path to the file to be hashed.
            progress (Optional[Progress]): An optional Progress instance for tracking hash calculation.
            file_progress_id (Optional[TaskID]): An optional TaskID for progress tracking.
            show_progress (Optional[bool]): Whether to show progress during hash calculation.

        Returns:
            bytes: The calculated SHA1 hash as a byte array.
        """
        if progress and file_progress_id:
            progress.update(task_id=file_progress_id, description=f"Calculating Hash: {file_path.name}", visible=show_progress)

        hash_sha1 = hashlib.sha1()

        if progress:
            file_obj = progress.open(file_path, "rb", task_id=file_progress_id)
        else:
            file_obj = open(file_path, "rb")

        with file_obj as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_sha1.update(chunk)

        return hash_sha1.digest()

    def _process_string_hash(self, sha1_hash: str) -> Tuple[bytes, str]:
        """
        Process a string representation of a SHA1 hash.

        Args:
            sha1_hash (str): The SHA1 hash as a hexadecimal string or base64 encoded string.

        Returns:
            Tuple[bytes, str]: A tuple containing the SHA1 hash in bytes and base64 encoded string format.

        Raises:
            ValueError: If the SHA1 hash format is invalid.
        """
        try:
            if self._is_hash_hexadec(sha1_hash):
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

    def _is_hash_hexadec(self, string: str) -> bool:
        """
        Check if the given string is a valid hexadecimal representation of a SHA-1 hash.

        Args:
            string (str): The string to check.

        Returns:
            bool: True if the string is a valid hexadecimal SHA-1 hash, False otherwise.
        """
        return len(string) == 40 and all(c in "0123456789abcdefABCDEF" for c in string)

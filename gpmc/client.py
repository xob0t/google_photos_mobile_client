import time
from typing import Optional, Literal, Iterable
from concurrent.futures import ThreadPoolExecutor
import signal
import hashlib
import base64
import os
import mimetypes
from pathlib import Path

import blackboxprotobuf
from rich.progress import TaskID
from . import api_methods
from . import utils

# Make Ctrl+C work for cancelling threads
signal.signal(signal.SIGINT, signal.SIG_DFL)

DEFAULT_TIMEOUT = api_methods.DEFAULT_TIMEOUT


class Client:
    """Reverse engineered Google Photos mobile API client."""

    def __init__(self, auth_data: Optional[str] = None, timeout: Optional[int] = DEFAULT_TIMEOUT, log_level: Literal["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"] = "INFO") -> None:
        """
        Initialize the Google Photos mobile client.

        Args:
            auth_data: Google authentication data string. If not provided, will attempt to use
                      the `GP_AUTH_DATA` environment variable.
            log_level: Logging level to use. Must be one of "INFO", "DEBUG", "WARNING",
                      "ERROR", or "CRITICAL". Defaults to "INFO".
            timeout: Requests timeout, seconds. Defaults to DEFAULT_TIMEOUT.

        Raises:
            ValueError: If no auth_data is provided and GP_AUTH_DATA environment variable is not set.
            requests.HTTPError: If the authentication request fails.
        """
        self.logger = utils.create_logger(log_level)
        self.progress = utils.create_progress()
        self.valid_mimetypes = ["image/", "video/"]
        self.auth_data = auth_data or os.getenv("GP_AUTH_DATA")
        self.timeout = timeout

        if not self.auth_data:
            raise ValueError("`GP_AUTH_DATA` environment variable not set. Create it or provide `auth_data` as an argument.")
        self.auth_response = api_methods.get_auth_token(self.auth_data, timeout=self.timeout)

    def _upload_file(self, file_path: str | Path, sha1_hash: Optional[bytes | str] = None, show_progress: Optional[bool] = False, force_upload: Optional[bool] = False) -> dict[str, str]:
        """
        Upload a single file to Google Photos.

        Args:
            file_path: Path to the file to upload, can be string or Path object.
            sha1_hash: The file's SHA-1 hash, represented as bytes, a hexadecimal string, or a Base64-encoded string.
            show_progress: Whether to display upload progress in the console.
                         Defaults to False.
            force_upload: Whether to upload the file even if it's already present
                             in Google Photos (based on hash). Defaults to False.

        Returns:
            A dictionary mapping the absolute file path to its Google Photos media key.
            Example: {"/absolute/path/to/photo.jpg": "media_key_123"}

        Raises:
            FileNotFoundError: If the file does not exist.
            IOError: If there are issues reading the file.
            ValueError: If the file is empty or cannot be processed.
        """
        file_path = Path(file_path)
        file_size = file_path.stat().st_size

        if int(self.auth_response["Expiry"]) <= int(time.time()):
            # get a new token if current is expired
            self.auth_response = api_methods.get_auth_token(self.auth_data, timeout=self.timeout)

        bearer_token = self.auth_response["Auth"]

        file_progress = self.progress.add_task(description="placeholder", visible=False)

        if not sha1_hash:
            # Calculate new hash if none provided
            sha1_hash_bytes = self._calculate_sha1_hash(file_progress, file_path, show_progress)
            sha1_hash_b64 = base64.b64encode(sha1_hash_bytes).decode("utf-8")
        else:
            sha1_hash_bytes, sha1_hash_b64 = utils.process_sha1_hash(sha1_hash)

        if not force_upload:
            self.progress.update(task_id=file_progress, description=f"Checking: {file_path.name}")
            if remote_media_key := api_methods.find_remote_media_by_hash(sha1_hash_bytes, auth_token=bearer_token, timeout=self.timeout):
                self.progress.remove_task(file_progress)
                return {file_path.absolute().as_posix(): remote_media_key}

        upload_token = api_methods.get_upload_token(sha1_hash_b64, file_size, auth_token=bearer_token, timeout=self.timeout)
        self.progress.reset(task_id=file_progress)
        self.progress.update(task_id=file_progress, description=f"Uploading: {file_path.name}", visible=show_progress)
        with self.progress.open(file_path, "rb", task_id=file_progress) as file:
            upload_response = api_methods.upload_file(file=file, upload_token=upload_token, auth_token=bearer_token, timeout=self.timeout)
        self.progress.update(task_id=file_progress, description=f"Finalizing Upload: {file_path.name}")
        last_modified_timestamp = int(os.path.getmtime(file_path))
        media_key = api_methods.finalize_upload(
            upload_response_decoded=upload_response,
            file_name=file_path.name,
            sha1_hash=sha1_hash_bytes,
            auth_token=bearer_token,
            upload_timestamp=last_modified_timestamp,
            timeout=self.timeout,
        )
        self.progress.remove_task(file_progress)
        return {file_path.absolute().as_posix(): media_key}

    def _calculate_sha1_hash(self, file_progress: TaskID, file_path: Path, show_progress: Optional[bool] = False) -> bytes:
        """Calculate sha1 without loading whole file in memory"""
        self.progress.update(task_id=file_progress, description=f"Calculating Hash: {file_path.name}", visible=show_progress)
        hash_sha1 = hashlib.sha1()
        with self.progress.open(file_path, "rb", task_id=file_progress) as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_sha1.update(chunk)
        return hash_sha1.digest()

    def get_media_key_by_hash(self, sha1_hash: bytes | str) -> str | None:
        """
        Get a Google Photos media key by media's hash.

        Args:
            sha1_hash: The file's SHA-1 hash, represented as bytes, a hexadecimal string, or a Base64-encoded string.

        Returns:
            The Google Photos media key if the hash is found, otherwise None.
        """
        sha1_hash_bytes, _ = utils.process_sha1_hash(sha1_hash)

        if int(self.auth_response["Expiry"]) <= int(time.time()):
            # get a new token if current is expired
            self.auth_response = api_methods.get_auth_token(self.auth_data, timeout=self.timeout)

        bearer_token = self.auth_response["Auth"]
        return api_methods.find_remote_media_by_hash(sha1_hash_bytes, auth_token=bearer_token, timeout=self.timeout)

    def upload(
        self,
        target: str | Path | Iterable[str | Path],
        sha1_hash: Optional[bytes | str] = None,
        recursive: Optional[bool] = False,
        show_progress: Optional[bool] = False,
        threads: Optional[int] = 1,
        force_upload: Optional[int] = False,
    ) -> dict[str, str]:
        """
        Upload one or more files or directories to Google Photos.

        Args:
            target: A file path, directory path, or an iterable of such paths to upload.
            sha1_hash: The file's SHA-1 hash, represented as bytes, a hexadecimal string, or a Base64-encoded string.
                        Used to skip hash calculation. Only applies when uploading a single file.
            recursive: Whether to recursively search for media files in subdirectories.
                          Only applies when uploading directories. Defaults to True.
            show_progress: Whether to display upload progress in the console. Defaults to True.
            threads: Number of concurrent upload threads for multiple files. Defaults to 1.
            force_upload: Whether to upload files even if they're already present in
                             Google Photos (based on hash). Defaults to False.

        Returns:
            A dictionary mapping absolute file paths to their Google Photos media keys.
            Example: {
                "/path/to/photo1.jpg": "media_key_123",
                "/path/to/photo2.jpg": "media_key_456"
            }
        """
        if isinstance(target, (str, Path)):
            target = [target]

        if not isinstance(target, Iterable) or not all(isinstance(p, (str, Path)) for p in target):
            raise TypeError("`target` must be a file path, a directory path, or an iterable of such paths.")

        # Expand all paths to a flat list of files
        files_to_upload = [file for path in target for file in self._find_media_files(path, recursive=recursive)]

        if not files_to_upload:
            raise ValueError("No valid media files found to upload.")

        if len(files_to_upload) > 1:
            return self._upload_multiple(files_to_upload, threads=threads, show_progress=show_progress, force_upload=force_upload)

        return self._upload_file(files_to_upload[0], sha1_hash=sha1_hash, show_progress=show_progress, force_upload=force_upload)

    def _find_media_files(self, path: str | Path, recursive: Optional[bool] = False) -> list[Path]:
        """
        Find all valid media files in the specified path.

        Args:
            path: File or directory path to search for media files.
            recursive: Whether to search subdirectories recursively. Only applies
                          when path is a directory. Defaults to True.

        Returns:
            List of Path objects pointing to valid media files.

        Raises:
            ValueError: If the path is invalid, or if no valid media files are found,
                       or if a single file's mime type is not supported.
        """
        path = Path(path)

        if path.is_file():
            if any(mimetype_guess is not None and mimetype_guess.startswith(mimetype) for mimetype in self.valid_mimetypes if (mimetype_guess := mimetypes.guess_type(path)[0])):
                return [path]
            raise ValueError("File's mime type does not matches image or video mime type.")

        if not path.is_dir():
            raise ValueError("Invalid path. Please provide a file or directory path.")

        # Get list of files in directory
        files = []
        if recursive:
            for root, _, filenames in os.walk(path):
                for filename in filenames:
                    file_path = Path(root) / filename
                    files.append(file_path)
        else:
            files = [file for file in path.iterdir() if file.is_file()]

        if len(files) == 0:
            raise ValueError("No files in the directory.")

        media_files = [file for file in files if any(mimetype_guess is not None and mimetype_guess.startswith(mimetype) for mimetype in self.valid_mimetypes if (mimetype_guess := mimetypes.guess_type(file)[0]) is not None)]

        if len(media_files) == 0:
            raise ValueError("No files in the directory matched image or video mime types")

        return media_files

def _upload_multiple(self, paths: Iterable[str | Path], threads: Optional[int] = 1, show_progress: Optional[bool] = False, force_upload: Optional[bool] = False) -> dict[str, str]:
    """
    Upload multiple files in parallel to Google Photos.
    Args:
        paths: Iterable of file paths to upload.
        threads: Number of concurrent upload threads to use. Defaults to 1.
        show_progress: Whether to display upload progress in the console. Defaults to False.
        force_upload: Whether to upload files even if they're already present in
                      Google Photos (based on hash). Defaults to False.
    Returns:
        A dictionary mapping absolute file paths to their Google Photos media keys.
    Note:
        Failed uploads are logged as errors but don't stop the overall process.
    """
    uploaded_files = {}
    total_files = len(paths)  # Общее количество файлов
    completed_files = 0       # Количество успешно загруженных файлов

    overall_progress = self.progress.add_task(
        description=f"Overall Progress: {completed_files}/{total_files}",
        total=total_files,
        visible=show_progress
    )

    # Upload files in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {
            executor.submit(self._upload_file, file, show_progress=show_progress, force_upload=force_upload): file
            for file in paths
        }
        for future in self.progress.track(futures, task_id=overall_progress):
            file = futures[future]
            try:
                media_key_dict = future.result()
                uploaded_files.update(media_key_dict)
            except Exception as e:
                self.logger.error(f"Error uploading file {file}: {e}")
            finally:
                completed_files += 1
                # Обновляем описание задачи с текущим состоянием
                self.progress.update(
                    task_id=overall_progress,
                    description=f"Overall Progress: {completed_files}/{total_files}"
                )

    self.progress.remove_task(overall_progress)
    return uploaded_files

    def move_to_trash(self, sha1_hashes: str | bytes | Iterable[str | bytes]) -> dict:
        """
        Move remote media files to trash.

        Args:
            sha1_hashes: A single SHA-1 hash (as bytes or a hexadecimal/Base64-encoded string)
                        or an iterable of such hashes representing the files to be moved to trash.

        Returns:
            A BlackboxProtobuf Message containing the response from the API.

        Raises:
            ValueError: If the input hashes are invalid.
            requests.HTTPError: If the API request fails.
        """

        if isinstance(sha1_hashes, str | bytes):
            sha1_hashes = [sha1_hashes]

        hashes_b64 = [utils.process_sha1_hash(hash)[1] for hash in sha1_hashes]
        dedup_keys = [utils.urlsafe_base64(hash) for hash in hashes_b64]
        bearer_token = self.auth_response["Auth"]
        response = api_methods.move_remote_media_to_trash(dedup_keys=dedup_keys, auth_token=bearer_token)
        return response

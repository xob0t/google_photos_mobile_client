import time
from typing import Optional, Literal, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
import signal

import os
import mimetypes
from pathlib import Path

from rich.console import Group
from rich.live import Live
from rich.progress import (
    SpinnerColumn,
    MofNCompleteColumn,
    DownloadColumn,
    TaskProgressColumn,
    TransferSpeedColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from . import api_methods
from . import utils
from .hash_handler import HashHandler

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
        self.valid_mimetypes = ["image/", "video/"]
        self.auth_data = auth_data or os.getenv("GP_AUTH_DATA")
        self.timeout = timeout

        if not self.auth_data:
            raise ValueError("`GP_AUTH_DATA` environment variable not set. Create it or provide `auth_data` as an argument.")
        self.auth_response = api_methods.get_auth_token(self.auth_data, timeout=self.timeout)

    def _upload_file(self, file_path: str | Path, progress: Progress = None, sha1_hash: Optional[bytes | str] = None, show_progress: Optional[bool] = False, force_upload: Optional[bool] = False) -> dict[str, str]:
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

        file_progress_id = progress.add_task(description="placeholder", visible=False)
        try:
            hash_hand = HashHandler(sha1_hash=sha1_hash, file_path=file_path, progress=progress, file_progress_id=file_progress_id, show_progress=show_progress)

            if not force_upload:
                progress.update(task_id=file_progress_id, description=f"Checking: {file_path.name}", visible=show_progress)
                if remote_media_key := api_methods.find_remote_media_by_hash(hash_hand.hash_bytes, auth_token=bearer_token, timeout=self.timeout):
                    return {file_path.absolute().as_posix(): remote_media_key}

            upload_token = api_methods.get_upload_token(hash_hand.hash_b64, file_size, auth_token=bearer_token, timeout=self.timeout)
            progress.reset(task_id=file_progress_id)
            progress.update(task_id=file_progress_id, description=f"Uploading: {file_path.name}", visible=show_progress)
            with progress.open(file_path, "rb", task_id=file_progress_id) as file:
                upload_response = api_methods.upload_file(file=file, upload_token=upload_token, auth_token=bearer_token, timeout=self.timeout)
            progress.update(task_id=file_progress_id, description=f"Finalizing Upload: {file_path.name}")
            last_modified_timestamp = int(os.path.getmtime(file_path))
            media_key = api_methods.finalize_upload(
                upload_response_decoded=upload_response,
                file_name=file_path.name,
                sha1_hash=hash_hand.hash_bytes,
                auth_token=bearer_token,
                upload_timestamp=last_modified_timestamp,
                timeout=self.timeout,
            )
            return {file_path.absolute().as_posix(): media_key}
        finally:
            progress.update(file_progress_id, visible=False)

    def get_media_key_by_hash(self, sha1_hash: bytes | str) -> str | None:
        """
        Get a Google Photos media key by media's hash.

        Args:
            sha1_hash: The file's SHA-1 hash, represented as bytes, a hexadecimal string, or a Base64-encoded string.

        Returns:
            The Google Photos media key if the hash is found, otherwise None.
        """
        hash_hand = HashHandler(sha1_hash=sha1_hash)

        if int(self.auth_response["Expiry"]) <= int(time.time()):
            # get a new token if current is expired
            self.auth_response = api_methods.get_auth_token(self.auth_data, timeout=self.timeout)

        bearer_token = self.auth_response["Auth"]
        return api_methods.find_remote_media_by_hash(hash_hand.hash_bytes, auth_token=bearer_token, timeout=self.timeout)

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
        files_to_upload = [file for path in target for file in self._search_for_media_files(path, recursive=recursive)]

        if not files_to_upload:
            raise ValueError("No valid media files found to upload.")

        if len(files_to_upload) == 1:
            return self._upload_single(files_to_upload[0], sha1_hash=sha1_hash, show_progress=show_progress, force_upload=force_upload)

        return self._upload_multiple(files_to_upload, threads=threads, show_progress=show_progress, force_upload=force_upload)

    def _search_for_media_files(self, path: str | Path, recursive: Optional[bool] = False) -> list[Path]:
        """
        Search for valid media files in the specified path.

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

    def _upload_single(self, file_path: str | Path, sha1_hash: Optional[bytes | str] = None, show_progress: Optional[bool] = False, force_upload: Optional[bool] = False) -> dict[str, str]:
        """
        Upload a single file to Google Photos.

        Args:
            file_path: Path to the file to upload
            sha1_hash: The file's SHA-1 hash for skipping hash calculation
            show_progress: Whether to show progress
            force_upload: Whether to force upload even if file exists

        Returns:
            Dictionary mapping file path to media key
        """
        file_progress = Progress(
            DownloadColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TransferSpeedColumn(),
            TextColumn("{task.description}"),
        )

        with Live(file_progress):
            try:
                return self._upload_file(
                    file_path=file_path,
                    progress=file_progress,
                    sha1_hash=sha1_hash,
                    show_progress=show_progress,
                    force_upload=force_upload,
                )
            except Exception as e:
                self.logger.error(f"Error uploading file {file_path}: {e}")

    def _upload_multiple(self, paths: Iterable[str | Path], threads: Optional[int] = 1, show_progress: Optional[bool] = False, force_upload: Optional[bool] = False) -> dict[str, str]:
        """
        Upload files in parallel to Google Photos.

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
        overall_progress = Progress(
            TextColumn("[bold yellow]Files processed:"),
            SpinnerColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        )
        file_progress = Progress(
            DownloadColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TransferSpeedColumn(),
            TextColumn("{task.description}"),
        )
        progress_group = Group(
            file_progress,
            overall_progress,
        )
        overall_task_id = overall_progress.add_task("Uploading files", total=len(paths), visible=show_progress)
        with Live(progress_group, refresh_per_second=20):
            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = {executor.submit(self._upload_file, file, progress=file_progress, show_progress=show_progress, force_upload=force_upload): file for file in paths}
                for future in as_completed(futures):
                    file = futures[future]
                    try:
                        media_key_dict = future.result()
                        uploaded_files = uploaded_files | media_key_dict
                    except Exception as e:
                        self.logger.error(f"Error uploading file {file}: {e}")
                    finally:
                        overall_progress.advance(overall_task_id)
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

        hashes_b64 = [HashHandler(sha1_hash=hash).hash_b64 for hash in sha1_hashes]
        dedup_keys = [utils.urlsafe_base64(hash) for hash in hashes_b64]
        bearer_token = self.auth_response["Auth"]
        response = api_methods.move_remote_media_to_trash(dedup_keys=dedup_keys, auth_token=bearer_token)
        return response

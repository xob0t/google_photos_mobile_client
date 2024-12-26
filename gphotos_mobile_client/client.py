import time
from typing import Optional, Literal
from concurrent.futures import ThreadPoolExecutor
import signal
import hashlib
import base64
import os
import mimetypes
from pathlib import Path

from . import api_methods
from . import utils

# Make Ctrl+C work for cancelling threads
signal.signal(signal.SIGINT, signal.SIG_DFL)

DEFAULT_TIMEOUT = api_methods.DEFAULT_TIMEOUT


class GPhotosMobileClient:
    """Reverse engineered Google Photos mobile API client."""

    def __init__(self, auth_data: Optional[str] = None, timeout: Optional[int] = DEFAULT_TIMEOUT, log_level: Literal["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"] = "INFO") -> None:
        """
        Initialize the Google Photos mobile client.

        Args:
            auth_data: Google authentication data string. If not provided, will attempt to use
                      the GP_AUTH_DATA environment variable.
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
            raise ValueError("No auth_data argument provided and `GP_AUTH_DATA` environment variable not set")
        self.auth_response = api_methods.get_auth_token(self.auth_data, timeout=self.timeout)

    def _upload_file(self, file_path: str | Path, show_progress: Optional[bool] = False, force_upload: Optional[bool] = False) -> dict[str, str]:
        """
        Upload a single file to Google Photos.

        Args:
            file_path: Path to the file to upload, can be string or Path object.
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

        file_progress = self.progress.add_task(description=f"Generating Hash: {file_path.name}", visible=show_progress)

        # calculate sha1 without loading whole file in memory
        sha1 = hashlib.sha1()
        chunk_size = 4096
        with self.progress.open(file_path, "rb", task_id=file_progress) as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                sha1.update(chunk)

        sha1_hash = sha1.digest()

        sha1_hash_b64 = base64.b64encode(sha1_hash).decode("utf-8")

        if not force_upload:
            self.progress.update(task_id=file_progress, description=f"Checking: {file_path.name}")
            if remote_media_key := api_methods.find_remote_media_by_hash(sha1_hash, auth_token=bearer_token, timeout=self.timeout):
                self.progress.remove_task(file_progress)
                return {file_path.absolute().as_posix(): remote_media_key}

        upload_token = api_methods.get_upload_token(sha1_hash_b64, file_size, auth_token=bearer_token, timeout=self.timeout)
        self.progress.reset(task_id=file_progress)
        self.progress.update(task_id=file_progress, description=f"Uploading: {file_path.name}")
        with self.progress.open(file_path, "rb", task_id=file_progress) as file:
            upload_response_decoded = api_methods.upload_file(file=file, upload_token=upload_token, auth_token=bearer_token, timeout=self.timeout)
        self.progress.update(task_id=file_progress, description=f"Finalizing Upload: {file_path.name}")
        media_key = api_methods.finalize_upload(upload_response_decoded=upload_response_decoded, file_name=file_path.name, sha1_hash=sha1_hash, auth_token=bearer_token, timeout=self.timeout)
        self.progress.remove_task(file_progress)
        return {file_path.absolute().as_posix(): media_key}

    def upload(
        self,
        path: Optional[str | Path] = None,
        file_path_list: Optional[list[str | Path]] = None,
        recursive: Optional[bool] = False,
        show_progress: Optional[bool] = False,
        threads: Optional[int] = 1,
        force_upload: Optional[int] = False,
    ) -> dict[str, str]:
        """
        Upload one or more files or directories to Google Photos.

        Args:
            path: Single file or directory path to upload. If a directory, all media files
                 within it will be uploaded.
            file_path_list: List of file paths to upload. Takes precedence over `path`
                      if both are provided.
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

        Raises:
            ValueError: If neither path nor path_list is provided, or if no valid media
                       files are found in the specified locations.
        """

        # TODO maybe use functools instead of two optional args

        if file_path_list:
            return self._upload_multiple(file_path_list, threads=threads, show_progress=show_progress, force_upload=force_upload)

        if path:
            files_to_upload = self._find_media_files(path, recursive=recursive)
            if len(files_to_upload) > 1:
                return self._upload_multiple(files_to_upload, threads=threads, show_progress=show_progress, force_upload=force_upload)

            # Upload single file
            return self._upload_file(files_to_upload[0], show_progress=show_progress, force_upload=force_upload)

        raise ValueError("Must provide a `path` or `path_list` argument.")

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

    def _upload_multiple(self, paths: list[str | Path], threads: Optional[int] = 1, show_progress: Optional[bool] = False, force_upload: Optional[bool] = False) -> dict[str, str]:
        """
        Upload multiple files in parallel to Google Photos.

        Args:
            paths: List of file paths to upload.
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
        overall_progress = self.progress.add_task(description="Overall Progress", visible=show_progress)
        # Upload files in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self._upload_file, file, show_progress=show_progress, force_upload=force_upload): file for file in paths}
            for future in self.progress.track(futures, task_id=overall_progress):
                file = futures[future]
                try:
                    media_key_dict = future.result()
                    uploaded_files = uploaded_files | media_key_dict
                except Exception as e:
                    self.logger.error(f"Error uploading file {file}: {e}")
        self.progress.remove_task(overall_progress)
        return uploaded_files

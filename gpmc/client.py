import time
from typing import Literal, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
import signal
from contextlib import nullcontext
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

    def __init__(self, auth_data: str | None = None, timeout: int = DEFAULT_TIMEOUT, log_level: Literal["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"] = "INFO") -> None:
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
        self.timeout = timeout
        self.auth_data = self._handle_auth_data(auth_data)
        self.auth_response_cache: dict[str, str] = {"Expiry": "0", "Auth": ""}

    @property
    def bearer_token(self) -> str:
        """Property that automatically checks and renews the auth token if expired."""
        if int(self.auth_response_cache.get("Expiry", "0")) <= int(time.time()):
            self.auth_response_cache = api_methods.get_auth_token(self.auth_data, timeout=self.timeout)
        if token := self.auth_response_cache.get("Auth", ""):
            return token
        raise RuntimeError("Auth response does not contain bearer token")

    def _handle_auth_data(self, auth_data: str | None) -> str:
        """
        Validate and return authentication data.

        Args:
            auth_data: Authentication data string.

        Returns:
            str: Validated authentication data.

        Raises:
            ValueError: If no auth_data is provided and GP_AUTH_DATA environment variable is not set.
        """
        if auth_data is not None:
            return auth_data

        env_auth = os.getenv("GP_AUTH_DATA")
        if env_auth is not None:
            return env_auth

        raise ValueError("`GP_AUTH_DATA` environment variable not set. Create it or provide `auth_data` as an argument.")

    def _upload_file(self, file_path: str | Path, progress: Progress, force_upload: bool, use_quota: bool, saver: bool, sha1_hash: bytes | str | None = None) -> dict[str, str]:
        """
        Upload a single file to Google Photos.

        Args:
            file_path: Path to the file to upload, can be string or Path object.
            progress: Rich Progress object for tracking upload progress.
            force_upload: Whether to upload the file even if it's already present in Google Photos (based on hash).
            use_quota: Uploaded files will count against your Google Photos storage quota.
            saver: Upload files in storage saver quality.
            sha1_hash: The file's SHA-1 hash, represented as bytes, a hexadecimal string,
                                               or a Base64-encoded string. Defaults to None.

        Returns:
            dict[str, str]: A dictionary mapping the absolute file path to its Google Photos media key.
                           Example: {"/absolute/path/to/photo.jpg": "media_key_123"}

        Raises:
            FileNotFoundError: If the file does not exist.
            IOError: If there are issues reading the file.
            ValueError: If the file is empty or cannot be processed.
        """
        file_path = Path(file_path)
        file_size = file_path.stat().st_size

        file_progress_id = progress.add_task(description="")
        try:
            hash_hand = HashHandler(sha1_hash=sha1_hash, file_path=file_path, progress=progress, file_progress_id=file_progress_id)

            if not force_upload:
                progress.update(task_id=file_progress_id, description=f"Checking: {file_path.name}")
                if remote_media_key := api_methods.find_remote_media_by_hash(hash_hand.hash_bytes, auth_token=self.bearer_token, timeout=self.timeout):
                    return {file_path.absolute().as_posix(): remote_media_key}

            upload_token = api_methods.get_upload_token(hash_hand.hash_b64, file_size, auth_token=self.bearer_token, timeout=self.timeout)
            progress.reset(task_id=file_progress_id)
            progress.update(task_id=file_progress_id, description=f"Uploading: {file_path.name}")
            with progress.open(file_path, "rb", task_id=file_progress_id) as file:
                upload_response = api_methods.upload_file(file=file, upload_token=upload_token, auth_token=self.bearer_token, timeout=self.timeout)
            progress.update(task_id=file_progress_id, description=f"Finalizing Upload: {file_path.name}")
            last_modified_timestamp = int(os.path.getmtime(file_path))
            model = "Pixel XL"
            quality = "original"
            if saver:
                quality = "saver"
                model = "Pixel 2"
            if use_quota:
                model = "Pixel 8"
            media_key = api_methods.finalize_upload(
                upload_response_decoded=upload_response,
                file_name=file_path.name,
                sha1_hash=hash_hand.hash_bytes,
                auth_token=self.bearer_token,
                upload_timestamp=last_modified_timestamp,
                timeout=self.timeout,
                model=model,
                quality=quality,
            )
            return {file_path.absolute().as_posix(): media_key}
        finally:
            progress.update(file_progress_id, visible=False)

    def get_media_key_by_hash(self, sha1_hash: bytes | str) -> str | None:
        """
        Get a Google Photos media key by media's hash.

        Args:
            sha1_hash The file's SHA-1 hash, represented as bytes, a hexadecimal string,
                                     or a Base64-encoded string.

        Returns:
            str | None: The Google Photos media key if the hash is found, otherwise None.
        """
        hash_hand = HashHandler(sha1_hash=sha1_hash)
        return api_methods.find_remote_media_by_hash(hash_hand.hash_bytes, auth_token=self.bearer_token, timeout=self.timeout)

    def _handle_album_creation(self, results: dict[str, str], album_name: str, show_progress: bool) -> None:
        """
        Handle album creation based on the provided album_name.

        Args:
            results: A dictionary mapping file paths to their Google Photos media keys.
            album_name: The name of the album to create. If set to "AUTO", albums will be
                    created based on the immediate parent directory of each file.
            show_progress: Whether to display progress in the console.

        Returns:
            None
        """
        if album_name != "AUTO":
            # Add all media keys to the specified album
            media_keys = list(results.values())
            self.add_to_album(media_keys, album_name, show_progress=show_progress)
            return

        # Group media keys by the full path of their parent directory
        media_keys_by_album = {}
        for file_path, media_key in results.items():
            parent_dir = Path(file_path).parent.resolve().as_posix()
            if parent_dir not in media_keys_by_album:
                media_keys_by_album[parent_dir] = []
            media_keys_by_album[parent_dir].append(media_key)

        for parent_dir, media_keys in media_keys_by_album.items():
            album_name_from_path = Path(parent_dir).name  # Use the directory name as the album name
            self.add_to_album(media_keys, album_name_from_path, show_progress=show_progress)

    def upload(
        self,
        target: str | Path | Sequence[str | Path],
        sha1_hash: bytes | str | None = None,
        album_name: str | None = None,
        use_quota: bool = False,
        saver: bool = False,
        recursive: bool = False,
        show_progress: bool = False,
        threads: int = 1,
        force_upload: bool = False,
        delete_from_host: bool = False,
    ) -> dict[str, str]:
        """
        Upload one or more files or directories to Google Photos.

        Args:
            target: A file path, directory path, or an iterable of such paths to upload.
            sha1_hash: The file's SHA-1 hash, represented as bytes, a hexadecimal string,
                                               or a Base64-encoded string. Used to skip hash calculation.
                                               Only applies when uploading a single file. Defaults to None.
            album_name:
                If provided, the uploaded media will be added to a new album.
                If set to "AUTO", albums will be created based on the immediate parent directory of each file.

                "AUTO" Example:
                    - When uploading '/foo':
                        - '/foo/image1.jpg' will be placed in a 'foo' album.
                        - '/foo/bar/image2.jpg' will be placed in a 'bar' album.
                        - '/foo/bar/foo/image3.jpg' will be placed in a 'foo' album, distinct from the first 'foo' album.

                Defaults to None.
            use_quota: Uploaded files will count against your Google Photos storage quota. Defaults to False.
            saver: Upload files in storage saver quality. Defaults to False.
            recursive: Whether to recursively search for media files in subdirectories.
                                Only applies when uploading directories. Defaults to False.
            show_progress: Whether to display upload progress in the console. Defaults to False.
            threads: Number of concurrent upload threads for multiple files. Defaults to 1.
            force_upload: Whether to upload files even if they're already present in
                                Google Photos (based on hash). Defaults to False.
            delete_from_host: Whether to delete the file from the host after successful upload.
                                    Defaults to False.

        Returns:
            dict[str, str]: A dictionary mapping absolute file paths to their Google Photos media keys.
                            Example: {
                                "/path/to/photo1.jpg": "media_key_123",
                                "/path/to/photo2.jpg": "media_key_456"
                            }

        Raises:
            TypeError: If `target` is not a file path, directory path, or an iterable of such paths.
            ValueError: If no valid media files are found to upload.
        """
        if isinstance(target, (str, Path)):
            target = [target]

        if not isinstance(target, Sequence) or not all(isinstance(p, (str, Path)) for p in target):
            raise TypeError("`target` must be a file path, a directory path, or an iterable of such paths.")

        # Expand all paths to a flat list of files
        files_to_upload = [file for path in target for file in self._search_for_media_files(path, recursive=recursive)]

        if not files_to_upload:
            raise ValueError("No valid media files found to upload.")

        if len(files_to_upload) == 1:
            results = self._upload_single(
                files_to_upload[0],
                sha1_hash=sha1_hash,
                show_progress=show_progress,
                force_upload=force_upload,
                use_quota=use_quota,
                saver=saver,
            )
        else:
            results = self._upload_multiple(
                files_to_upload,
                threads=threads,
                show_progress=show_progress,
                force_upload=force_upload,
                use_quota=use_quota,
                saver=saver,
            )

        if album_name:
            self._handle_album_creation(results, album_name, show_progress)

        if delete_from_host:
            for file_path, _ in results.items():
                self.logger.info(f"{file_path} deleting from host")
                os.remove(file_path)
        return results

    def _search_for_media_files(self, path: str | Path, recursive: bool) -> list[Path]:
        """
        Search for valid media files in the specified path.

        Args:
            path: File or directory path to search for media files.
            recursive: Whether to search subdirectories recursively. Only applies
                             when path is a directory.

        Returns:
            list[Path]: List of Path objects pointing to valid media files.

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

    def _upload_single(self, file_path: str | Path, show_progress: bool, force_upload: bool, use_quota: bool, saver: bool, sha1_hash: bytes | str | None = None) -> dict[str, str]:
        """
        Upload a single file to Google Photos.

        Args:
            file_path: Path to the file to upload.
            show_progress: Whether to show progress.
            force_upload: Whether to force upload even if file exists.
            use_quota: Uploaded files will count against your Google Photos storage quota.
            saver: Upload files in storage saver quality.
            sha1_hash: The file's SHA-1 hash for skipping hash calculation.
                                               Defaults to None.

        Returns:
            dict[str, str]: Dictionary mapping file path to media key.
        """
        file_progress = Progress(
            DownloadColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TransferSpeedColumn(),
            TextColumn("{task.description}"),
        )

        live_context = (show_progress and Live(file_progress)) or nullcontext()

        with live_context:
            try:
                return self._upload_file(
                    file_path=file_path,
                    progress=file_progress,
                    sha1_hash=sha1_hash,
                    force_upload=force_upload,
                    use_quota=use_quota,
                    saver=saver,
                )
            except Exception:
                self.logger.exception(f"Error uploading file {file_path}")
                raise

    def _upload_multiple(self, paths: Sequence[str | Path], threads: int, show_progress: bool, force_upload: bool, use_quota: bool, saver: bool) -> dict[str, str]:
        """
        Upload files in parallel to Google Photos.

        Args:
            paths: Iterable of file paths to upload.
            threads Number of concurrent upload threads to use.
            show_progress : Whether to display upload progress in the console. Defaults to False.
            force_upload: Whether to upload files even if they're already present in
                                Google Photos (based on hash). Defaults to False.
            use_quota: Uploaded files will count against your Google Photos storage quota.
            saver: Upload files in storage saver quality.

        Returns:
            dict[str, str]: A dictionary mapping absolute file paths to their Google Photos media keys.

        Note:
            Failed uploads are logged as errors but don't stop the overall process.
        """
        uploaded_files = {}
        overall_progress = Progress(
            TextColumn("[bold yellow]Files processed:"),
            SpinnerColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TextColumn("{task.description}"),
        )
        file_progress = Progress(
            DownloadColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TransferSpeedColumn(),
            TextColumn("{task.description}"),
        )
        upload_error_count = 0
        progress_group = Group(
            file_progress,
            overall_progress,
        )

        live_context = (show_progress and Live(progress_group)) or nullcontext()

        overall_task_id = overall_progress.add_task("Errors: 0", total=len(paths), visible=show_progress)
        with live_context:
            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = {executor.submit(self._upload_file, file, progress=file_progress, force_upload=force_upload, use_quota=use_quota, saver=saver): file for file in paths}
                for future in as_completed(futures):
                    file = futures[future]
                    try:
                        media_key_dict = future.result()
                        uploaded_files = uploaded_files | media_key_dict
                    except Exception as e:
                        self.logger.error(f"Error uploading file {file}: {e}")
                        upload_error_count += 1
                        overall_progress.update(task_id=overall_task_id, description=f"[bold red] Errors: {upload_error_count}")
                    finally:
                        overall_progress.advance(overall_task_id)
        return uploaded_files

    def move_to_trash(self, sha1_hashes: str | bytes | Sequence[str | bytes]) -> dict:
        """
        Move remote media files to trash.

        Args:
            sha1_hashes: A single SHA-1 hash (as bytes or a hexadecimal/Base64-encoded string)
                        or an Sequence of such hashes representing the files to be moved to trash.

        Returns:
            dict: A BlackboxProtobuf Message containing the response from the API.

        Raises:
            ValueError: If the input hashes are invalid.
            requests.HTTPError: If the API request fails.
        """

        if isinstance(sha1_hashes, str | bytes):
            sha1_hashes = [sha1_hashes]

        hashes_b64 = [HashHandler(sha1_hash=hash).hash_b64 for hash in sha1_hashes]
        dedup_keys = [utils.urlsafe_base64(hash) for hash in hashes_b64]
        response = api_methods.move_remote_media_to_trash(dedup_keys=dedup_keys, auth_token=self.bearer_token)
        return response

    def add_to_album(self, media_keys: Sequence[str], album_name: str, show_progress: bool) -> list[str]:
        """
        Add media items to one or more albums with the given name. If the total number of items exceeds the album limit,
        additional albums with numbered suffixes are created. The first album will also have a suffix if there are multiple albums.

        Args:
            media_keys: Media keys of the media items to be added to album.
            album_name: Album name.
            show_progress : Whether to display upload progress in the console.

        Returns:
            list[str]: A list of album media keys for all created albums.

        Raises:
            requests.HTTPError: If the API request fails.
            ValueError: If media_keys is empty.
        """
        album_limit = 20000  # Maximum number of items per album
        batch_size = 500  # Number of items to process per API call
        album_keys = []
        album_counter = 1

        if len(media_keys) > album_limit:
            self.logger.warning(f"{len(media_keys)} items exceed the album limit of {album_limit}. They will be split into multiple albums.")

        # Initialize progress bar
        progress = Progress(
            TextColumn("{task.description}"),
            SpinnerColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        )
        task = progress.add_task(f"[bold yellow]Adding items to album[/bold yellow] [cyan]{album_name}[/cyan]:", total=len(media_keys))

        live_context = (show_progress and Live(progress)) or nullcontext()

        with live_context:
            for i in range(0, len(media_keys), album_limit):
                album_batch = media_keys[i : i + album_limit]
                # Add a suffix if media_keys will not fit into a single album
                current_album_name = f"{album_name} {album_counter}" if len(media_keys) > album_limit else album_name
                current_album_key = None
                for j in range(0, len(album_batch), batch_size):
                    batch = album_batch[j : j + batch_size]
                    if current_album_key is None:
                        # Create the album with the first batch
                        current_album_key = api_methods.create_new_album(album_name=current_album_name, media_keys=batch, auth_token=self.bearer_token)
                        album_keys.append(current_album_key)
                    else:
                        # Add to the existing album
                        api_methods.add_media_to_album(album_media_key=current_album_key, media_keys=batch, auth_token=self.bearer_token)
                    progress.update(task, advance=len(batch))
                album_counter += 1
        return album_keys

import time
from typing import Any, Optional
import pathlib
import hashlib
import base64
from urllib.parse import parse_qs
import requests
from rich.progress import Progress
import blackboxprotobuf

from .message_types import FINALIZE_MESSAGE_TYPE


class GPhotosMobileClient:
    """Reverse engineered Google Photos mobile API client."""

    def __init__(self, auth_data: str) -> None:
        """Initializes the GPhotosMobileClient instance.

        Args:
            auth_data (str): Android auth data for authentication.
        """
        self.auth_data = auth_data
        self.auth_response: Optional[dict] = None
        self.session = requests.Session()
        self.request_timeout = 10
        self.session.headers = {
            "Accept-Encoding": "gzip",
            "Accept-Language": "en_US",
            "User-Agent": "com.google.android.apps.photos/49029607 (Linux; U; Android 9; en_US; Pixel XL; Build/PQ2A.190205.001; Cronet/127.0.6510.5) (gzip)",
        }
        self._auth_and_update_session(self.auth_data)

    def _auth_and_update_session(self, auth_data: str) -> dict:
        """Send auth request to get bearer token and update session header."""
        auth_data_dict = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(auth_data).items()}

        request_auth_data = {
            "androidId": auth_data_dict["androidId"],
            "app": "com.google.android.apps.photos",
            "client_sig": auth_data_dict["client_sig"],
            "callerPkg": "com.google.android.apps.photos",
            "callerSig": auth_data_dict["callerSig"],
            "device_country": auth_data_dict["device_country"],
            "Email": auth_data_dict["Email"],
            "google_play_services_version": auth_data_dict["google_play_services_version"],
            "lang": auth_data_dict["lang"],
            "oauth2_foreground": auth_data_dict["oauth2_foreground"],
            "sdk_version": auth_data_dict["sdk_version"],
            "service": auth_data_dict["service"],
            "Token": auth_data_dict["Token"],
        }

        headers = {
            "Accept-Encoding": "gzip",
            "app": "com.google.android.apps.photos",
            "Connection": "Keep-Alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "device": request_auth_data["androidId"],
            "User-Agent": "GoogleAuth/1.4 (Pixel XL PQ2A.190205.001); gzip",
        }

        try:
            response = self.session.post("https://android.googleapis.com/auth", headers=headers, data=request_auth_data, timeout=self.request_timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Print the error message and the response body
            error_message = f"HTTPError: {e}, Response Body: {response.text}"
            print(error_message)
            raise

        parsed_auth_response = {}
        for line in response.text.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                parsed_auth_response[key] = value

        self.session.headers["Authorization"] = f"Bearer {parsed_auth_response['Auth']}"

        self.auth_response = parsed_auth_response

    def _get_upload_token(self, sha_hash_b64: str, file_size: int) -> str:
        """Obtain an upload token from the Google Photos API."""
        message_type = {"1": {"type": "int"}, "2": {"type": "int"}, "3": {"type": "int"}, "4": {"type": "int"}, "7": {"type": "int"}}
        proto_body = {"1": 2, "2": 1, "3": 1, "4": 3, "7": file_size}

        serialized_data = blackboxprotobuf.encode_message(proto_body, message_type)

        self.session.headers.update(
            {
                "X-Goog-Hash": f"sha1={sha_hash_b64}",
                "X-Upload-Content-Length": str(file_size),
                "Content-Type": "application/x-protobuf",
            }
        )

        try:
            response = self.session.post("https://photos.googleapis.com/data/upload/uploadmedia/interactive", data=serialized_data, timeout=self.request_timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Print the error message and the response body
            error_message = f"HTTPError: {e}, Response Body: {response.text}"
            print(error_message)
            raise
        return response.headers["X-GUploader-UploadID"]

    def _finalize_upload(self, decoded_message: dict[str, Any], file_name: str, sha1_hash: bytes) -> requests.Response:
        """Finalize the upload by sending the complete message to the API."""

        message_type = FINALIZE_MESSAGE_TYPE
        proto_body = {
            "1": {
                "1": {
                    "1": 2,
                    "2": decoded_message["2"],
                },
                "2": file_name,
                "3": sha1_hash,
                "4": {"1": int(time.time()), "2": 46000000},
                "7": 3,
                "8": {
                    "1": {
                        "1": "",
                        "3": "",
                        "4": "",
                        "5": {"1": "", "2": "", "3": "", "4": "", "5": "", "7": ""},
                        "6": "",
                        "7": {"2": ""},
                        "15": "",
                        "16": "",
                        "17": "",
                        "19": "",
                        "20": "",
                        "21": {"5": {"3": ""}, "6": ""},
                        "25": "",
                        "30": {"2": ""},
                        "31": "",
                        "32": "",
                        "33": {"1": ""},
                        "34": "",
                        "36": "",
                        "37": "",
                        "38": "",
                        "39": "",
                        "40": "",
                        "41": "",
                    },
                    "5": {
                        "2": {"2": {"3": {"2": ""}, "4": {"2": ""}}, "4": {"2": {"2": 1}}, "5": {"2": ""}, "6": 1},
                        "3": {"2": {"3": "", "4": ""}, "3": {"2": "", "3": {"2": 1}}, "4": "", "5": {"2": {"2": 1}}, "7": ""},
                        "4": {"2": {"2": ""}},
                        "5": {"1": {"2": {"3": "", "4": ""}, "3": {"2": "", "3": {"2": 1}}}, "3": 1},
                    },
                    "8": "",
                    "9": {"2": "", "3": {"1": "", "2": ""}, "4": {"1": {"3": {"1": {"1": {"5": {"1": ""}, "6": ""}, "2": "", "3": {"1": {"5": {"1": ""}, "6": ""}, "2": ""}}}, "4": {"1": {"2": ""}}}}},
                    "11": {"2": "", "3": "", "4": {"2": {"1": 1, "2": 2}}},
                    "12": "",
                    "14": {"2": "", "3": "", "4": {"2": {"1": 1, "2": 2}}},
                    "15": {"1": "", "4": ""},
                    "17": {"1": "", "4": ""},
                    "19": {"2": "", "3": "", "4": {"2": {"1": 1, "2": 2}}},
                    "22": "",
                    "23": "",
                },
                "10": 1,
                "17": 0,
            },
            "2": {"3": "Pixel XL", "4": "Google", "5": 28},  # changing this to other make and model will make uploads take up storage
            "3": bytes([1, 3]),
        }

        serialized_data = blackboxprotobuf.encode_message(proto_body, message_type)
        self.session.headers.update({"Content-Type": "application/x-protobuf", "x-goog-ext-173412678-bin": "CgcIAhClARgC", "x-goog-ext-174067345-bin": "CgIIAg=="})

        try:
            response = self.session.post("https://photosdata-pa.googleapis.com/6439526531001121323/16538846908252377752", data=serialized_data, timeout=self.request_timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Print the error message and the response body
            error_message = f"HTTPError: {e}, Response Body: {response.text}"
            print(error_message)
            raise
        return response

    def upload_file(self, file_path: str, progress: bool = False, force_upload: bool = False) -> str:
        """
        Upload a file to Google Photos.

        Args:
            file_path (str): Path to the file to upload.
            progress (bool, optional): Display upload progress. Defaults to False.
            force_upload (bool, optional): Upload the file even if it's already uploaded. Defaults to False.

        Returns:
            str: Media key of the uploaded file.
        """
        file_size = pathlib.Path(file_path).stat().st_size

        if int(self.auth_response["Expiry"]) <= int(time.time()):
            self._auth_and_update_session(self.auth_data)

        with open(file_path, "rb") as file:
            sha1_hash = hashlib.sha1(file.read()).digest()
        sha1_hash_b64 = base64.b64encode(sha1_hash).decode("utf-8")

        if not force_upload and (remote_media_key := self.find_remote_media_by_hash(sha1_hash)):
            return remote_media_key

        token = self._get_upload_token(sha1_hash_b64, file_size)

        # Upload file
        with open(file_path, "rb") as file:
            with Progress() as rich_progress:
                task = rich_progress.add_task(f"[cyan]Uploading [white]{pathlib.Path(file_path).name}", total=file_size, visible=progress)

                # Define a generator to read the file in chunks and update the progress bar
                def read_in_chunks(file_object, chunk_size=1024):
                    while chunk := file_object.read(chunk_size):
                        rich_progress.update(task, advance=len(chunk))
                        yield chunk

                try:
                    response = self.session.put(f"https://photos.googleapis.com/data/upload/uploadmedia/interactive?upload_id={token}", data=read_in_chunks(file), timeout=self.request_timeout)
                    response.raise_for_status()
                except Exception as e:
                    print(f"Upload failed: {e}")
        decoded_message, _ = blackboxprotobuf.decode_message(response.content)

        # Finalize upload
        api_response = self._finalize_upload(decoded_message, pathlib.Path(file_path).name, sha1_hash)
        decoded_message, _ = blackboxprotobuf.decode_message(api_response.content)
        media_key = decoded_message["1"]["3"]["1"]
        return media_key

    def find_remote_media_by_hash(self, sha1_hash: bytes) -> str | None:
        """
        Check library for existing files with the hash.

        Args:
            sha1_hash (bytes): SHA-1 hash of the file.

        Returns:
            str: Media key of the existing file, or None if not found.
        """
        message_type = {"1": {"field_order": ["1", "2"], "message_typedef": {"1": {"field_order": ["1"], "message_typedef": {"1": {"type": "bytes"}}, "type": "message"}, "2": {"message_typedef": {}, "type": "message"}}, "type": "message"}}
        proto_body = {"1": {"1": {"1": sha1_hash}, "2": {}}}
        serialized_data = blackboxprotobuf.encode_message(proto_body, message_type)
        self.session.headers.update({"Content-Type": "application/x-protobuf"})
        try:
            response = self.session.post("https://photosdata-pa.googleapis.com/6439526531001121323/5084965799730810217", data=serialized_data, timeout=self.request_timeout)
            response.raise_for_status()
        except Exception as e:
            print(f"Error Checking for: {e}")

        decoded_message, _ = blackboxprotobuf.decode_message(response.content)
        media_key = decoded_message["1"].get("2", {}).get("2", {}).get("1", None)
        return media_key

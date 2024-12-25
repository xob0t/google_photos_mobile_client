import argparse
from .client import GPhotosMobileClient


def main():
    parser = argparse.ArgumentParser(description="Google Photos mobile client.")
    parser.add_argument("file_path", type=str, help="Path to the file to upload.")
    parser.add_argument("auth_data", type=str, help="Google auth data for authentication.")
    parser.add_argument("--progress", action="store_true", help="Display upload progress.")
    parser.add_argument("--force-upload", action="store_true", help="Upload the file even if it is already uploaded.")

    args = parser.parse_args()

    uploader = GPhotosMobileClient(auth_data=args.auth_data)
    media_key = uploader.upload_file(file_path=args.file_path, progress=args.progress, force_upload=args.force_upload)
    print(media_key)

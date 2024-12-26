import argparse
from .client import GPhotosMobileClient


def main():
    parser = argparse.ArgumentParser(description="Google Photos mobile client.")
    parser.add_argument("path", type=str, help="Path to the file or directory to upload.")
    parser.add_argument("--auth_data", type=str, help="Google auth data for authentication. If not provided, `GP_AUTH_DATA` env variable will be used.")
    parser.add_argument("--progress", action="store_true", help="Display upload progress.")
    parser.add_argument("--recursive", action="store_true", help="Scan the directory recursively.")
    parser.add_argument("--threads", type=int, default=1, help="Number of threads to run uploads with. Defaults to 1.")
    parser.add_argument("--force-upload", action="store_true", help="Force the upload of the file even if it's already present in Google Photos (based on hash).")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level (default: INFO)")

    args = parser.parse_args()

    client = GPhotosMobileClient(auth_data=args.auth_data, log_level=args.log_level)
    output = client.upload(path=args.path, show_progress=args.progress, recursive=args.recursive, threads=args.threads, force_upload=args.force_upload)
    print(output)

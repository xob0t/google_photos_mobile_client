import unittest
import threading
from rich.progress import Progress
from gpmc import Client


class TestUpload(unittest.TestCase):
    def test_upload_with_progress(self):
        file_path = "media/image.png"

        with Progress(disable=True) as progress:
            client = Client(custom_progress=progress)
            # Start upload in a thread
            upload_thread = threading.Thread(
                target=client.upload,
                kwargs={
                    "target": file_path,
                    "show_progress": False,
                    "album_name": "FOO",
                },
            )
            upload_thread.start()

            # Monitor progress while upload is running
            while upload_thread.is_alive():
                for task in progress.tasks:
                    print(task)
                threading.Event().wait(0.1)  # Delay between updates

            upload_thread.join()


if __name__ == "__main__":
    unittest.main()

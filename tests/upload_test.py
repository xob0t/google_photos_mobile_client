import unittest

from gphotos_mobile_client import GPhotosMobileClient


class TestUpload(unittest.TestCase):
    def setUp(self):
        self.file_path = "media/image.png"
        self.client = GPhotosMobileClient()

    def test_upload(self):
        media_key = self.client.upload_file(file_path=self.file_path, force_upload=True, progress=True)
        print(media_key)


if __name__ == "__main__":
    unittest.main()

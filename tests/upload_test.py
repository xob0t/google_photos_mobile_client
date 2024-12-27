import unittest

from gphotos_mobile_client import GPhotosMobileClient


class TestUpload(unittest.TestCase):
    def setUp(self):
        self.image_file_path = "media/image.png"
        self.image_sha1_hash_b64 = "bjvmULLYvkVj8jWVQFu1Pl98hYA="
        self.mkv_file_path = "media/sample_640x360.mkv"
        self.client = GPhotosMobileClient()

    def test_image_upload(self):
        media_key = self.client.upload(target=self.image_file_path, force_upload=True, show_progress=True)
        print(media_key)

    def test_mkv_upload(self):
        media_key = self.client.upload(target=self.mkv_file_path, force_upload=True, show_progress=True)
        print(media_key)

    def test_hash_check(self):
        if media_key := self.client.check_hash(self.image_sha1_hash_b64):
            print(media_key)
        else:
            print("No remote media with matching hash found.")


if __name__ == "__main__":
    unittest.main()

import unittest

from gphotos_mobile_client import GPhotosMobileClient


class TestUpload(unittest.TestCase):
    def setUp(self):
        self.image_file_path = "media/image.png"
        self.image_sha1_hash_b64 = "bjvmULLYvkVj8jWVQFu1Pl98hYA="
        self.image_sha1_hash_hxd = "6e3be650b2d8be4563f23595405bb53e5f7c8580"
        self.mkv_file_path = "media/sample_640x360.mkv"
        self.client = GPhotosMobileClient()

    def test_image_upload(self):
        """Test image upload."""
        media_key = self.client.upload(target=self.image_file_path, force_upload=True, show_progress=True)
        print(media_key)

    def test_image_upload_with_hash(self):
        """Test media upload with known hash.
        If hash is already known, it can be passed to avoid calculating it again."""
        media_key = self.client.upload(target=self.image_file_path, sha1_hash=self.image_sha1_hash_b64, force_upload=True, show_progress=True)
        print(media_key)

    def test_mkv_upload(self):
        """Test mkv upload."""
        media_key = self.client.upload(target=self.mkv_file_path, force_upload=True, show_progress=True)
        print(media_key)

    def test_hash_check_b64(self):
        """Test hash check b64"""
        if media_key := self.client.get_media_key_by_hash(self.image_sha1_hash_b64):
            print(media_key)
        else:
            print("No remote media with matching hash found.")

    def test_hash_check_hxd(self):
        """Test hash check hxd"""
        if media_key := self.client.get_media_key_by_hash(self.image_sha1_hash_hxd):
            print(media_key)
        else:
            print("No remote media with matching hash found.")


if __name__ == "__main__":
    unittest.main()

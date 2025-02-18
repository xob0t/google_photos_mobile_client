import unittest

from gpmc import Client


class TestUpload(unittest.TestCase):
    def setUp(self):
        self.image_file_path = "media/image.png"
        self.image_sha1_hash_b64 = "bjvmULLYvkVj8jWVQFu1Pl98hYA="
        self.image_sha1_hash_hxd = "6e3be650b2d8be4563f23595405bb53e5f7c8580"
        self.directory_path = "C:/Users/admin/Pictures"
        self.mkv_file_path = "media/sample_640x360.mkv"
        self.client = Client()

    def test_add_to_album(self):
        """Test add to album."""
        response = self.client.add_to_album(
            media_keys=["AF1QipPQJJlcp_XbcSuZojLHg19NLkMiziqdjp2FS-6X", "AF1QipMvXu56uuldoyflKD60lctos9u-8BJ_luropFcZ"],
            album_name="test1",
        )
        print(response)

    def test_move_to_trash(self):
        """Test move to trash."""
        response = self.client.move_to_trash(sha1_hashes=self.image_sha1_hash_hxd)
        print(response)

    def test_image_upload(self):
        """Test image upload."""
        media_key = self.client.upload(target=self.image_file_path, force_upload=True, show_progress=True, saver=True, use_quota=True)
        print(media_key)

    def test_directory_uplod(self):
        """Test directory upload."""
        media_key = self.client.upload(target=self.directory_path, threads=5, show_progress=True)
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

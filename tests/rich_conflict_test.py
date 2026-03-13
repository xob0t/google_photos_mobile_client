import os
from gpmc import Client

@unittest.skipIf(not os.getenv("GP_AUTH_DATA"), "GP_AUTH_DATA environment variable not set")
class TestUpload(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        self.image_file_path = "media/image.png"

    def test_rich_live_no_conflict(self):
        """Test conflict"""
        with Live():
            self.client.upload(target=self.image_file_path, show_progress=False)

    def test_rich_live_conflict(self):
        """Test conflict"""
        with self.assertRaises(LiveError):
            with Live():
                self.client.upload(target=self.image_file_path, show_progress=True)


if __name__ == "__main__":
    unittest.main()

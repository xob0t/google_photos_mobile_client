import unittest
from unittest.mock import MagicMock, patch

from gpmc.client import ALBUM_BATCH_SIZE, Client


class TestAddToExistingAlbum(unittest.TestCase):
    def setUp(self):
        with patch("gpmc.client.Client._handle_auth_data", return_value="androidId=123&Email=test@gmail.com"):
            self.client = Client(auth_data="dummy")
        self.client.api = MagicMock()

    def test_batches_calls(self):
        """Media keys are split into api sized batches, all targeting the same album."""
        media_keys = [f"key_{i}" for i in range(ALBUM_BATCH_SIZE + 1)]

        album_key = self.client.add_to_existing_album(media_keys, "album_media_key")

        self.assertEqual(album_key, "album_media_key")
        self.assertEqual(self.client.api.add_media_to_album.call_count, 2)
        self.client.api.create_album.assert_not_called()

        first_call, second_call = self.client.api.add_media_to_album.call_args_list
        self.assertEqual(first_call.kwargs["album_media_key"], "album_media_key")
        self.assertEqual(len(first_call.kwargs["media_keys"]), ALBUM_BATCH_SIZE)
        self.assertEqual(len(second_call.kwargs["media_keys"]), 1)

    def test_empty_media_keys_is_a_noop(self):
        """An upload where every file failed must not hit the api."""
        album_key = self.client.add_to_existing_album([], "album_media_key")

        self.assertEqual(album_key, "album_media_key")
        self.client.api.add_media_to_album.assert_not_called()

    def test_album_name_and_album_id_are_mutually_exclusive(self):
        with self.assertRaises(ValueError):
            self.client.upload("some_path.jpg", album_name="TEST", album_id="album_media_key")


class TestAddToAlbum(unittest.TestCase):
    """`add_to_album` was refactored to share batching with `add_to_existing_album`."""

    def setUp(self):
        with patch("gpmc.client.Client._handle_auth_data", return_value="androidId=123&Email=test@gmail.com"):
            self.client = Client(auth_data="dummy")
        self.client.api = MagicMock()
        self.client.api.create_album.return_value = "new_album_key"

    def test_creates_album_with_first_batch_then_appends(self):
        media_keys = [f"key_{i}" for i in range(ALBUM_BATCH_SIZE + 10)]

        album_keys = self.client.add_to_album(media_keys, "TEST", show_progress=False)

        self.assertEqual(album_keys, ["new_album_key"])
        self.client.api.create_album.assert_called_once()
        self.assertEqual(len(self.client.api.create_album.call_args.kwargs["media_keys"]), ALBUM_BATCH_SIZE)

        self.client.api.add_media_to_album.assert_called_once()
        self.assertEqual(self.client.api.add_media_to_album.call_args.kwargs["album_media_key"], "new_album_key")
        self.assertEqual(len(self.client.api.add_media_to_album.call_args.kwargs["media_keys"]), 10)

    def test_single_batch_makes_no_append_call(self):
        album_keys = self.client.add_to_album(["key_0"], "TEST", show_progress=False)

        self.assertEqual(album_keys, ["new_album_key"])
        self.client.api.create_album.assert_called_once()
        self.client.api.add_media_to_album.assert_not_called()


if __name__ == "__main__":
    unittest.main()

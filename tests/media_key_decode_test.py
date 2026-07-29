import unittest

from blackboxprotobuf import decode_message, encode_message

from gpmc import message_types

# A real-shaped media key whose raw bytes also parse as a valid protobuf submessage.
# Without an explicit typedef blackboxprotobuf prefers the message interpretation and hands
# back a dict, which later fails in encode_message with
# `TypeError: not expecting type '<class 'dict'>'`. See issue #80.
AMBIGUOUS_MEDIA_KEY = "AF1Qipyl_A9e_Ct-lde3sq3qC9yQZUHzPXY-ek7GNpE"


def _encode(nesting: dict) -> bytes:
    """Encode `nesting` with the media key stored as raw bytes, the way the api sends it."""

    def build(node):
        if isinstance(node, dict):
            return {"type": "message", "message_typedef": {k: build(v) for k, v in node.items()}}
        return {"type": "bytes"}

    def values(node):
        return {k: (values(v) if isinstance(v, dict) else AMBIGUOUS_MEDIA_KEY.encode()) for k, v in node.items()}

    return encode_message(values(nesting), {k: build(v) for k, v in nesting.items()})  # type: ignore


class TestMediaKeyDecoding(unittest.TestCase):
    def test_key_is_ambiguous_without_a_typedef(self):
        """Guard the premise: this key really does decode as a dict when the type is inferred."""
        buf = _encode({"1": {"1": None}})
        decoded, _ = decode_message(buf)
        self.assertIsInstance(decoded["1"]["1"], dict)

    def test_create_album_response(self):
        buf = _encode({"1": {"1": None}})
        decoded, _ = decode_message(buf, message_types.CREATE_ALBUM_RESPONSE)  # type: ignore
        self.assertEqual(decoded["1"]["1"], AMBIGUOUS_MEDIA_KEY)

    def test_commit_upload_response(self):
        buf = _encode({"1": {"3": {"1": None}}})
        decoded, _ = decode_message(buf, message_types.COMMIT_UPLOAD_RESPONSE)  # type: ignore
        self.assertEqual(decoded["1"]["3"]["1"], AMBIGUOUS_MEDIA_KEY)

    def test_find_remote_media_by_hash_response(self):
        buf = _encode({"1": {"2": {"2": {"1": None}}}})
        decoded, _ = decode_message(buf, message_types.FIND_REMOTE_MEDIA_BY_HASH_RESPONSE)  # type: ignore
        self.assertEqual(decoded["1"]["2"]["2"]["1"], AMBIGUOUS_MEDIA_KEY)

    def test_unrelated_fields_still_decode(self):
        """The typedefs are partial: fields they don't declare must still come through."""
        typedef = {
            "1": {"type": "message", "message_typedef": {"1": {"type": "bytes"}, "2": {"type": "int"}}},
            "9": {"type": "int"},
        }
        buf = encode_message({"1": {"1": AMBIGUOUS_MEDIA_KEY.encode(), "2": 7}, "9": 42}, typedef)  # type: ignore
        decoded, _ = decode_message(buf, message_types.CREATE_ALBUM_RESPONSE)  # type: ignore
        self.assertEqual(decoded["1"]["1"], AMBIGUOUS_MEDIA_KEY)
        self.assertEqual(decoded["1"]["2"], 7)
        self.assertEqual(decoded["9"], 42)


if __name__ == "__main__":
    unittest.main()

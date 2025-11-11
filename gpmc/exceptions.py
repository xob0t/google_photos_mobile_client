class CustomException(Exception):
    pass


class UploadRejected(CustomException):
    pass


class ProtobufDecodeError(CustomException):
    """Raised when protobuf message decoding fails."""
    pass


class ProtobufEncodeError(CustomException):
    """Raised when protobuf message encoding fails."""
    pass

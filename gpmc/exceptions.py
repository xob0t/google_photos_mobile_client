class CustomError(Exception):
    pass


class UploadRejectedError(CustomError):
    pass


class AuthenticationError(CustomError):
    """Google authentication failed or returned an unusable credential."""


class BrowserAuthenticationRequiredError(AuthenticationError):
    """Google requires a fresh Embedded Setup sign-in."""


class SyncCycleError(CustomError):
    """Raised when sync token doesn't change between iterations, indicating an infinite sync loop."""

    pass

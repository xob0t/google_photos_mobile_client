"""Google Embedded Setup sign-in, ported from gotohp/backend/googleauth.go."""

import secrets
from email.utils import parseaddr
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter, Retry

from .exceptions import AuthenticationError, BrowserAuthenticationRequiredError

EMBEDDED_SETUP_URL = "https://accounts.google.com/EmbeddedSetup"
PHOTOS_PACKAGE = "com.google.android.apps.photos"
PHOTOS_SIGNATURE = "24bb24c05e47e0aefa68a58a766179d9b613a600"
GMS_SIGNATURE = "38918a453d07199354f8b19af05ec6562ced5788"
PHOTOS_SERVICE = "oauth2:openid https://www.googleapis.com/auth/mobileapps.native https://www.googleapis.com/auth/photos.native"


def new_auth_session(proxy: str = "") -> requests.Session:
    """Keep certificate verification enabled for authentication, including proxies."""
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504]))
    session.mount("https://", adapter)
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})
    return session


def parse_auth_response(response: requests.Response) -> dict[str, str]:
    values = dict(line.strip().split("=", 1) for line in response.text.splitlines() if "=" in line)
    code = values.get("Error")
    if code == "NeedsBrowser":
        raise BrowserAuthenticationRequiredError(f"Google requires a fresh browser sign-in at {EMBEDDED_SETUP_URL}.")
    if code == "BadAuthentication":
        raise AuthenticationError("Google rejected the credential. Obtain a fresh oauth_token cookie or export new GMSCore auth data.")
    if code == "MissingDroidguard":
        raise AuthenticationError("Google rejected the device verification data.")
    # Do not include response bodies or redirect URLs, which can contain tokens.
    if not 200 <= response.status_code < 300:
        raise AuthenticationError(f"Google authentication returned HTTP {response.status_code}")
    if code:
        raise AuthenticationError("Google authentication failed.")
    return values


def authenticate(oauth_token: str, proxy: str = "", timeout: int = 60) -> str:
    """Exchange an Embedded Setup cookie and return validated, reusable auth data.

    Sign in at https://accounts.google.com/EmbeddedSetup, click I agree, then
    copy the oauth_token cookie from your browser's developer tools. The cookie
    can be supplied as its value or as ``oauth_token=value``.
    """
    token = oauth_token.strip().removeprefix("oauth_token=")
    if not 16 <= len(token) <= 8192 or any(c in token for c in "\r\n"):
        raise ValueError("Enter the oauth_token cookie value from Google Embedded Setup.")
    android_id = secrets.token_hex(8)
    form = {
        "accountType": "HOSTED_OR_GOOGLE",
        "Email": "oauth-token@example.com",
        "has_permission": "1",
        "add_account": "1",
        "ACCESS_TOKEN": "1",
        "Token": token,
        "service": "ac2dm",
        "source": "android",
        "androidId": android_id,
        "device_country": "us",
        "operatorCountry": "us",
        "lang": "en",
        "sdk_version": "17",
        "google_play_services_version": "240913000",
        "client_sig": GMS_SIGNATURE,
        "callerSig": GMS_SIGNATURE,
        "droidguard_results": "dummy123",
    }
    with new_auth_session(proxy) as session:
        response = session.post(
            "https://android.clients.google.com/auth",
            data=form,
            headers={"Accept-Encoding": "identity", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "GoogleAuth/1.4"},
            timeout=timeout,
            allow_redirects=False,
        )
    values = parse_auth_response(response)
    if not values.get("Token"):
        raise AuthenticationError("Google authentication response did not contain a master token.")
    email = values.get("Email", "").strip()
    if not email or "@" not in email or parseaddr(email)[1] != email or any(c.isspace() for c in email):
        raise AuthenticationError("Google authentication response did not contain a valid account email.")
    credential = urlencode({
        "androidId": android_id,
        "app": PHOTOS_PACKAGE,
        "callerPkg": PHOTOS_PACKAGE,
        "client_sig": PHOTOS_SIGNATURE,
        "callerSig": PHOTOS_SIGNATURE,
        "device_country": "us",
        "Email": email,
        "google_play_services_version": "240913000",
        "lang": "en_US",
        "oauth2_foreground": "1",
        "operatorCountry": "us",
        "sdk_version": "33",
        "service": PHOTOS_SERVICE,
        "source": "android",
        "Token": values["Token"],
    })
    return credential


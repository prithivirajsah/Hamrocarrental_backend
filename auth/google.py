import json
import os
import urllib.parse
import urllib.request


def verify_google_id_token(id_token: str) -> dict:
    """
    Verifies Google ID token via Google's tokeninfo endpoint.
    Returns decoded payload when valid, otherwise raises ValueError.
    """
    if not id_token:
        raise ValueError("Google ID token is required")

    url = "https://oauth2.googleapis.com/tokeninfo?" + urllib.parse.urlencode(
        {"id_token": id_token}
    )

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise ValueError("Failed to verify Google token") from exc

    if payload.get("error_description") or payload.get("error"):
        raise ValueError("Invalid Google token")

    # Optional hard check when configured.
    expected_client_id = os.getenv("GOOGLE_CLIENT_ID")
    token_aud = payload.get("aud")
    if expected_client_id and token_aud != expected_client_id:
        raise ValueError("Google token audience mismatch")

    if not payload.get("email"):
        raise ValueError("Google token does not include email")

    return payload

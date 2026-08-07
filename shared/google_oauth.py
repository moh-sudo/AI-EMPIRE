"""Shared Google OAuth credentials helper -- used by both
shared/gmail/client.py and shared/calendar/client.py, since they're
both built on the same Google Cloud project/OAuth client/refresh token
(one combined token covering gmail.readonly + calendar.readonly,
obtained via agents/personal/gmail_oauth_setup.py's one-time consent
flow). Not a division-separation violation -- Gmail/Calendar aren't
separate AI_EMPIRE divisions, just two pieces of the same underlying
Google integration.
"""

import os


def get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_OAUTH_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return creds


def check_required_env() -> list[str]:
    required = ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "GOOGLE_OAUTH_REFRESH_TOKEN"]
    return [k for k in required if not os.environ.get(k)]

"""One-time script to obtain a Google API refresh token (Gmail +
Calendar) via the OAuth Desktop app flow. Run manually, once -- not
part of the ongoing Morning Brief pipeline. Opens a real browser
window for Mohamed to log in and consent; on success, prints the
refresh token to store in .env as GOOGLE_OAUTH_REFRESH_TOKEN.

Re-run 2026-08-02 to add Calendar on top of the original Gmail-only
token (2026-08-02 first run) -- one combined refresh token covering
both scopes, simpler than managing two separate tokens for the same
Google Cloud project/OAuth client. Both scopes are deliberately
read-only (gmail.readonly, calendar.readonly) -- least privilege, this
integration only ever reads, never sends/modifies/creates anything.
"""

import os

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def main() -> None:
    client_id = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
    client_secret = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n--- SUCCESS ---")
    print("Add this line to .env:")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()

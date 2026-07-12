"""One-time interactive helper to obtain a Google Calendar OAuth refresh token for the
Calendar rail (src/personalos/rails/calendar.py).

Run this yourself, in your own terminal:

    python3 scripts/calendar_oauth_setup.py

It never sends anything anywhere except directly to Google's own OAuth endpoints
(oauth2.googleapis.com), and it never contacts any Claude/Anthropic service, any
other part of this codebase, or anywhere else. Nothing you type here is written to
disk by this script or logged anywhere -- the resulting refresh token is printed once,
to your terminal, for you to copy into your own environment yourself.

Prerequisites (do this first, in the Google Cloud Console, https://console.cloud.google.com/):
  1. Create or select a project.
  2. APIs & Services -> Library -> enable "Google Calendar API".
  3. APIs & Services -> OAuth consent screen -> configure it (External is fine;
     "Testing" publish status is fine for personal use -- add your own Google account
     as a test user under "Test users").
  4. APIs & Services -> Credentials -> Create Credentials -> OAuth client ID ->
     Application type: "Desktop app". Note the Client ID and Client Secret it gives you.

This script will then walk you through the rest.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"  # "Desktop app" client type's manual-copy flow
SCOPE = "https://www.googleapis.com/auth/calendar.events"  # narrowest scope that can create events


def main() -> None:
    print(__doc__)
    print("-" * 72)
    client_id = input("Paste your OAuth Client ID: ").strip()
    client_secret = input("Paste your OAuth Client Secret: ").strip()

    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",   # required to receive a refresh_token at all
        "prompt": "consent",        # forces a refresh_token even if you've consented before
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    print("\nOpen this URL in your browser, sign in, and approve access:\n")
    print(auth_url)
    print(
        "\nGoogle will show you a page with an authorization code (it will NOT redirect "
        "anywhere real -- that's expected for a Desktop app client). Copy that code."
    )
    auth_code = input("\nPaste the authorization code here: ").strip()

    token_body = urllib.parse.urlencode({
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=token_body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"\nToken exchange failed: HTTP {e.code}: {e.read().decode()}")
        print("Common cause: the authorization code was already used, or expired (they're "
              "single-use and short-lived) -- rerun this script to get a fresh one.")
        raise SystemExit(1)

    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        print(
            "\nNo refresh_token in the response. This usually means you'd already granted "
            "consent before without 'prompt=consent' forcing a new one. In Google Account "
            "settings -> Security -> Third-party access, remove this app's access, then "
            "rerun this script from the top."
        )
        raise SystemExit(1)

    print("\n" + "=" * 72)
    print("Success. Set these four environment variables in your own shell profile or")
    print("wherever personalos reads its environment from (never commit them):\n")
    print(f"export PERSONALOS_RAIL_CALENDAR_CLIENT_ID='{client_id}'")
    print(f"export PERSONALOS_RAIL_CALENDAR_CLIENT_SECRET='{client_secret}'")
    print(f"export PERSONALOS_RAIL_CALENDAR_REFRESH_TOKEN='{refresh_token}'")
    print("export PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID='<see below>'")
    print("=" * 72)
    print(
        "\nFor the controlled calendar ID: usually 'primary' for your main calendar, or "
        "find a specific calendar's ID under Google Calendar -> Settings -> [that "
        "calendar] -> 'Integrate calendar' -> Calendar ID."
    )


if __name__ == "__main__":
    main()

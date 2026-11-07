"""
Run this ONCE, locally, on your own laptop — not in GitHub Actions.

It opens a browser so you can sign in to the Google account that owns
your YouTube channel, then prints a refresh token. Paste that refresh
token into the YT_REFRESH_TOKEN GitHub Secret, alongside YT_CLIENT_ID
and YT_CLIENT_SECRET from the same OAuth client. After that, the
GitHub Actions upload workflow can authenticate without ever opening a
browser again.

Prerequisites (see SETUP_GUIDE.md for the click-by-click version):
  1. pip install google-auth-oauthlib google-api-python-client
  2. A Google Cloud project with "YouTube Data API v3" enabled.
  3. An OAuth 2.0 Client ID of type "Desktop app", downloaded as JSON.

Usage:
  python scripts/get_youtube_token.py path/to/client_secret.json
"""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/get_youtube_token.py path/to/client_secret.json")
        sys.exit(1)

    client_secret_path = sys.argv[1]
    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    # Opens your default browser for a one-time sign-in + consent screen.
    credentials = flow.run_local_server(port=0)

    print("\n=== Success! Copy these into your GitHub repo's Secrets ===\n")
    print(f"YT_CLIENT_ID      = {credentials.client_id}")
    print(f"YT_CLIENT_SECRET  = {credentials.client_secret}")
    print(f"YT_REFRESH_TOKEN  = {credentials.refresh_token}")
    print(
        "\nIf YT_REFRESH_TOKEN is blank, Google only issues a refresh token "
        "the FIRST time an app is authorized. Go to "
        "https://myaccount.google.com/permissions, remove access for this "
        "app, then run this script again.\n"
    )


if __name__ == "__main__":
    main()

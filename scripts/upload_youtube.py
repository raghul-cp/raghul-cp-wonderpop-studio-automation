"""
Uploads output/final_short.mp4 to YouTube using the stored OAuth refresh
token — no browser, no interactive login. Only ever runs from the
"Upload Short to YouTube" workflow, which is manual (workflow_dispatch),
so nothing is ever uploaded without a human deliberately triggering it.

IMPORTANT — read this before you expect a public video:
Google restricts videos uploaded via the videos.insert endpoint from
*unaudited* API projects to Private, permanently, regardless of the
privacyStatus you send — this is a Google policy, not a bug here. See
SETUP_GUIDE.md for both ways to get your finished video public:
  (a) request Google's free YouTube API Audit, or
  (b) just upload the finished output/final_short.mp4 yourself through
      the normal YouTube Studio / app, pasting in the generated title,
      description and tags from output/metadata.json.
Either way, this script always sets privacyStatus="private" on purpose —
that private upload IS your review step: watch it in YouTube Studio,
then decide whether to publish it.

Required secrets (see SETUP_GUIDE.md):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from common import FINAL_VIDEO, METADATA_JSON, load_channel_config, read_json, log, fail

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def get_credentials() -> Credentials:
    client_id = os.environ.get("YT_CLIENT_ID")
    client_secret = os.environ.get("YT_CLIENT_SECRET")
    refresh_token = os.environ.get("YT_REFRESH_TOKEN")
    if not all([client_id, client_secret, refresh_token]):
        fail("YT_CLIENT_ID, YT_CLIENT_SECRET and YT_REFRESH_TOKEN must all be set as secrets.")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def main():
    if not FINAL_VIDEO.exists():
        fail(f"{FINAL_VIDEO} not found. Run the generate workflow first and download its artifact.")

    channel = load_channel_config()
    metadata = read_json(METADATA_JSON)
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": metadata["title"][:100],
            "description": metadata["description"],
            "tags": metadata.get("tags", []),
            "categoryId": channel.get("category_id", "1"),
            "defaultLanguage": channel.get("default_language", "en"),
        },
        "status": {
            "privacyStatus": "private",   # always — see module docstring
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(FINAL_VIDEO), chunksize=-1, resumable=True, mimetype="video/mp4")
    log(f"Uploading {FINAL_VIDEO} as PRIVATE to YouTube...")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log(f"Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    log(f"Done. Video ID: {video_id}")
    log(f"Review it privately here: https://studio.youtube.com/video/{video_id}/edit")


if __name__ == "__main__":
    main()

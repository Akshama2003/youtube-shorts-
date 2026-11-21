"""Publisher: uploads the approved video to YouTube through the official Data API (OAuth)."""
from pathlib import Path

from ..config import ROOT, S
from ..util import log

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET = ROOT / "client_secret.json"
TOKEN = ROOT / "token.json"
CATEGORY_EDUCATION = "27"


def get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET.exists():
                raise RuntimeError(
                    "client_secret.json not found in the project folder. See README -> 'YouTube API setup'."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def authorize() -> None:
    get_service()
    log("Publisher", "YouTube authorization OK (token.json saved).")


def upload(video_path: str, seo: dict) -> dict:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    yt = get_service()
    body = {
        "snippet": {
            "title": seo["title"],
            "description": seo["description"],
            "tags": seo["tags"],
            "categoryId": CATEGORY_EDUCATION,
            "defaultLanguage": S.language,
            "defaultAudioLanguage": S.language,
        },
        "status": {
            "privacyStatus": S.privacy,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": S.disclose_ai,
        },
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", chunksize=-1, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    try:
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
    except HttpError as e:
        raise RuntimeError(f"YouTube upload failed: {e}") from e
    vid = resp["id"]
    url = f"https://youtube.com/shorts/{vid}"
    log("Publisher", f"Uploaded ({S.privacy}): {url}")
    return {"video_id": vid, "url": url, "privacy": S.privacy}

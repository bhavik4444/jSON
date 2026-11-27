"""Run ONCE (and again the day before the demo) to log into Google and create token.json.

Needs credentials.json (OAuth client of type 'Desktop app') in this folder.
"""
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

BASE = Path(__file__).parent
SCOPES = ["https://www.googleapis.com/auth/calendar"]

flow = InstalledAppFlow.from_client_secrets_file(str(BASE / "credentials.json"), SCOPES)
creds = flow.run_local_server(port=0, prompt="consent")
(BASE / "token.json").write_text(creds.to_json())
print("Done. token.json saved. You can now run: python host.py")
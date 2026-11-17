#!/usr/bin/env python3
"""Optional: einmaliger Google-Browserlogin auf dem eigenen PC, niemals in Actions."""
import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from sync import SCOPES

if __name__ == "__main__":
    os.umask(0o077)
    try:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        if not creds.refresh_token:
            raise ValueError("Refresh-Token fehlt")
        info = json.loads(creds.to_json())
        info["type"] = "authorized_user"
        Path("token.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
        print("token.json gespeichert. Inhalt ausschließlich als GitHub Secret GOOGLE_CREDENTIALS_JSON eintragen.")
    except Exception:
        print("Google-Autorisierung fehlgeschlagen. Desktop-OAuth-Client, Zustimmungsstatus und Testnutzer prüfen.")
        raise SystemExit(1)

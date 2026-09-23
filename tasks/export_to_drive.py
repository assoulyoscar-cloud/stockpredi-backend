"""Export stats vers Google Drive (cron hebdo)."""
import os
import json
import logging
from datetime import datetime, timezone
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests

logger = logging.getLogger("stockpredi.gdrive")

# Config Google Drive
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
BACKEND_URL = os.getenv("BACKEND_URL", "https://stockpredi-backend.onrender.com")
BACKEND_AUTH_TOKEN = os.getenv("BACKEND_AUTH_TOKEN", "")  # Service token


def export_stats_to_drive():
    """Fetch stats from backend + upload to Google Drive."""
    
    if not GOOGLE_DRIVE_FOLDER_ID or not GOOGLE_SERVICE_ACCOUNT_JSON:
        logger.error("Google Drive config manquante")
        return False
    
    try:
        # 1. Fetch stats from notre API
        headers = {"Authorization": f"Bearer {BACKEND_AUTH_TOKEN}"}
        res = requests.get(f"{BACKEND_URL}/api/stats/export", headers=headers, timeout=10)
        if res.status_code != 200:
            logger.error("Stats fetch failed: %s", res.status_code)
            return False
        
        stats = res.json()
        now = datetime.now(timezone.utc)
        
        # 2. Setup Google Drive API
        creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = Credentials.from_service_account_info(creds_dict)
        drive = build("drive", "v3", credentials=creds)
        
        # 3. Créer JSON local
        filename = f"stats_{now.strftime('%Y-%m-%d_%H%M%S')}.json"
        with open(f"/tmp/{filename}", "w") as f:
            json.dump(stats, f, indent=2)
        
        # 4. Upload vers Google Drive
        media = MediaFileUpload(f"/tmp/{filename}", mimetype="application/json")
        file_metadata = {
            "name": filename,
            "parents": [GOOGLE_DRIVE_FOLDER_ID],
            "mimeType": "application/json"
        }
        file = drive.files().create(body=file_metadata, media_body=media, fields="id").execute()
        logger.info("Stats uploaded to Drive: %s (%s)", filename, file.get("id"))
        
        # 5. Créer/update cumul mensuel
        month_filename = f"stats_{now.strftime('%Y-%m')}.json"
        monthly_file = drive.files().list(
            q=f"name='{month_filename}' and '{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed=false",
            spaces="drive", fields="files(id, name)", pageSize=1
        ).execute()
        
        if monthly_file.get("files"):
            # Update existing
            file_id = monthly_file["files"][0]["id"]
            drive.files().update(body=file_metadata, fileId=file_id, media_body=media).execute()
            logger.info("Stats monthly updated: %s", month_filename)
        else:
            # Create new
            drive.files().create(body=file_metadata, media_body=media, fields="id").execute()
            logger.info("Stats monthly created: %s", month_filename)
        
        return True
    
    except Exception as e:
        logger.error("Export to Drive failed: %s", str(e))
        return False


# Pour tester: python -c "from tasks.export_to_drive import export_stats_to_drive; export_stats_to_drive()"
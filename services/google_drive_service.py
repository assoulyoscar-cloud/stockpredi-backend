"""
Google Drive Service - Archive automatique des fichiers clients
"""
import os
import json
import base64
from io import BytesIO
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload


class GoogleDriveService:
    """Service pour uploader les fichiers sur Google Drive"""

    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self, service_account_json_str: str, folder_id: str):
        """
        Initialise le service Google Drive

        Args:
            service_account_json_str: Contenu du fichier JSON de la Service Account
            folder_id: ID du dossier Google Drive où uploader les fichiers
        """
        try:
            # Parse le JSON de la Service Account
            service_account_info = json.loads(service_account_json_str)

            # Crée les credentials
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=self.SCOPES
            )

            # Crée le service Drive
            self.service = build('drive', 'v3', credentials=self.credentials)
            self.folder_id = folder_id

        except Exception as e:
            raise Exception(f"Erreur initialisation Google Drive: {str(e)}")

    def upload_pdf(self, pdf_bytes: bytes, filename: str) -> dict:
        """
        Upload un fichier PDF sur Google Drive

        Args:
            pdf_bytes: Contenu du PDF en bytes
            filename: Nom du fichier (ex: "oscar_assouly_20260830.pdf")

        Returns:
            Dict avec file_id et file_url
        """
        try:
            # Crée un fichier avec le PDF en bytes
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }

            # Upload le fichier
            media = MediaIoBaseUpload(
                BytesIO(pdf_bytes),
                mimetype='application/pdf',
                resumable=True
            )

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            return {
                'success': True,
                'file_id': file.get('id'),
                'file_url': file.get('webViewLink'),
                'filename': filename
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"Erreur upload Google Drive: {str(e)}"
            }

    def list_files(self, max_results=10) -> list:
        """Liste les fichiers du dossier"""
        try:
            results = self.service.files().list(
                q=f"'{self.folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='files(id, name, createdTime)',
                pageSize=max_results
            ).execute()

            return results.get('files', [])

        except Exception as e:
            return []


def get_google_drive_service():
    """Crée une instance du service Google Drive avec les env vars"""
    try:
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

        if not service_account_json or not folder_id:
            return None

        return GoogleDriveService(service_account_json, folder_id)
    except Exception as e:
        print(f"Erreur création Google Drive Service: {str(e)}")
        return None

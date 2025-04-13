from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
from django.conf import settings
import mimetypes

# The folder ID where we want to upload files
DRIVE_FOLDER_ID = '1GJeeAdKQZt5KCpDjt0lAOL6rEVlTse8D'


def get_drive_service():
    """
    Creates and returns a Google Drive service object
    Requires a service account credentials file at settings.GOOGLE_DRIVE_CREDENTIALS_FILE
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_DRIVE_CREDENTIALS_FILE,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        print(f"Error creating Google Drive service: {str(e)}")
        return None


def upload_file_to_drive(file_path, file_name):
    """
    Uploads a file to Google Drive and returns the file ID and viewable link

    Parameters:
    file_path (str): The full path to the file
    file_name (str): The name to give the file in Google Drive

    Returns:
    tuple: (file_id, web_view_link) or (None, None) if upload fails
    """
    try:
        service = get_drive_service()
        if not service:
            return None

        # Determine the MIME type of the file
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'  # Default MIME type

        file_metadata = {
            'name': file_name,
            'parents': [DRIVE_FOLDER_ID]
        }

        media = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            resumable=True
        )

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        # Create a shared link that anyone can view
        service.permissions().create(
            fileId=file.get('id'),
            body={
                'type': 'anyone',
                'role': 'reader'
            }
        ).execute()

        # Get the updated file with the web view link
        file = service.files().get(
            fileId=file.get('id'),
            fields='webViewLink'
        ).execute()
        return file.get('webViewLink')
    except Exception as e:
        print(f"Error uploading file to Google Drive: {str(e)}")
        return None

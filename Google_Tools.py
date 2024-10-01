from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
import io

import os

# SCOPES should include the required permissions for your app.
SCOPES = ['https://www.googleapis.com/auth/drive']

def google_drive_auth(username):
    # Create the flow using the client_secrets.json file.
    flow = Flow.from_client_secrets_file(
        '/tmp/google_drive_client_secret.json',
        scopes=SCOPES,
        redirect_uri=f'https://adma.hopto.org/api/google_drive_auth_callback/'
    )

    # Get the authorization URL.
    auth_url, _ = flow.authorization_url(prompt='consent',state = f"username={username}")

    # Redirect the user to the Google OAuth2 authorization page.
    return auth_url

def google_drive_generate_credentials(redirect_url,username):
    credential_file = f"/tmp/google_drive_credential_{username}.json"
    while not os.path.exists(credential_file):
        pass

    credentials = Credentials.from_authorized_user_file(credential_file, SCOPES)

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    return credential_file



def google_drive_list(credential_file):
    # Load the credentials from the session.
    if not os.path.exists(credential_file):
        return []
    credentials = Credentials.from_authorized_user_file(credential_file,SCOPES)



    # Create a service object using the credentials.
    service = build('drive', 'v3', credentials=credentials)

    # Call the Drive v3 API.
    #results = service.files().list(q="'root' in parents",pageSize=100, fields="nextPageToken, files(id, name,size,webViewLink,modifiedTime, createdTime, mimeType)").execute()
    results = service.files().list(q="'root' in parents",pageSize=100, fields="nextPageToken, files(name,webViewLink,modifiedTime, createdTime)").execute()
    items = results.get('files', [])

    return items

def google_drive_download_file(credential_file, file_path):
    file_name = os.path.basename(file_path)
    destination = f"tmp/{file_name}"
    if not os.path.exists(credential_file):
        return ""

    # Load the credentials from the session.
    credentials = Credentials.from_authorized_user_file(credential_file, SCOPES)


    



    # Create a service object using the credentials.
    service = build('drive', 'v3', credentials=credentials)

    # Search for the file by path
    file = google_drive_find_file_by_path(credential_file, file_path)
    mime_type_of_file = file['mimeType']
    file_id = file['id']
    #print(f"Downloading file: {file_path}")
    if mime_type_of_file.startswith('application/vnd.google-apps'):
        
        # Set default export mime type based on Google file type
        mime_type_of_file = {
            'application/vnd.google-apps.document': 'application/pdf',  # Google Docs -> PDF
            'application/vnd.google-apps.spreadsheet': 'text/csv',  # Google Sheets -> CSV
            'application/vnd.google-apps.presentation': 'application/pdf',  # Google Slides -> PDF
        }.get(mime_type_of_file, 'application/pdf')  # Default to PDF if unknown
        suffix = mime_type_of_file.split('/')[1]
        destination = f"tmp/{file_name}.{suffix}"

    request = service.files().export_media(fileId=file_id, mimeType=mime_type_of_file)

    

    if file == None:
        return ""

    


    # Create a file object to write the file to.
    fh = io.FileIO(destination, 'wb')

    # Download the file in chunks.
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        #print(f"Download {int(status.progress() * 100)}%.")  # Print download progress
    return destination



def google_drive_find_file_by_path(credential_file, file_path):
    # Load the credentials.
    credentials = Credentials.from_authorized_user_file(credential_file, SCOPES)



    # Create a service object using the credentials.
    service = build('drive', 'v3', credentials=credentials)

    # Split the path into folder and file components.
    path_parts = file_path.split("/")
    
    # Start from the root folder (Google Drive's root ID is 'root')
    parent_id = 'root'

    # Traverse the folder path
    for part in path_parts[:-1]:  # Traverse folders, excluding the file
        query = f"name = '{part}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        
        if not items:
            print(f"Folder '{part}' not found in path.")
            return None  # Stop if folder not found
        
        # Move to the next folder (use the first result if multiple matches)
        parent_id = items[0]['id']
    
    # Now search for the final file in the last folder.
    file_name = path_parts[-1]
    query = f"name = '{file_name}' and '{parent_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name, webViewLink, mimeType)").execute()
    items = results.get('files', [])

    if not items:
        print(f"File '{file_name}' not found in path.")
        return None

    # Return file metadata (such as file ID and webViewLink)
    file = items[0]
    print(f"Found file: {file['name']} (ID: {file['id']})")
    return file
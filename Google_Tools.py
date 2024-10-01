from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import os

# SCOPES should include the required permissions for your app.
SCOPES = ['https://www.googleapis.com/auth/drive']

def google_drive_auth():
    # Create the flow using the client_secrets.json file.
    flow = Flow.from_client_secrets_file(
        '/tmp/google_drive_client_secret.json',
        scopes=SCOPES,
        redirect_uri='https://adma.hopto.org/api/google_drive_auth_callback/'
    )

    # Get the authorization URL.
    auth_url, _ = flow.authorization_url(prompt='consent')

    # Redirect the user to the Google OAuth2 authorization page.
    return auth_url

def google_drive_generate_credentials(redirect_url):
    credential_file = "/tmp/google_drive_credential.json"
    while not os.path.exists(credential_file):
        pass

    return credential_file



def google_drive_list(credential_file):
    # Load the credentials from the session.
    credentials = Credentials.from_authorized_user_file(credential_file,SCOPES)

    # Create a service object using the credentials.
    service = build('drive', 'v3', credentials=credentials)

    # Call the Drive v3 API.
    results = service.files().list(q="'root' in parents",pageSize=100, fields="nextPageToken, files(id, name,size,webViewLink,modifiedTime, createdTime, mimeType)").execute()
    items = results.get('files', [])

    return items
import asyncio
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/documents"]

async def create_google_doc(title):
    """Create google doc and return document_id"""
    def _create_doc():
        try:
          service = create_docs_service()       # create service in this thread
          doc_body = {'title': title}
          doc = service.documents().create(body=doc_body).execute()
          document_id = doc.get('documentId')
          print(f"Created document with title '{doc.get('title')}' and ID: {document_id}")
          return document_id
        except:
           return ""

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _create_doc)
    

async def update_google_doc(document_id, body_text):
    """Update google doc with document_id with body_text"""
    def _update_doc():
        try:
            service = create_docs_service() 
            requests = [
                {
                    'insertText': {
                        'location': {'index': 1},
                        'text': body_text
                    }
                }
            ]
            service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            print(f"Successfully inserted text into document: {document_id}")
        except Exception as e:
            print(f"Error occurred: {e}")

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _update_doc)


def create_docs_service():
  """Create and return doc service"""
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token_docs.json"):
    creds = Credentials.from_authorized_user_file("token_docs.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token_docs.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("docs", "v1", credentials=creds)
    return service
  except HttpError as err:
    print(err)


if __name__ == "__main__":
  create_docs_service()
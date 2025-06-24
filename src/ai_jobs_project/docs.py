import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/documents"]

# The ID of a sample document.
DOCUMENT_ID = "195j9eDD3ccgjQRttHhJPymLJUCOUjs-jmwTrekvdjFE"

TEST_DOC = """This is a test"""


def create_google_doc(service, title: str) -> str | None:
    """
    Creates a new Google Doc with a title.

    Args:
        service: The authenticated Google Docs API service object.
        title: The title of the new Google Doc.

    Returns:
        The ID of the newly created document, or None if an error occurred.
    """
    try:
        # 1. Create a new document with the specified title
        doc_body = {
            'title': title
        }
        doc = service.documents().create(body=doc_body).execute()
        document_id = doc.get('documentId')
        print(f"Created document with title '{doc.get('title')}' and ID: {document_id}")
        return document_id

    except HttpError as err:
        print(f"An error occurred: {err}")
        return None
    

def update_google_doc(service, document_id, body_text):
        try:
              # 2. Insert the raw text into the document at the beginning
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': 1,  # Insert at the beginning of the document body
                        },
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
  


def create_docs_service():
  """Shows basic usage of the Docs API.
  Prints the title of a sample document.
  """
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
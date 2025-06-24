import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils import Job, JobType

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
SAMPLE_RANGE_NAME = "Class Data!A2:Z"
SPREADSHEET_ID = "1lLvlU7MPXryelDDKvY1hhggb3hTWCW79dy3mlX0Pp60"

def create_test_job():
    """Create a test job instance"""
    return Job(
        job_type=JobType.PYTHON_DEVELOPER,
        job_title="Junior Python Developer",
        company="Test Company Ltd",
        salary="£45,000 - £55,000",
        location="London, UK",
        contact_email="jobs@testcompany.com",
        company_link="https://testcompany.com",
        job_link="https://testcompany.com/jobs/python-dev",
        technologies=["Python", "Django", "PostgreSQL", "AWS"],
        job_description="We are looking for a Junior Python Developer to join our team...",
        company_description="Test Company is a leading tech company...",
        job_source="Test Source"
    )

def create_spreadsheet(service, title: str, columns: list[str], sheet_name: str = "Sheet1") -> str:
    """
    Create a new Google Spreadsheet with specified columns.
    
    Args:
        service: Google Sheets API service instance
        title: Title of the spreadsheet
        columns: List of column names
        sheet_name: Name of the first sheet (default: "Sheet1")
    
    Returns:
        str: The ID of the created spreadsheet
    """
    # Create a new spreadsheet
    spreadsheet = {
        'properties': {
            'title': title
        },
        'sheets': [
            {
                'properties': {
                    'title': sheet_name,
                    'gridProperties': {
                        'rowCount': 1000,
                        'columnCount': len(columns)
                    }
                }
            }
        ]
    }
    
    # Create the spreadsheet
    spreadsheet = service.spreadsheets().create(body=spreadsheet).execute()
    spreadsheet_id = spreadsheet['spreadsheetId']
    
    # Update the first row with headers
    range_name = f'{sheet_name}!A1'
    body = {
        'values': [columns]
    }
    
    # Update the headers
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption='RAW',
        body=body
    ).execute()
    
    return spreadsheet_id


def update_sheet(service, spreadsheet_id, rows, range):
    body = {
        'values': rows
    }
    try:
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        print(f"Rows appended: {result.get('updates').get('updatedRows')}")
    except HttpError as err:
        print(err)
    except Exception as e:
       print(e)


def create_sheet_service():
  """Shows basic usage of the Sheets API.
  Prints values from a sample spreadsheet.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
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
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("sheets", "v4", credentials=creds)
    return service

  except HttpError as err:
    print(err)

  


def create_rows(jobs):
    rows = []
    for job in jobs:
        job_dict = job.model_dump()
        row = []
        for col in Job.model_fields.keys():
            value = job_dict[col]
            if isinstance(value, list):
                row.append(", ".join(value))  # Join list items with commas
            else:
                row.append(value)
        rows.append(row)
    return rows


if __name__ == "__main__":
  service = create_sheet_service()
  if not SPREADSHEET_ID:
    try:
       SPREADSHEET_ID = create_spreadsheet(service, title="Jobs List", columns=list(Job.model_fields.keys()))
    except Exception as e:
       print(e)
  test_job = create_test_job()
  job_dict = test_job.model_dump()
  row = []
  for col in Job.model_fields.keys():
     value = job_dict[col]
     if isinstance(value, list):
        row.append(", ".join(value))  # Join list items with commas
     else:
        row.append(value)
        
  
  update_sheet(service, SPREADSHEET_ID, rows = [row], range='Sheet1!A:L')

 
       


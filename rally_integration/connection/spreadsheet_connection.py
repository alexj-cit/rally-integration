import gspread
import os
from dotenv import load_dotenv
from pathlib import Path

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# The ID and range of a spreadsheet.
SPREADSHEET_ID = '11NiIWdDtWTI5cXXjFXPIhadbnNkLY4Lp--7ieS83-70'

load_dotenv()


def get_connection():
    print("Getting Credentials...")
    BASE_DIR = Path(__file__).resolve().parent.parent  # Ajuste conforme sua estrutura
    credentials_path = BASE_DIR / os.getenv('GOOGLE_CREDENTIALS_PATH')

    gspread_client = gspread.service_account(filename=credentials_path)
    # list all available spreadsheets
    # sp = gspread_client.openall()
    print("Opening Metrics File...")
    spreadsheet = gspread_client.open_by_key(SPREADSHEET_ID)
    return spreadsheet
    # for spreadsheet in sp:
    #     if spreadsheet.id == SPREADSHEET_ID:
    #         return spreadsheet

    print("No spreadsheets available")
    print("Please share the spreadsheet with Service Account email")
    print(gspread_client.auth.signer_email)


def clear_spreadsheet(worksheet):
    print("Cleaning...")
    worksheet.clear()


def add_data_to_sheet(worksheet, data):
    rows = len(data)
    cols = len(data[0])
    cell_range = f'A1:{chr(65 + cols - 1)}{rows}'
    print("Saving...")
    worksheet.update(cell_range, data, value_input_option='USER_ENTERED')

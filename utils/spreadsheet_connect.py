# utils/spreadsheet.py

import os
from pathlib import Path

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials


ROOT_DIR = Path(__file__).resolve().parents[1]

load_dotenv(ROOT_DIR / ".env")


def get_google_sheet(worksheet_name: str):
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")

    if not credentials_path:
        raise RuntimeError("GOOGLE_CREDENTIALS_PATH is not configured in .env")

    if not spreadsheet_id:
        raise RuntimeError("GOOGLE_SPREADSHEET_ID is not configured in .env")

    credentials_path = Path(credentials_path)

    if not credentials_path.is_absolute():
        credentials_path = ROOT_DIR / credentials_path

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_file(
        credentials_path,
        scopes=scopes,
    )

    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(spreadsheet_id)

    worksheet = spreadsheet.worksheet(worksheet_name)

    return worksheet
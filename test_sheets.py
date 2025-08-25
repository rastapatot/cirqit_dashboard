#!/usr/bin/env python3

import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import json

# Load secrets the same way the app does
try:
    # Try to load from Streamlit secrets
    service_account_info = st.secrets["google"]
    print("✅ Loaded secrets from Streamlit")
except:
    # Fallback to loading from service account file
    try:
        with open('service_account.json', 'r') as f:
            service_account_info = json.load(f)
        print("✅ Loaded secrets from service_account.json")
    except:
        print("❌ Could not load service account credentials")
        exit(1)

print(f"Service account email: {service_account_info.get('client_email', 'Unknown')}")

# Set up credentials
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
try:
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    gc = gspread.authorize(credentials)
    print("✅ Google Sheets client authorized")
except Exception as e:
    print(f"❌ Failed to authorize: {e}")
    exit(1)

# Test each sheet
sheets_to_test = [
    {"id": "1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8", "name": "Attendance Sheet"},
    {"id": "1xGVH2TDV4at_WmNnaMDtjYbQPTAAUffd04bejme1Gxo", "name": "Scores Sheet"},
    {"id": "1u5i9s9Ty-jf-djMeAAzO1qOl_nk3_X3ICdfFfLGvLcc", "name": "Masterlist Sheet"},
]

for sheet_info in sheets_to_test:
    print(f"\n--- Testing {sheet_info['name']} ---")
    try:
        sheet = gc.open_by_key(sheet_info["id"])
        print(f"✅ Successfully opened sheet: {sheet.title}")
        
        worksheets = [ws.title for ws in sheet.worksheets()]
        print(f"📋 Worksheets: {worksheets}")
        
        # Test reading from first worksheet
        if worksheets:
            first_ws = sheet.worksheet(worksheets[0])
            sample_data = first_ws.get_all_values()[:2]  # Get first 2 rows
            print(f"📖 Sample data (first 2 rows): {len(sample_data)} rows")
            
            # Test writing (try to update a cell that won't matter)
            try:
                # Get current value and write it back (safe test)
                test_cell = first_ws.cell(1, 1)
                current_value = test_cell.value
                first_ws.update_cell(1, 1, current_value)
                print("✅ Write test successful")
            except Exception as e:
                print(f"❌ Write test failed: {e}")
        
    except Exception as e:
        print(f"❌ Failed to access {sheet_info['name']}: {e}")

# Test specific attendance sheet access
print(f"\n--- Testing Member Attendance Worksheet ---")
try:
    ATTENDANCE_SHEET_ID = "1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8"
    attendance_sheet = gc.open_by_key(ATTENDANCE_SHEET_ID)
    
    # Find member attendance worksheet
    member_ws = None
    for ws in attendance_sheet.worksheets():
        if 'member' in ws.title.lower() and 'attendance' in ws.title.lower():
            member_ws = ws
            break
    
    if member_ws:
        print(f"✅ Found Member Attendance worksheet: {member_ws.title}")
        
        # Get all records
        all_records = member_ws.get_all_records()
        print(f"📊 Total records: {len(all_records)}")
        
        # Look for Mariel and Christopher
        for name in ["Mariel", "Christopher"]:
            found_records = []
            for i, record in enumerate(all_records):
                if name in str(record.get('Member Name', '')):
                    found_records.append((i+2, record))  # i+2 for row number
            
            if found_records:
                print(f"👤 {name} records found:")
                for row_num, record in found_records:
                    session = record.get('Session', 'Unknown')
                    points = record.get('Points Earned', 0)
                    print(f"   Row {row_num}: {session} = {points} points")
            else:
                print(f"❌ No records found for {name}")
    else:
        print("❌ Member Attendance worksheet not found")
        print(f"Available worksheets: {[ws.title for ws in attendance_sheet.worksheets()]}")
        
except Exception as e:
    print(f"❌ Failed to test attendance sheet: {e}")

print("\n=== Test Complete ===")
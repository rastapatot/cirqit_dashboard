#!/usr/bin/env python3

import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

def fix_attendance_records():
    """Fix Mariel and Christopher's attendance records"""
    try:
        # Load credentials
        service_account_info = st.secrets["google"]
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        
        # Open attendance sheet
        ATTENDANCE_SHEET_ID = "1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8"
        attendance_sheet = gc.open_by_key(ATTENDANCE_SHEET_ID)
        
        # Find member attendance worksheet
        member_ws = None
        for ws in attendance_sheet.worksheets():
            if 'member' in ws.title.lower() and 'attendance' in ws.title.lower():
                member_ws = ws
                break
        
        if not member_ws:
            print("❌ Member Attendance worksheet not found")
            return False
        
        # Get all records
        all_records = member_ws.get_all_records()
        print(f"📊 Processing {len(all_records)} total records...")
        
        # Find Points Earned column
        points_col = member_ws.find('Points Earned').col
        print(f"📍 Points Earned column: {points_col}")
        
        updates_made = 0
        
        # Fix Mariel Peñaflor records
        print("\n🔧 Fixing Mariel Peñaflor records...")
        for i, record in enumerate(all_records):
            member_name = str(record.get('Member Name', ''))
            if 'Mariel' in member_name and 'Pe' in member_name:
                session = record.get('Session', '')
                current_points = record.get('Points Earned', 0)
                
                # Update if it's 0 points and should be 1
                if current_points == 0 and any(s in session for s in ['TechSharing2-ADAM', 'TechSharing3-N8N', 'TechSharing3.1-Claude']):
                    row_num = i + 2  # +2 because headers are row 1
                    member_ws.update_cell(row_num, points_col, 1)
                    print(f"   ✅ Updated row {row_num}: {session} = 0 → 1 point")
                    updates_made += 1
                elif current_points == 1:
                    print(f"   ⏭️  Row {i+2}: {session} already has 1 point")
        
        # Fix Christopher Lizada records  
        print("\n🔧 Fixing Christopher Lizada records...")
        for i, record in enumerate(all_records):
            member_name = str(record.get('Member Name', ''))
            if 'Christopher' in member_name and 'Lizada' in member_name:
                session = record.get('Session', '')
                current_points = record.get('Points Earned', 0)
                
                # Update if it's 0 points and should be 1
                if current_points == 0 and any(s in session for s in ['TechSharing2-ADAM', 'TechSharing3-N8N', 'TechSharing3.1-Claude']):
                    row_num = i + 2  # +2 because headers are row 1
                    member_ws.update_cell(row_num, points_col, 1)
                    print(f"   ✅ Updated row {row_num}: {session} = 0 → 1 point")
                    updates_made += 1
                elif current_points == 1:
                    print(f"   ⏭️  Row {i+2}: {session} already has 1 point")
        
        print(f"\n🎯 Total updates made: {updates_made}")
        return updates_made > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_attendance_records()
    if success:
        print("✅ Attendance records updated successfully!")
    else:
        print("❌ Failed to update attendance records")
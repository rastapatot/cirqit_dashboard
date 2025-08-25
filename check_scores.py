#!/usr/bin/env python3

import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd

def check_individual_scores():
    """Check what individual scores the dashboard is calculating"""
    try:
        # Load credentials (same as dashboard)
        service_account_info = st.secrets["google"]
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        
        # Load attendance data (same as dashboard)
        ATTENDANCE_SHEET_ID = "1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8"
        attendance_sheet = gc.open_by_key(ATTENDANCE_SHEET_ID)
        
        # Get all worksheets as the dashboard does
        attendance = {ws.title: pd.DataFrame(ws.get_all_records()) for ws in attendance_sheet.worksheets()}
        
        print("📋 Available worksheets in Attendance Sheet:")
        for sheet_name, sheet_data in attendance.items():
            print(f"  - {sheet_name}: {len(sheet_data)} rows")
            if len(sheet_data) > 0:
                print(f"    Columns: {list(sheet_data.columns)}")
        
        print("\n🔍 Looking for individual member scores...")
        
        # Try to find individual member attendance data (same logic as dashboard)
        individual_scores = pd.DataFrame()
        for sheet_name, sheet_data in attendance.items():
            if len(sheet_data) > 0 and 'Member Name' in sheet_data.columns and 'Points Earned' in sheet_data.columns:
                print(f"\n✅ Found individual attendance data in: {sheet_name}")
                
                # Check Alliance members specifically
                alliance_members = sheet_data[sheet_data['Team'].str.contains('Alliance', na=False, case=False) | 
                                            sheet_data.get('Team Name', pd.Series(dtype='object')).str.contains('Alliance', na=False, case=False)]
                
                if len(alliance_members) > 0:
                    print(f"👥 Alliance members found: {len(alliance_members)} records")
                    
                    # Group by member and sum points (same as dashboard)
                    if 'Team' in sheet_data.columns:
                        individual_scores = sheet_data.groupby(['Team', 'Member Name'])['Points Earned'].sum().reset_index()
                    elif 'Team Name' in sheet_data.columns:
                        sheet_data_renamed = sheet_data.rename(columns={'Team Name': 'Team'})
                        individual_scores = sheet_data_renamed.groupby(['Team', 'Member Name'])['Points Earned'].sum().reset_index()
                    
                    print("\n📊 Individual scores calculation:")
                    alliance_scores = individual_scores[individual_scores['Team'].str.contains('Alliance', na=False, case=False)]
                    for _, row in alliance_scores.iterrows():
                        print(f"  {row['Member Name']}: {row['Points Earned']} points")
                    
                    # Check raw records for Mariel and Christopher
                    print("\n🔍 Raw records for target members:")
                    for name in ['Mariel', 'Christopher']:
                        member_records = sheet_data[sheet_data['Member Name'].str.contains(name, na=False, case=False)]
                        print(f"\n{name} records ({len(member_records)} total):")
                        if len(member_records) > 0:
                            for _, record in member_records.iterrows():
                                team = record.get('Team', record.get('Team Name', 'Unknown'))
                                session = record.get('Session', 'Unknown')
                                points = record.get('Points Earned', 0)
                                print(f"  {team} | {session} | {points} points")
                break
        
        if len(individual_scores) == 0:
            print("❌ No individual member scores found - dashboard will use team distribution logic")
        else:
            print(f"\n✅ Individual scores loaded: {len(individual_scores)} member records")
        
        return individual_scores
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    scores = check_individual_scores()
    print(f"\n=== Final result: {len(scores)} individual score records ===")
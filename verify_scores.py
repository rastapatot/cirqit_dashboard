#!/usr/bin/env python3

import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd

def verify_alliance_scores():
    """Verify Alliance of Just Minds scores are calculated correctly"""
    try:
        # Load credentials
        service_account_info = st.secrets["google"]
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        
        # Load attendance data
        ATTENDANCE_SHEET_ID = "1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8"
        attendance_sheet = gc.open_by_key(ATTENDANCE_SHEET_ID)
        
        # Get Member Attendance worksheet
        member_ws = None
        for ws in attendance_sheet.worksheets():
            if 'member' in ws.title.lower() and 'attendance' in ws.title.lower():
                member_ws = ws
                break
        
        if not member_ws:
            print("❌ Member Attendance worksheet not found")
            return
        
        # Get all records and filter for Alliance
        all_records = member_ws.get_all_records()
        member_df = pd.DataFrame(all_records)
        
        alliance_records = member_df[member_df['Team'].str.contains('Alliance', na=False, case=False)]
        
        print("🏆 ALLIANCE OF JUST MINDS - SCORE VERIFICATION")
        print("=" * 50)
        
        # Calculate individual member scores
        individual_scores = alliance_records.groupby(['Team', 'Member Name'])['Points Earned'].sum().reset_index()
        
        print("👥 Individual Member Scores:")
        total_member_points = 0
        members_with_points = 0
        for _, row in individual_scores.iterrows():
            points = int(row['Points Earned'])
            total_member_points += points
            if points > 0:
                members_with_points += 1
            print(f"  {row['Member Name']}: {points} points")
        
        print(f"\n📊 Team Member Summary:")
        print(f"  Total Members: 5")
        print(f"  Members with Points: {members_with_points}")
        print(f"  Member Attendance Rate: {(members_with_points/5)*100:.1f}%")
        print(f"  Total Member Points: {total_member_points}")
        
        # Check coach scores
        coach_ws = None
        for ws in attendance_sheet.worksheets():
            if 'coach' in ws.title.lower() and 'attendance' in ws.title.lower():
                coach_ws = ws
                break
        
        if coach_ws:
            coach_records = coach_ws.get_all_records()
            coach_df = pd.DataFrame(coach_records)
            alliance_coach = coach_df[coach_df['Team'].str.contains('Alliance', na=False, case=False)]
            
            if len(alliance_coach) > 0:
                coach_total = alliance_coach['Points Earned'].sum()
                print(f"\n🎓 Coach Score:")
                print(f"  Coach: Vincent Daraliay")
                print(f"  Total Coach Points: {coach_total}")
            else:
                print(f"\n🎓 Coach Score:")
                print(f"  No coach attendance records found")
                coach_total = 0
        else:
            coach_total = 0
            print(f"\n🎓 Coach Score:")
            print(f"  Coach worksheet not found")
        
        # Calculate final team score
        final_score = total_member_points + coach_total
        print(f"\n🏆 FINAL TEAM SCORE:")
        print(f"  {total_member_points} (Members) + {coach_total} (Coach) = {final_score} (Total)")
        print(f"  Expected Member Attendance Rate: 100.0%")
        
        return final_score
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    score = verify_alliance_scores()
    if score:
        print(f"\n✅ Verification complete: Alliance should have {score} total points")
    else:
        print("\n❌ Verification failed")
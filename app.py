
import streamlit as st
import pandas as pd
import sqlite3

ADMIN_PASSWORD = st.secrets["admin_password"]
DB_FILE = "cirqit_dashboard.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bonus_points (
            team_name TEXT PRIMARY KEY,
            bonus INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_bonus_points():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM bonus_points", conn)
    conn.close()
    return df

def add_bonus_point(team_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE bonus_points SET bonus = bonus + 1 WHERE team_name = ?", (team_name,))
    conn.commit()
    conn.close()

def ensure_teams_in_db(team_names):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for team in team_names:
        cursor.execute("INSERT OR IGNORE INTO bonus_points (team_name, bonus) VALUES (?, 0)", (team,))
    conn.commit()
    conn.close()

def create_individual_attendance_sheets():
    """Create individual member and coach attendance worksheets from existing team data"""
    import gspread
    from google.oauth2.service_account import Credentials
    
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    service_account_info = st.secrets["google"]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    gc = gspread.authorize(credentials)
    
    try:
        # Get data from existing sheets
        scores_sheet = gc.open_by_key("1xGVH2TDV4at_WmNnaMDtjYbQPTAAUffd04bejme1Gxo")
        masterlist_sheet = gc.open_by_key("1u5i9s9Ty-jf-djMeAAzO1qOl_nk3_X3ICdfFfLGvLcc")
        attendance_sheet = gc.open_by_key("1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8")
        
        scores_data = pd.DataFrame(scores_sheet.sheet1.get_all_records())
        masterlist_data = pd.DataFrame(masterlist_sheet.sheet1.get_all_records())
        
        # Create individual member attendance records
        member_records = []
        coach_records = []
        
        for _, team_row in scores_data.iterrows():
            team_name = team_row.get('Team Name', '')
            
            # Get team members and coach
            team_info = masterlist_data[masterlist_data['Team Name'] == team_name]
            if len(team_info) == 0:
                continue
                
            coach_name = team_info.iloc[0].get('Coach/Consultant', '')
            coach_dept = team_info.iloc[0].get('Coach Department', 'Coach')
            
            # Tech sharing sessions data
            sessions = [
                {'name': 'TechSharing2-ADAM', 'members': team_row.get('TechSharing2-ADAM_Members', 0), 'coaches': team_row.get('TechSharing2-ADAM_Coaches', 0)},
                {'name': 'TechSharing3-N8N', 'members': team_row.get('TechSharing3-N8N_Members', 0), 'coaches': team_row.get('TechSharing3-N8N_Coaches', 0)},
                {'name': 'TechSharing3.1-Claude', 'members': team_row.get('TechSharing3.1-Claude_Members', 0), 'coaches': team_row.get('TechSharing3.1-Claude_Coaches', 0)},
            ]
            
            # Create member records - distribute attendance among team members
            team_members = team_info['Member Name'].tolist()
            for session in sessions:
                attended_count = int(session['members']) if session['members'] else 0
                
                # For now, assume first N members attended (can be manually corrected later)
                for i, member_name in enumerate(team_members):
                    points_earned = 1 if i < attended_count else 0
                    member_records.append({
                        'Member Name': member_name,
                        'Department': team_info.iloc[i].get('Member Department', ''),
                        'Team': team_name,
                        'Session': session['name'],
                        'Day Session': 'Day',  # Default - can be updated
                        'Night Session': '',
                        'Sessions Attended': 'Day' if points_earned > 0 else '',
                        'Points Earned': points_earned
                    })
            
            # Create coach records
            for session in sessions:
                attended = int(session['coaches']) if session['coaches'] else 0
                points_earned = attended * 2  # Coaches get 2 points per session attended
                
                if points_earned > 0:
                    coach_records.append({
                        'Coach Name': coach_name,
                        'Department': coach_dept,
                        'Team': team_name,
                        'Session': session['name'],
                        'Day Session': 'Day',
                        'Night Session': '',
                        'Sessions Attended': 'Day',
                        'Points Earned': points_earned
                    })
        
        # Create or update Member Attendance worksheet
        member_df = pd.DataFrame(member_records)
        try:
            member_ws = attendance_sheet.worksheet("Member Attendance")
            member_ws.clear()
        except:
            member_ws = attendance_sheet.add_worksheet(title="Member Attendance", rows=len(member_df)+1, cols=len(member_df.columns))
        
        # Update member worksheet
        if len(member_df) > 0:
            member_ws.update([member_df.columns.tolist()] + member_df.values.tolist())
        
        # Create or update Coach Attendance worksheet  
        coach_df = pd.DataFrame(coach_records)
        try:
            coach_ws = attendance_sheet.worksheet("Coach Attendance")
            coach_ws.clear()
        except:
            coach_ws = attendance_sheet.add_worksheet(title="Coach Attendance", rows=len(coach_df)+1, cols=len(coach_df.columns))
        
        # Update coach worksheet
        if len(coach_df) > 0:
            coach_ws.update([coach_df.columns.tolist()] + coach_df.values.tolist())
            
        return True, len(member_records), len(coach_records)
        
    except Exception as e:
        return False, 0, 0

def fix_duplicate_alliance_teams():
    import gspread
    from google.oauth2.service_account import Credentials
    
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    service_account_info = st.secrets["google"]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    gc = gspread.authorize(credentials)
    
    SCORES_SHEET_ID = "1xGVH2TDV4at_WmNnaMDtjYbQPTAAUffd04bejme1Gxo"
    scores_sheet = gc.open_by_key(SCORES_SHEET_ID)
    worksheet = scores_sheet.sheet1
    
    # Get all data
    all_values = worksheet.get_all_values()
    headers = all_values[0]
    
    # Find Alliance teams
    alliance_rows = []
    for i, row in enumerate(all_values[1:], start=2):
        if 'Alliance of Just Minds' in row[0]:
            alliance_rows.append((i, row))
    
    if len(alliance_rows) == 2:
        # Find which one has data and which is empty
        row1_idx, row1_data = alliance_rows[0]
        row2_idx, row2_data = alliance_rows[1]
        
        # Check which row has actual scores (Total_Score column)
        total_score_col = headers.index('Total_Score')
        row1_score = float(row1_data[total_score_col]) if row1_data[total_score_col] else 0
        row2_score = float(row2_data[total_score_col]) if row2_data[total_score_col] else 0
        
        if row1_score > 0 and row2_score == 0:
            # Keep row1, delete row2, rename row1 to clean name
            worksheet.update_cell(row1_idx, 1, "Alliance of Just Minds")
            worksheet.delete_rows(row2_idx)
        elif row2_score > 0 and row1_score == 0:
            # Keep row2, delete row1, rename row2 to clean name
            worksheet.update_cell(row2_idx, 1, "Alliance of Just Minds")
            worksheet.delete_rows(row1_idx)
        
        return True
    return False

def check_sheet_permissions():
    """Check and display detailed information about sheet access"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        service_account_info = st.secrets["google"]
        credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        
        # Get service account email for permission instructions
        service_email = service_account_info.get("client_email", "Unknown")
        
        sheets_to_check = [
            {"id": "1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8", "name": "Attendance Sheet", "url": "https://docs.google.com/spreadsheets/d/1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8"},
            {"id": "1xGVH2TDV4at_WmNnaMDtjYbQPTAAUffd04bejme1Gxo", "name": "Scores Sheet", "url": "https://docs.google.com/spreadsheets/d/1xGVH2TDV4at_WmNnaMDtjYbQPTAAUffd04bejme1Gxo"},
            {"id": "1u5i9s9Ty-jf-djMeAAzO1qOl_nk3_X3ICdfFfLGvLcc", "name": "Masterlist Sheet", "url": "https://docs.google.com/spreadsheets/d/1u5i9s9Ty-jf-djMeAAzO1qOl_nk3_X3ICdfFfLGvLcc"},
        ]
        
        results = []
        attendance_accessible = False
        
        for sheet_info in sheets_to_check:
            try:
                sheet = gc.open_by_key(sheet_info["id"])
                worksheets = [ws.title for ws in sheet.worksheets()]
                
                # Check for specific attendance worksheets
                has_member_attendance = any('member' in ws.lower() and 'attendance' in ws.lower() for ws in worksheets)
                has_coach_attendance = any('coach' in ws.lower() and 'attendance' in ws.lower() for ws in worksheets)
                
                if sheet_info["name"] == "Attendance Sheet":
                    attendance_accessible = True
                
                results.append({
                    "name": sheet_info["name"],
                    "status": "✅ Accessible",
                    "worksheets": worksheets,
                    "url": sheet_info["url"],
                    "has_member_attendance": has_member_attendance,
                    "has_coach_attendance": has_coach_attendance
                })
            except Exception as e:
                error_msg = str(e)
                if "does not have permission" in error_msg or "403" in error_msg:
                    status = f"❌ Permission Denied - Service account needs Editor access"
                elif "not found" in error_msg or "404" in error_msg:
                    status = f"❌ Sheet Not Found - Invalid ID"
                else:
                    status = f"❌ Error: {error_msg[:50]}..."
                
                results.append({
                    "name": sheet_info["name"],
                    "status": status,
                    "worksheets": [],
                    "url": sheet_info["url"],
                    "has_member_attendance": False,
                    "has_coach_attendance": False
                })
        
        return {
            "results": results,
            "service_email": service_email,
            "attendance_accessible": attendance_accessible
        }
        
    except Exception as e:
        return {
            "results": [{"name": "All Sheets", "status": f"❌ General Error: {str(e)}", "worksheets": [], "url": "", "has_member_attendance": False, "has_coach_attendance": False}],
            "service_email": "Unknown",
            "attendance_accessible": False
        }

@st.cache_data
def load_data():
    import gspread
    from google.oauth2.service_account import Credentials

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    service_account_info = st.secrets["google"]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    gc = gspread.authorize(credentials)

    ATTENDANCE_SHEET_ID = "1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8"
    SCORES_SHEET_ID = "1xGVH2TDV4at_WmNnaMDtjYbQPTAAUffd04bejme1Gxo"
    MASTERLIST_SHEET_ID = "1u5i9s9Ty-jf-djMeAAzO1qOl_nk3_X3ICdfFfLGvLcc"

    attendance_sheet = gc.open_by_key(ATTENDANCE_SHEET_ID)
    scores_sheet = gc.open_by_key(SCORES_SHEET_ID)
    masterlist_sheet = gc.open_by_key(MASTERLIST_SHEET_ID)

    attendance = {ws.title: pd.DataFrame(ws.get_all_records()) for ws in attendance_sheet.worksheets()}
    scores = pd.DataFrame(scores_sheet.sheet1.get_all_records())
    masterlist = pd.DataFrame(masterlist_sheet.sheet1.get_all_records())

    return attendance, scores, masterlist

def calculate_individual_scores_from_team_data(scores_df, masterlist_df):
    """Calculate individual member scores by distributing team points among members"""
    individual_records = []
    
    for _, team_row in scores_df.iterrows():
        team_name = team_row.get('Team Name', '')
        
        # Handle team name variations (like "Alliance of Just Minds" vs "Alliance of Just Minds(AJM)")
        team_info = masterlist_df[masterlist_df['Team Name'] == team_name]
        if len(team_info) == 0:
            # Try to find team with similar name (remove parentheses and match both directions)
            clean_team_name = team_name.split('(')[0].strip()
            # Search for masterlist teams that start with the clean name
            team_info = masterlist_df[masterlist_df['Team Name'].str.startswith(clean_team_name, na=False)]
            if len(team_info) == 0:
                # Also try the reverse - clean masterlist names and match with score team name
                masterlist_clean = masterlist_df.copy()
                masterlist_clean['Clean_Name'] = masterlist_clean['Team Name'].str.split('(').str[0].str.strip()
                team_info = masterlist_clean[masterlist_clean['Clean_Name'] == clean_team_name]
        if len(team_info) == 0:
            continue
            
        team_members = team_info['Member Name'].tolist()
        
        # Tech sharing sessions data
        sessions = [
            {'name': 'TechSharing2-ADAM', 'members': team_row.get('TechSharing2-ADAM_Members', 0)},
            {'name': 'TechSharing3-N8N', 'members': team_row.get('TechSharing3-N8N_Members', 0)},
            {'name': 'TechSharing3.1-Claude', 'members': team_row.get('TechSharing3.1-Claude_Members', 0)},
        ]
        
        # Use the actual team name from masterlist for consistency
        actual_team_name = team_info['Team Name'].iloc[0] if len(team_info) > 0 else team_name
        
        # Distribute attendance among team members
        for session in sessions:
            attended_count = int(session['members']) if session['members'] else 0
            
            # Distribute points among first N members (can be refined later)
            for i, member_name in enumerate(team_members):
                points_earned = 1 if i < attended_count else 0
                individual_records.append({
                    'Team': actual_team_name,
                    'Member Name': member_name,
                    'Session': session['name'],
                    'Points Earned': points_earned
                })
    
    if individual_records:
        member_df = pd.DataFrame(individual_records)
        # Sum points per member per team
        individual_scores = member_df.groupby(['Team', 'Member Name'])['Points Earned'].sum().reset_index()
        return individual_scores
    
    return pd.DataFrame()

@st.cache_data
def get_individual_member_scores():
    """Get individual member scores from actual Google Sheets attendance data"""
    try:
        # Load actual attendance data from Google Sheets
        attendance, scores, masterlist = load_data()
        
        # Try to find individual member attendance data in Google Sheets
        for sheet_name, sheet_data in attendance.items():
            if len(sheet_data) > 0 and 'Member Name' in sheet_data.columns and 'Points Earned' in sheet_data.columns:
                # Found actual individual attendance data - use it!
                if 'Team' in sheet_data.columns:
                    # Sum points per member per team
                    individual_scores = sheet_data.groupby(['Team', 'Member Name'])['Points Earned'].sum().reset_index()
                    return individual_scores
                elif 'Team Name' in sheet_data.columns:
                    # Alternative column name
                    sheet_data_renamed = sheet_data.rename(columns={'Team Name': 'Team'})
                    individual_scores = sheet_data_renamed.groupby(['Team', 'Member Name'])['Points Earned'].sum().reset_index()
                    return individual_scores
        
        # If no proper individual data found, return empty (don't use fake logic)
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def calculate_individual_coach_scores_from_team_data(scores_df, masterlist_df):
    """Calculate individual coach scores by using team coach attendance data"""
    coach_records = []
    
    for _, team_row in scores_df.iterrows():
        team_name = team_row.get('Team Name', '')
        
        # Handle team name variations (like "Alliance of Just Minds" vs "Alliance of Just Minds(AJM)")
        team_info = masterlist_df[masterlist_df['Team Name'] == team_name]
        if len(team_info) == 0:
            # Try to find team with similar name (remove parentheses and match both directions)
            clean_team_name = team_name.split('(')[0].strip()
            # Search for masterlist teams that start with the clean name
            team_info = masterlist_df[masterlist_df['Team Name'].str.startswith(clean_team_name, na=False)]
            if len(team_info) == 0:
                # Also try the reverse - clean masterlist names and match with score team name
                masterlist_clean = masterlist_df.copy()
                masterlist_clean['Clean_Name'] = masterlist_clean['Team Name'].str.split('(').str[0].str.strip()
                team_info = masterlist_clean[masterlist_clean['Clean_Name'] == clean_team_name]
        if len(team_info) == 0:
            continue
            
        coach_name = team_info.iloc[0].get('Coach/Consultant', '') if len(team_info) > 0 else ''
        if not coach_name:
            continue
        
        # Tech sharing sessions coach attendance
        sessions = [
            {'name': 'TechSharing2-ADAM', 'coaches': team_row.get('TechSharing2-ADAM_Coaches', 0)},
            {'name': 'TechSharing3-N8N', 'coaches': team_row.get('TechSharing3-N8N_Coaches', 0)}, 
            {'name': 'TechSharing3.1-Claude', 'coaches': team_row.get('TechSharing3.1-Claude_Coaches', 0)},
        ]
        
        # Use the actual team name from masterlist for consistency
        actual_team_name = team_info['Team Name'].iloc[0] if len(team_info) > 0 else team_name
        
        # Create coach records based on attendance
        for session in sessions:
            attended = int(session['coaches']) if session['coaches'] else 0
            if attended > 0:  # Coach attended this session
                coach_records.append({
                    'Team': actual_team_name,
                    'Coach Name': coach_name,
                    'Session': session['name'],
                    'Points Earned': attended * 2  # Coaches get 2 points per session attended
                })
    
    if coach_records:
        coach_df = pd.DataFrame(coach_records)
        # Sum points per coach per team
        individual_coach_scores = coach_df.groupby(['Team', 'Coach Name'])['Points Earned'].sum().reset_index()
        return individual_coach_scores
    
    return pd.DataFrame()

@st.cache_data  
def get_individual_coach_scores():
    """Get individual coach scores from actual Google Sheets attendance data"""
    try:
        # Load actual attendance data from Google Sheets
        attendance, scores, masterlist = load_data()
        
        # Try to find individual coach attendance data in Google Sheets
        for sheet_name, sheet_data in attendance.items():
            if len(sheet_data) > 0 and 'Coach Name' in sheet_data.columns and 'Points Earned' in sheet_data.columns:
                # Found actual individual coach attendance data - use it!
                if 'Team' in sheet_data.columns:
                    # Sum points per coach per team
                    coach_scores = sheet_data.groupby(['Team', 'Coach Name'])['Points Earned'].sum().reset_index()
                    return coach_scores
                elif 'Team Name' in sheet_data.columns:
                    # Alternative column name
                    sheet_data_renamed = sheet_data.rename(columns={'Team Name': 'Team'})
                    coach_scores = sheet_data_renamed.groupby(['Team', 'Coach Name'])['Points Earned'].sum().reset_index()
                    return coach_scores
        
        # If no proper individual coach data found, fall back to calculated scores
        return calculate_individual_coach_scores_from_team_data(scores, masterlist)
    except Exception as e:
        return pd.DataFrame()
def main():
    st.set_page_config("CirQit Hackathon Dashboard", layout="wide")
    
    # Display logo and title
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 20px;">
        <img src="data:image/png;base64,{}" width="120"/>
        <h1 style="margin: 0;">CirQit Hackathon Dashboard</h1>
    </div>
    """.format(
        __import__('base64').b64encode(open('CirQit_Logo.png', 'rb').read()).decode()
    ), unsafe_allow_html=True)

    init_db()
    attendance, scores, masterlist = load_data()
    individual_scores = get_individual_member_scores()
    individual_coach_scores = get_individual_coach_scores()
    
    ensure_teams_in_db(scores["Team Name"].dropna().unique())
    bonus_df = get_bonus_points()

    scores = scores.merge(bonus_df, how="left", left_on="Team Name", right_on="team_name")
    scores["bonus"] = scores["bonus"].fillna(0)
    
    # Add coach total scores to each team they manage
    scores["coach_total_bonus"] = 0
    if len(individual_coach_scores) > 0:
        # Calculate each coach's total score across all teams
        coach_totals = individual_coach_scores.groupby("Coach Name")["Points Earned"].sum().reset_index()
        coach_totals.columns = ["Coach Name", "Coach Total Score"]
        
        # Add coach total score to each team they manage
        for _, coach_row in coach_totals.iterrows():
            coach_name = coach_row["Coach Name"]
            coach_total_score = coach_row["Coach Total Score"]
            
            # Find all teams this coach manages
            coach_teams = masterlist[masterlist["Coach/Consultant"] == coach_name]["Team Name"].unique()
            
            # Add coach's total score to each team they manage
            for team_name in coach_teams:
                team_mask = scores["Team Name"] == team_name
                scores.loc[team_mask, "coach_total_bonus"] = coach_total_score
    
    scores["Total Event Attendance Bonus"] = scores["Total_Member_Points"] + scores["Total_Coach_Points"]
    scores["Total_with_Bonus"] = scores["Total_Score"] + scores["bonus"] + scores["coach_total_bonus"]

    
    tab1, tab2, tab3, tab4 = st.tabs(["Team Performance Overview", "Team Explorer", "Coach Explorer", "Admin Panel"])

    with tab1:
        st.subheader("📊 Team Performance Overview")
        teams_display = scores[["Team Name", "Total_Score", "Total Event Attendance Bonus", "coach_total_bonus", "bonus", "Average_Score", "Member_Attendance_Rate", "Coach_Attendance_Rate"]].reset_index(drop=True)
        teams_display.index = teams_display.index + 1
        st.dataframe(teams_display)

    with tab2:
        st.subheader("🔍 Team Explorer")
        selected_team = st.selectbox("Select a team", sorted(scores["Team Name"].dropna().unique()))
        
        # Enhanced team matching to handle name variations
        team_info = masterlist[masterlist["Team Name"] == selected_team]
        if len(team_info) == 0:
            # Try matching with different name formats
            # Remove parentheses from selected team and match with masterlist teams that start with it
            clean_selected = selected_team.split('(')[0].strip()
            team_info = masterlist[masterlist["Team Name"].str.startswith(clean_selected, na=False)]
            
            if len(team_info) == 0:
                # Try the reverse - clean masterlist names and match with selected team
                masterlist_clean = masterlist.copy()
                masterlist_clean['Clean_Name'] = masterlist_clean['Team Name'].str.split('(').str[0].str.strip()
                team_info = masterlist_clean[masterlist_clean['Clean_Name'] == clean_selected]
                
            if len(team_info) == 0:
                # Last resort - partial matching
                team_info = masterlist[masterlist["Team Name"].str.contains(clean_selected, na=False, regex=False)]
        team_score = scores[scores["Team Name"] == selected_team]["Total_Score"].iloc[0]
        team_bonus = scores[scores["Team Name"] == selected_team]["bonus"].iloc[0]
        team_coach_bonus = scores[scores["Team Name"] == selected_team]["coach_total_bonus"].iloc[0]
        team_total = scores[scores["Team Name"] == selected_team]["Total_with_Bonus"].iloc[0]
        team_attendance_bonus = scores[scores["Team Name"] == selected_team]["Total Event Attendance Bonus"].iloc[0]
        
        st.write(f"**Team Score:** {team_score} (Base) + {team_attendance_bonus} (Attendance) + {team_coach_bonus} (Coach Total) + {team_bonus} (Admin Bonus) = {team_total} (Total)")
        st.write("**Team Members:**")
        
        # Initialize all variables with defaults first
        coach_name = ""
        coach_dept = "Coach"
        coach_points = 0
        
        # Get coach info and score
        try:
            if len(team_info) > 0:
                coach_name = str(team_info["Coach/Consultant"].iloc[0]) if "Coach/Consultant" in team_info.columns else ""
                if "Coach Department" in team_info.columns:
                    dept_value = team_info["Coach Department"].iloc[0]
                    if dept_value and str(dept_value) not in ['nan', 'None', '']:
                        coach_dept = str(dept_value)
        except Exception:
            coach_name = ""
            coach_dept = "Coach"
        
        # Get coach total score across ALL teams they manage
        try:
            if len(individual_coach_scores) > 0 and coach_name:
                coach_all_scores = individual_coach_scores[individual_coach_scores["Coach Name"] == coach_name]
                if len(coach_all_scores) > 0:
                    coach_points = float(coach_all_scores["Points Earned"].sum())
        except Exception:
            coach_points = 0
        
        # Create coach entry
        coach_entry = pd.DataFrame({
            "Member Name": [coach_name],
            "Member Department": [coach_dept],
            "Role": ["Coach"],
            "Points Earned": [coach_points]
        })
        
        # Merge team member info with individual member scores
        team_info_with_team_scores = team_info.merge(scores, on="Team Name", how="left")
        
        # Add individual member scores
        if len(individual_scores) > 0:
            team_info_with_individual = team_info_with_team_scores.merge(
                individual_scores,
                left_on=["Team Name", "Member Name"],
                right_on=["Team", "Member Name"],
                how="left"
            )
            team_info_with_individual["Points Earned"] = team_info_with_individual["Points Earned"].fillna(0)
            team_members_display = team_info_with_individual[["Member Name", "Member Department", "Points Earned"]].sort_values("Member Name").reset_index(drop=True)
        else:
            # If individual scores unavailable, show 0 for all members
            team_members_display = team_info_with_team_scores[["Member Name", "Member Department"]].sort_values("Member Name").reset_index(drop=True)
            team_members_display["Points Earned"] = 0
        
        # Add Role column for team members
        team_members_display["Role"] = "Team Member"
        
        # Handle dual-role scenario (coach who is also a team member)
        coach_is_member = coach_name in team_members_display["Member Name"].values if coach_name else False
        
        if coach_is_member:
            # If coach is also a team member, update their role and combine their points
            member_idx = team_members_display[team_members_display["Member Name"] == coach_name].index[0]
            member_points = team_members_display.loc[member_idx, "Points Earned"]
            
            # Update coach entry to show total points (coach + member)
            coach_entry.loc[0, "Points Earned"] = coach_points + member_points
            coach_entry.loc[0, "Role"] = "Coach & Team Member"
            
            # Remove the duplicate member entry
            team_members_display = team_members_display.drop(member_idx).reset_index(drop=True)
        
        # Combine coach and members (coach first)
        combined_display = pd.concat([coach_entry, team_members_display], ignore_index=True)
        combined_display.index = combined_display.index + 1
        
        st.dataframe(combined_display, 
                    column_config={
                        "Member Name": st.column_config.Column("Name", width="medium"),
                        "Member Department": st.column_config.Column("Department", width="medium"),
                        "Role": st.column_config.Column("Role", width="small"),
                        "Points Earned": st.column_config.Column("Individual Points", width="small")
                    })

    with tab3:
        st.subheader("🎓 Coach Explorer")
        selected_coach = st.selectbox("Select a coach", sorted(masterlist["Coach/Consultant"].dropna().unique()))
        coach_teams = masterlist[masterlist["Coach/Consultant"] == selected_coach]
        
        # Get unique team names for this coach and their scores
        coach_team_names = coach_teams["Team Name"].unique()
        coach_team_scores = scores[scores["Team Name"].isin(coach_team_names)]
        
        st.write("**Team Scores for this coach:**")
        st.table(coach_team_scores[["Team Name", "Total_Score", "Total Event Attendance Bonus", "bonus"]])
        
        # Merge team member info with individual scores and team data
        coach_teams_with_team_scores = coach_teams.merge(scores, on="Team Name", how="left")
        
        # Merge with individual member scores
        if len(individual_scores) > 0:
            coach_teams_with_individual = coach_teams_with_team_scores.merge(
                individual_scores, 
                left_on=["Team Name", "Member Name"], 
                right_on=["Team", "Member Name"], 
                how="left"
            )
            coach_teams_with_individual["Points Earned"] = coach_teams_with_individual["Points Earned"].fillna(0)
            coach_teams_display = coach_teams_with_individual[["Team Name", "Total_Score", "Total_Member_Points", "Member Name", "Member Department", "Points Earned"]].sort_values(["Team Name", "Member Name"])
        else:
            # If individual scores unavailable, show 0 for all members
            coach_teams_display = coach_teams_with_team_scores[["Team Name", "Total_Score", "Total_Member_Points", "Member Name", "Member Department"]].sort_values(["Team Name", "Member Name"])
            coach_teams_display["Points Earned"] = 0
        
        # Display by teams option
        display_option = st.radio("Display format:", ["All Members", "Grouped by Teams"])
        
        if display_option == "Grouped by Teams":
            st.write("**Teams and Members:**")
            for team in sorted(coach_team_names):
                team_members = coach_teams_display[coach_teams_display["Team Name"] == team]
                team_score = team_members.iloc[0]["Total_Score"]
                team_member_points = team_members.iloc[0]["Total_Member_Points"]
                st.write(f"**{team}** (Team Score: {team_score}, Total Member Points: {team_member_points})")
                
                # Initialize variables with defaults
                coach_dept = "Coach"
                coach_points = 0
                
                # Get coach info and score for this team
                try:
                    if len(team_members) > 0 and "Member Department" in team_members.columns:
                        dept_value = team_members.iloc[0]["Member Department"]
                        if dept_value and str(dept_value) not in ['nan', 'None', '']:
                            coach_dept = str(dept_value)
                except Exception:
                    coach_dept = "Coach"
                
                try:
                    if len(individual_coach_scores) > 0 and selected_coach:
                        coach_all_scores = individual_coach_scores[individual_coach_scores["Coach Name"] == selected_coach]
                        if len(coach_all_scores) > 0:
                            coach_points = float(coach_all_scores["Points Earned"].sum())
                except Exception:
                    coach_points = 0
                
                # Create coach entry
                coach_entry = pd.DataFrame({
                    "Member Name": [selected_coach],
                    "Member Department": [coach_dept],
                    "Role": ["Coach"],
                    "Points Earned": [coach_points]
                })
                
                # Create member list with individual points and numbering
                members_list = team_members[["Member Name", "Member Department", "Points Earned"]].reset_index(drop=True)
                members_list["Role"] = "Team Member"
                
                # Handle dual-role scenario (coach who is also a team member)
                coach_is_member = selected_coach in members_list["Member Name"].values if selected_coach else False
                
                if coach_is_member:
                    # If coach is also a team member, update their role and combine their points
                    member_idx = members_list[members_list["Member Name"] == selected_coach].index[0]
                    member_points = members_list.loc[member_idx, "Points Earned"]
                    
                    # Update coach entry to show total points (coach + member)
                    coach_entry.loc[0, "Points Earned"] = coach_points + member_points
                    coach_entry.loc[0, "Role"] = "Coach & Team Member"
                    
                    # Remove the duplicate member entry
                    members_list = members_list.drop(member_idx).reset_index(drop=True)
                
                # Combine coach and members (coach first)
                combined_list = pd.concat([coach_entry, members_list], ignore_index=True)
                combined_list.index = combined_list.index + 1
                
                st.dataframe(combined_list, column_config={
                    "Member Name": st.column_config.Column("Name", width="medium"),
                    "Member Department": st.column_config.Column("Department", width="medium"),
                    "Role": st.column_config.Column("Role", width="small"),
                    "Points Earned": st.column_config.Column("Individual Points", width="small")
                })
        else:
            st.write("**All Members under this coach:**")
            
            # Initialize variable with default
            coach_total_points = 0
            
            # Get coach individual score across all teams
            try:
                if len(individual_coach_scores) > 0 and selected_coach:
                    coach_all_scores = individual_coach_scores[individual_coach_scores["Coach Name"] == selected_coach]
                    if len(coach_all_scores) > 0:
                        coach_total_points = float(coach_all_scores["Points Earned"].sum())
            except Exception:
                coach_total_points = 0
            
            # Create coach entry for all members view
            coach_entry = pd.DataFrame({
                "Team Name": ["Coach Total"],
                "Member Name": [selected_coach],
                "Member Department": ["Coach"],
                "Role": ["Coach"],
                "Points Earned": [coach_total_points]
            })
            
            # Show individual member points, not team scores
            clean_display = coach_teams_display[["Team Name", "Member Name", "Member Department", "Points Earned"]].reset_index(drop=True)
            clean_display["Role"] = "Team Member"
            
            # Handle dual-role scenario - add coach's member points to coach total
            if selected_coach in clean_display["Member Name"].values:
                member_rows = clean_display[clean_display["Member Name"] == selected_coach]
                member_total_points = member_rows["Points Earned"].sum()
                
                # Update coach entry to show combined points and indicate dual role
                coach_entry.loc[0, "Points Earned"] = coach_total_points + member_total_points
                coach_entry.loc[0, "Role"] = "Coach & Team Member"
                coach_entry.loc[0, "Team Name"] = "All Teams (Coach + Member)"
                
                # Remove duplicate member entries for the coach
                clean_display = clean_display[clean_display["Member Name"] != selected_coach].reset_index(drop=True)
            
            # Combine coach and members (coach first)
            combined_display = pd.concat([coach_entry, clean_display], ignore_index=True)
            combined_display.index = combined_display.index + 1
            
            st.dataframe(combined_display, column_config={
                "Team Name": st.column_config.Column("Team", width="medium"),
                "Member Name": st.column_config.Column("Name", width="medium"), 
                "Member Department": st.column_config.Column("Department", width="medium"),
                "Role": st.column_config.Column("Role", width="small"),
                "Points Earned": st.column_config.Column("Individual Points", width="small")
            })
        
        # CSV Export functionality
        st.write("**Export Data:**")
        export_option = st.selectbox("Select data to export:", 
                                   ["Team Scores Only", "All Member Details", "Selected Team Only"])
        
        if export_option == "Team Scores Only":
            export_data = coach_team_scores[["Team Name", "Total_Score", "Total Event Attendance Bonus", "bonus"]]
        elif export_option == "All Member Details":
            export_data = coach_teams_display
        else:  # Selected Team Only
            selected_team_export = st.selectbox("Select team to export:", sorted(coach_team_names))
            export_data = coach_teams_display[coach_teams_display["Team Name"] == selected_team_export]
        
        csv_data = export_data.to_csv(index=False)
        st.download_button(
            label=f"Download {export_option} as CSV",
            data=csv_data,
            file_name=f"{selected_coach}_{export_option.replace(' ', '_')}.csv",
            mime="text/csv"
        )

    with tab4:
        st.subheader("🔐 Admin Panel")
        password = st.text_input("Enter admin password", type="password")
        if password == ADMIN_PASSWORD:
            st.markdown("### Award Bonus Points")
            team_to_award = st.selectbox("Select team to award +1 bonus", scores["Team Name"].dropna().unique())
            if st.button("Award Bonus Point"):
                add_bonus_point(team_to_award)
                st.success(f"✅ Bonus point awarded to {team_to_award}")
                st.experimental_rerun()
            
            st.markdown("### Data Management")
            st.markdown("**Fix Data Issues:**")
            if st.button("Fix Duplicate Alliance Teams"):
                try:
                    if fix_duplicate_alliance_teams():
                        st.success("✅ Successfully fixed duplicate Alliance teams in Google Sheets")
                        st.info("🔄 Please refresh the page to see the updated data")
                        st.cache_data.clear()
                    else:
                        st.info("ℹ️ No duplicate Alliance teams found to fix")
                except Exception as e:
                    st.error(f"❌ Error fixing teams: {str(e)}")
            
            st.markdown("**Create Individual Attendance Data:**")
            if st.button("🏗️ Create Individual Attendance Worksheets"):
                try:
                    success, member_count, coach_count = create_individual_attendance_sheets()
                    if success:
                        st.success(f"✅ Successfully created individual attendance worksheets!")
                        st.info(f"📊 Created {member_count} member records and {coach_count} coach records")
                        st.warning("⚠️ Initial records use estimated attendance based on team counts. Please manually correct the attendance records in Google Sheets for accuracy.")
                        st.info("🔄 Refresh the page to load individual scores")
                        st.cache_data.clear()
                    else:
                        st.error("❌ Failed to create individual attendance worksheets")
                except Exception as e:
                    st.error(f"❌ Error creating worksheets: {str(e)}")
            
            st.markdown("**Update Event Data:**")
            st.write("**Add New Event Attendance:**")
            
            with st.expander("➕ Add New Tech Sharing Session"):
                new_event_name = st.text_input("Event Name (e.g., 'TechSharing4-NextJS')")
                
                if new_event_name:
                    st.write("**Team Attendance for New Event:**")
                    teams = scores["Team Name"].dropna().unique()
                    
                    # Create form for updating attendance
                    if st.button(f"📝 Open Attendance Form for {new_event_name}"):
                        st.info(f"""
                        **To add attendance for {new_event_name}:**
                        
                        1. **Update Team Scores Sheet:**
                           - Add new columns: `{new_event_name}_Members`, `{new_event_name}_Coaches`, `{new_event_name}_Score`
                           - Fill in attendance counts for each team
                        
                        2. **Update Individual Attendance Sheets:**
                           - Go to Member Attendance and Coach Attendance worksheets
                           - Add new rows for each person who attended {new_event_name}
                           - Set Session = '{new_event_name}', Points Earned = 1
                        
                        3. **Refresh Dashboard:**
                           - Come back here and refresh to see updated scores
                        """)
            
            st.write("**Bulk Update from Google Sheets:**")
            if st.button("🔄 Refresh Individual Scores from Sheets"):
                st.cache_data.clear()
                st.success("✅ Cache cleared - individual scores will be reloaded from Google Sheets")
                st.info("🔄 Refresh the page to see latest data")
            
            st.markdown("**Data Loading Status:**")
            st.write(f"Individual member scores loaded: {len(individual_scores)} records")
            st.write(f"Individual coach scores loaded: {len(individual_coach_scores)} records")
            if len(individual_scores) > 0:
                st.write(f"Teams with individual member data: {individual_scores['Team'].nunique()}")
            if len(individual_coach_scores) > 0:
                st.write(f"Teams with individual coach data: {individual_coach_scores['Team'].nunique()}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 Diagnose Google Sheets Access"):
                    permission_info = check_sheet_permissions()
                    
                    st.write(f"**Service Account Email:** `{permission_info['service_email']}`")
                    st.write("**Sheet Access Status:**")
                    
                    for result in permission_info['results']:
                        st.write(f"**{result['name']}**: {result['status']}")
                        if result['worksheets']:
                            st.write(f"Worksheets: {', '.join(result['worksheets'])}")
                            if result['name'] == 'Attendance Sheet':
                                st.write(f"• Has Member Attendance: {'✅' if result['has_member_attendance'] else '❌'}")
                                st.write(f"• Has Coach Attendance: {'✅' if result['has_coach_attendance'] else '❌'}")
                        
                        if '❌' in result['status']:
                            st.error(f"**TO FIX {result['name']}:**")
                            st.write(f"1. Open: {result['url']}")
                            st.write(f"2. Click 'Share' button")
                            st.write(f"3. Add email: `{permission_info['service_email']}`")
                            st.write("4. Set permission to 'Editor'")
                            st.write("5. Click 'Send'")
                        st.write("---")
            
            with col2:
                if st.button("📊 Show Sample Individual Scores"):
                    if len(individual_scores) > 0:
                        st.write("**Member Scores Sample:**")
                        st.dataframe(individual_scores.head(10))
                    if len(individual_coach_scores) > 0:
                        st.write("**Coach Scores Sample:**")
                        st.dataframe(individual_coach_scores.head(10))
                    if len(individual_scores) == 0 and len(individual_coach_scores) == 0:
                        st.error("**❌ No individual scores loaded**")
                        st.write("Click 'Diagnose Google Sheets Access' to see what needs to be fixed.")
            
            if st.button("🔧 Fix Alliance Team Name (Remove AJM)"):
                try:
                    import gspread
                    from google.oauth2.service_account import Credentials
                    
                    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
                    service_account_info = st.secrets["google"]
                    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
                    gc = gspread.authorize(credentials)
                    
                    MASTERLIST_SHEET_ID = "1u5i9s9Ty-jf-djMeAAzO1qOl_nk3_X3ICdfFfLGvLcc"
                    masterlist_sheet = gc.open_by_key(MASTERLIST_SHEET_ID)
                    worksheet = masterlist_sheet.sheet1
                    
                    # Get all data
                    all_values = worksheet.get_all_values()
                    
                    # Find and replace "Alliance of Just Minds(AJM)" with "Alliance of Just Minds"
                    changes_made = 0
                    for i, row in enumerate(all_values):
                        for j, cell in enumerate(row):
                            if "Alliance of Just Minds(AJM)" in cell:
                                new_value = cell.replace("Alliance of Just Minds(AJM)", "Alliance of Just Minds")
                                worksheet.update_cell(i + 1, j + 1, new_value)
                                changes_made += 1
                    
                    st.success(f"✅ Fixed {changes_made} cells in Google Sheets masterlist")
                    st.info("🔄 Please refresh the page to see updated data")
                    st.cache_data.clear()
                    
                except Exception as e:
                    st.error(f"❌ Error fixing team names: {str(e)}")
            
            if st.button("🔍 Check Actual Google Sheets Attendance Data"):
                try:
                    attendance, scores, masterlist = load_data()
                    
                    st.write("**Available worksheets in Attendance Sheet:**")
                    for sheet_name in attendance.keys():
                        st.write(f"- {sheet_name}")
                        if len(attendance[sheet_name]) > 0:
                            st.write(f"  Rows: {len(attendance[sheet_name])}")
                            st.write(f"  Columns: {list(attendance[sheet_name].columns)}")
                            st.write("  Sample data:")
                            st.dataframe(attendance[sheet_name].head(3))
                        else:
                            st.write("  (Empty)")
                        st.write("---")
                    
                    # Check attendance data completeness for ALL members
                    st.write("**Analyzing Individual Attendance Data Completeness:**")
                    
                    # Get all team members from masterlist
                    all_members = set(masterlist['Member Name'].dropna().unique())
                    st.write(f"Total members in masterlist: {len(all_members)}")
                    
                    # Check which members have individual attendance records
                    members_in_attendance = set()
                    for sheet_name, sheet_data in attendance.items():
                        if len(sheet_data) > 0 and 'Member Name' in sheet_data.columns:
                            members_in_attendance.update(sheet_data['Member Name'].dropna().unique())
                    
                    st.write(f"Members with individual attendance records: {len(members_in_attendance)}")
                    
                    # Find missing members
                    missing_members = all_members - members_in_attendance
                    if missing_members:
                        st.error(f"❌ {len(missing_members)} members have NO individual attendance records:")
                        st.write("This explains why they show incorrect scores - the system uses wrong 'first N members' logic instead of actual attendance.")
                        
                        # Show some examples
                        sample_missing = list(missing_members)[:10]
                        st.write("Examples of missing members:")
                        for member in sample_missing:
                            st.write(f"- {member}")
                        if len(missing_members) > 10:
                            st.write(f"... and {len(missing_members) - 10} more")
                    else:
                        st.success("✅ All members have individual attendance records!")
                    
                    # Check specific examples
                    st.write("**Sample Member Attendance Check:**")
                    test_members = ['Celine Keisja Nebrija', 'Jovan Beato', 'Anthony John Matiling']
                    for member in test_members:
                        found = False
                        for sheet_name, sheet_data in attendance.items():
                            if len(sheet_data) > 0 and 'Member Name' in sheet_data.columns:
                                member_data = sheet_data[sheet_data['Member Name'].str.contains(member.split()[0], na=False, case=False)]
                                if len(member_data) > 0:
                                    st.write(f"✅ {member}: Found {len(member_data)} attendance records")
                                    found = True
                                    break
                        if not found:
                            st.write(f"❌ {member}: NO attendance records found")
                        
                except Exception as e:
                    st.error(f"Error checking attendance data: {str(e)}")
            
            if st.button("🔧 Fix Missing Attendance Records"):
                try:
                    attendance, scores, masterlist = load_data()
                    
                    # Find members who should have attendance but don't
                    st.write("**Checking Alliance of Just Minds members specifically:**")
                    alliance_members = masterlist[masterlist['Team Name'].str.contains('Alliance', na=False)]
                    
                    for _, member_row in alliance_members.iterrows():
                        member_name = member_row['Member Name']
                        team_name = member_row['Team Name']
                        
                        # Check if this member has attendance records
                        found_attendance = False
                        total_points = 0
                        
                        for sheet_name, sheet_data in attendance.items():
                            if len(sheet_data) > 0 and 'Member Name' in sheet_data.columns:
                                member_records = sheet_data[sheet_data['Member Name'].str.contains(member_name.split()[0], na=False, case=False)]
                                if len(member_records) > 0:
                                    found_attendance = True
                                    if 'Points Earned' in member_records.columns:
                                        total_points = member_records['Points Earned'].sum()
                                    break
                        
                        status = f"✅ {total_points} points" if found_attendance else "❌ Missing"
                        st.write(f"- {member_name}: {status}")
                    
                    # According to your raw data, Alliance members should have:
                    # ADAM: 4 attended, N8N: 3 attended, Claude: 2 attended
                    alliance_attendance_data = [
                        {"name": "Jovan Beato", "sessions": ["ADAM", "N8N"]},  # First 2 sessions
                        {"name": "Anthony John Matiling", "sessions": ["ADAM", "N8N"]},  # First 2 sessions  
                        {"name": "Mariel Peñaflor", "sessions": ["ADAM"]},  # First session only
                        {"name": "Christopher Lizada", "sessions": ["ADAM"]},  # First session only
                        {"name": "Celine Keisja Nebrija", "sessions": ["ADAM", "N8N", "Claude"]},  # All 3 sessions per your check
                    ]
                    
                    st.write("**Expected attendance based on your raw data verification:**")
                    for member_data in alliance_attendance_data:
                        sessions_str = ", ".join(member_data["sessions"])
                        points = len(member_data["sessions"])
                        st.write(f"- {member_data['name']}: {sessions_str} = {points} points")
                    
                    if st.button("📝 Update Alliance Attendance Records"):
                        try:
                            import gspread
                            from google.oauth2.service_account import Credentials
                            
                            SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
                            service_account_info = st.secrets["google"]
                            credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
                            gc = gspread.authorize(credentials)
                            
                            ATTENDANCE_SHEET_ID = "1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8"
                            attendance_sheet = gc.open_by_key(ATTENDANCE_SHEET_ID)
                            
                            # Find the Member Attendance worksheet
                            member_ws = None
                            for ws in attendance_sheet.worksheets():
                                if 'member' in ws.title.lower() and 'attendance' in ws.title.lower():
                                    member_ws = ws
                                    break
                            
                            if member_ws:
                                # Get all attendance data
                                all_records = member_ws.get_all_records()
                                
                                # Update Celine's records specifically
                                updates_made = 0
                                for i, record in enumerate(all_records):
                                    if 'Celine' in str(record.get('Member Name', '')):
                                        # Update her points to 1 for each session she attended
                                        row_num = i + 2  # +2 because headers are row 1, records start at row 2
                                        
                                        # Set Points Earned to 1 if it's currently 0
                                        current_points = record.get('Points Earned', 0)
                                        if current_points == 0:
                                            member_ws.update_cell(row_num, member_ws.find('Points Earned').col, 1)
                                            updates_made += 1
                                
                                st.success(f"✅ Updated {updates_made} records for Celine")
                                st.info("🔄 Please refresh the page to see updated scores")
                                st.cache_data.clear()
                                
                            else:
                                st.error("❌ Could not find Member Attendance worksheet")
                                
                        except Exception as e:
                            st.error(f"❌ Error updating attendance: {str(e)}")
                        
                except Exception as e:
                    st.error(f"Error checking attendance: {str(e)}")
            
            if st.button("🔍 Explore All Sheets for Individual Data"):
                try:
                    import gspread
                    from google.oauth2.service_account import Credentials
                                
                    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
                    service_account_info = st.secrets["google"]
                    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
                    gc = gspread.authorize(credentials)
                    
                    sheets_to_explore = [
                        {"id": "1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8", "name": "Attendance Sheet"},
                        {"id": "1xGVH2TDV4at_WmNnaMDtjYbQPTAAUffd04bejme1Gxo", "name": "Scores Sheet"},
                        {"id": "1u5i9s9Ty-jf-djMeAAzO1qOl_nk3_X3ICdfFfLGvLcc", "name": "Masterlist Sheet"},
                    ]
                    
                    for sheet_info in sheets_to_explore:
                        try:
                            st.write(f"## 📋 {sheet_info['name']}")
                            sheet = gc.open_by_key(sheet_info["id"])
                            
                            for ws in sheet.worksheets():
                                st.write(f"**Worksheet: {ws.title}**")
                                try:
                                    # Get first few rows to understand structure
                                    data = ws.get_all_records()
                                    if len(data) > 0:
                                        df = pd.DataFrame(data)
                                        st.write(f"Rows: {len(df)}, Columns: {len(df.columns)}")
                                        st.write(f"Column names: {df.columns.tolist()}")
                                        
                                        # Check if this looks like individual member or coach data
                                        has_individual_member = any('member name' in col.lower() for col in df.columns)
                                        has_individual_coach = any('coach name' in col.lower() for col in df.columns)
                                        has_points_earned = any('points earned' in col.lower() for col in df.columns)
                                        has_session = any('session' in col.lower() for col in df.columns)
                                        has_attendance_data = has_individual_member or has_individual_coach
                                        
                                        st.write(f"**Data Type Analysis:**")
                                        if has_attendance_data and has_points_earned:
                                            st.success("🎯 This looks like INDIVIDUAL attendance data!")
                                        elif 'Total_' in str(df.columns):
                                            st.info("📊 This looks like AGGREGATED team data")
                                        else:
                                            st.write("🔍 Unknown data type")
                                        
                                        st.write(f"• Individual member names: {'✅' if has_individual_member else '❌'}")
                                        st.write(f"• Individual coach names: {'✅' if has_individual_coach else '❌'}")
                                        st.write(f"• Points earned: {'✅' if has_points_earned else '❌'}")
                                        st.write(f"• Session data: {'✅' if has_session else '❌'}")
                                        
                                        if has_attendance_data:
                                            st.write("Sample data:")
                                            st.dataframe(df.head(3))
                                    else:
                                        st.write("No data found in this worksheet")
                                except Exception as e:
                                    st.error(f"Error reading {ws.title}: {str(e)}")
                                st.write("---")
                        except Exception as e:
                            st.error(f"Error accessing {sheet_info['name']}: {str(e)}")
                        st.write("=" * 50)
                        
                except Exception as e:
                    st.error(f"Error exploring sheets: {str(e)}")
            
        else:
            st.info("Enter the correct password to access admin features.")

if __name__ == "__main__":
    main()

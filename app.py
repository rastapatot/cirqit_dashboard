
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

@st.cache_data
def get_individual_member_scores():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        import pandas as pd
        
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        service_account_info = st.secrets["google"]
        credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        
        ATTENDANCE_SHEET_ID = "1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8"
        attendance_sheet = gc.open_by_key(ATTENDANCE_SHEET_ID)
        
        # Get Member Attendance worksheet
        member_attendance_ws = None
        for ws in attendance_sheet.worksheets():
            if 'member' in ws.title.lower() and 'attendance' in ws.title.lower():
                member_attendance_ws = ws
                break
        
        if member_attendance_ws:
            member_data = pd.DataFrame(member_attendance_ws.get_all_records())
            if len(member_data) > 0 and 'Points Earned' in member_data.columns:
                # Calculate individual member scores
                individual_scores = member_data.groupby(['Team', 'Member Name'])['Points Earned'].sum().reset_index()
                return individual_scores
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading individual member scores: {str(e)}")
        return pd.DataFrame()

@st.cache_data  
def get_individual_coach_scores():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        import pandas as pd
        
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        service_account_info = st.secrets["google"]
        credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        
        ATTENDANCE_SHEET_ID = "1YGWzH7WN322uCBwbmAZl_Rcn9SzuhzaO8XOI3cD_QG8"
        attendance_sheet = gc.open_by_key(ATTENDANCE_SHEET_ID)
        
        # Get Coach Attendance worksheet
        coach_attendance_ws = None
        for ws in attendance_sheet.worksheets():
            if 'coach' in ws.title.lower() and 'attendance' in ws.title.lower():
                coach_attendance_ws = ws
                break
        
        if coach_attendance_ws:
            coach_data = pd.DataFrame(coach_attendance_ws.get_all_records())
            if len(coach_data) > 0 and 'Points Earned' in coach_data.columns:
                # Calculate individual coach scores
                individual_coach_scores = coach_data.groupby(['Team', 'Coach Name'])['Points Earned'].sum().reset_index()
                return individual_coach_scores
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading individual coach scores: {str(e)}")
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
    scores["Total Event Attendance Bonus"] = scores["Total_Member_Points"] + scores["Total_Coach_Points"]
    scores["Total_with_Bonus"] = scores["Total_Score"] + scores["bonus"]

    
    tab1, tab2, tab3, tab4 = st.tabs(["Team Performance Overview", "Team Explorer", "Coach Explorer", "Admin Panel"])

    with tab1:
        st.subheader("📊 Team Performance Overview")
        teams_display = scores[["Team Name", "Total_Score", "Total Event Attendance Bonus", "bonus", "Average_Score", "Member_Attendance_Rate", "Coach_Attendance_Rate"]].reset_index(drop=True)
        teams_display.index = teams_display.index + 1
        st.dataframe(teams_display)

    with tab2:
        st.subheader("🔍 Team Explorer")
        selected_team = st.selectbox("Select a team", sorted(scores["Team Name"].dropna().unique()))
        team_info = masterlist[masterlist["Team Name"] == selected_team]
        team_score = scores[scores["Team Name"] == selected_team]["Total_Score"].iloc[0]
        team_bonus = scores[scores["Team Name"] == selected_team]["bonus"].iloc[0]
        team_total = scores[scores["Team Name"] == selected_team]["Total_with_Bonus"].iloc[0]
        team_attendance_bonus = scores[scores["Team Name"] == selected_team]["Total Event Attendance Bonus"].iloc[0]
        
        st.write(f"**Team Score:** {team_score} (Base) + {team_attendance_bonus} (Attendance) + {team_bonus} (Bonus) = {team_total} (Total)")
        st.write("**Team Members:**")
        
        # Get coach info and score
        coach_name = team_info["Coach/Consultant"].iloc[0]
        coach_dept = team_info["Coach Department"].iloc[0] if "Coach Department" in team_info.columns else "Coach"
        
        # Get coach individual score
        coach_points = 0
        if len(individual_coach_scores) > 0:
            coach_score_data = individual_coach_scores[
                (individual_coach_scores["Team"] == selected_team) & 
                (individual_coach_scores["Coach Name"] == coach_name)
            ]
            if len(coach_score_data) > 0:
                coach_points = coach_score_data.iloc[0]["Points Earned"]
        
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
            # Fallback if individual scores unavailable  
            team_members_display = team_info_with_team_scores[["Member Name", "Member Department"]].sort_values("Member Name").reset_index(drop=True)
            team_members_display["Points Earned"] = 0
            st.warning("⚠️ Individual member scores unavailable - showing 0 for all members")
        
        # Add Role column for team members
        team_members_display["Role"] = "Team Member"
        
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
            # Fallback if individual scores unavailable
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
                
                # Get coach info and score for this team
                coach_dept = team_members.iloc[0]["Member Department"] if len(team_members) > 0 else "Coach"
                coach_points = 0
                if len(individual_coach_scores) > 0:
                    coach_score_data = individual_coach_scores[
                        (individual_coach_scores["Team"] == team) & 
                        (individual_coach_scores["Coach Name"] == selected_coach)
                    ]
                    if len(coach_score_data) > 0:
                        coach_points = coach_score_data.iloc[0]["Points Earned"]
                
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
            
            # Get coach individual score across all teams
            coach_total_points = 0
            if len(individual_coach_scores) > 0:
                coach_all_scores = individual_coach_scores[individual_coach_scores["Coach Name"] == selected_coach]
                if len(coach_all_scores) > 0:
                    coach_total_points = coach_all_scores["Points Earned"].sum()
            
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
            
            st.markdown("**Update Event Data:**")
            st.info("📝 Event attendance update functionality can be added here for future events")
            
            st.markdown("**Data Loading Status:**")
            st.write(f"Individual member scores loaded: {len(individual_scores)} records")
            st.write(f"Individual coach scores loaded: {len(individual_coach_scores)} records")
            if len(individual_scores) > 0:
                st.write(f"Teams with individual data: {individual_scores['Team'].nunique()}")
            if st.button("Show Sample Individual Scores"):
                if len(individual_scores) > 0:
                    st.dataframe(individual_scores.head(10))
                else:
                    st.error("No individual scores loaded")
            
        else:
            st.info("Enter the correct password to access admin features.")

if __name__ == "__main__":
    main()

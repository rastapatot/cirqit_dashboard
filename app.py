
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

@st.cache_data
def load_data():
    import gspread
    from google.oauth2.service_account import Credentials

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
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
def main():
    st.set_page_config("CirQit Hackathon Dashboard", layout="wide")
    
    # Display logo and title
    col1, col2 = st.columns([1, 6])
    with col1:
        st.image("CirQit_Logo.png", width=80)
    with col2:
        st.markdown("<h1 style='margin-top: 15px; margin-left: -20px;'>CirQit Hackathon Dashboard</h1>", unsafe_allow_html=True)

    init_db()
    attendance, scores, masterlist = load_data()
    
    ensure_teams_in_db(scores["Team Name"].dropna().unique())
    bonus_df = get_bonus_points()

    scores = scores.merge(bonus_df, how="left", left_on="Team Name", right_on="team_name")
    scores["bonus"] = scores["bonus"].fillna(0)
    scores["Total Event Attendance Bonus"] = scores["Total_Member_Points"] + scores["Total_Coach_Points"]
    scores["Total_with_Bonus"] = scores["Total_Score"] + scores["bonus"]

    
    tab1, tab2, tab3, tab4 = st.tabs(["Team Performance Overview", "Team Explorer", "Coach Explorer", "Admin Panel"])

    with tab1:
        st.subheader("📊 Team Performance Overview")
        st.dataframe(scores[["Team Name", "Total_Score", "Total Event Attendance Bonus", "bonus", "Average_Score", "Member_Attendance_Rate", "Coach_Attendance_Rate"]])

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
        # Merge team member info with their individual scores
        team_info_with_scores = team_info.merge(scores, on="Team Name", how="left")
        team_members_display = team_info_with_scores[["Member Name", "Member Department", "Total_Member_Points"]].sort_values("Member Name")
        st.dataframe(team_members_display, 
                    column_config={
                        "Member Name": st.column_config.Column("Member Name", width="medium"),
                        "Member Department": st.column_config.Column("Member Department", width="medium"),
                        "Total_Member_Points": st.column_config.Column("Points", width="small")
                    },
                    hide_index=True)
        st.write("**Coach:**", team_info["Coach/Consultant"].iloc[0])

    with tab3:
        st.subheader("🎓 Coach Explorer")
        selected_coach = st.selectbox("Select a coach", sorted(masterlist["Coach/Consultant"].dropna().unique()))
        coach_teams = masterlist[masterlist["Coach/Consultant"] == selected_coach]
        
        # Get unique team names for this coach and their scores
        coach_team_names = coach_teams["Team Name"].unique()
        coach_team_scores = scores[scores["Team Name"].isin(coach_team_names)]
        
        st.write("**Team Scores for this coach:**")
        st.table(coach_team_scores[["Team Name", "Total_Score", "Total Event Attendance Bonus", "bonus"]])
        
        # Merge team member info with their individual scores
        coach_teams_with_scores = coach_teams.merge(scores, on="Team Name", how="left")
        coach_teams_display = coach_teams_with_scores[["Team Name", "Total_Member_Points", "Member Name", "Member Department"]].sort_values(["Team Name", "Member Name"])
        
        # Display by teams option
        display_option = st.radio("Display format:", ["All Members", "Grouped by Teams"])
        
        if display_option == "Grouped by Teams":
            st.write("**Teams and Members:**")
            for team in sorted(coach_team_names):
                team_members = coach_teams_display[coach_teams_display["Team Name"] == team]
                st.write(f"**{team}**")
                st.table(team_members[["Total_Member_Points", "Member Name", "Member Department"]])
        else:
            st.write("**All Members under this coach:**")
            st.table(coach_teams_display)
        
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
        st.subheader("🔐 Admin Panel: Award Bonus Points")
        password = st.text_input("Enter admin password", type="password")
        if password == ADMIN_PASSWORD:
            team_to_award = st.selectbox("Select team to award +1 bonus", scores["Team Name"].dropna().unique())
            if st.button("Award Bonus Point"):
                add_bonus_point(team_to_award)
                st.success(f"✅ Bonus point awarded to {team_to_award}")
                st.experimental_rerun()
        else:
            st.info("Enter the correct password to access admin features.")

if __name__ == "__main__":
    main()

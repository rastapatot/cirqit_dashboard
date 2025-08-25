
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
st.title("🚀 CirQit Hackathon Dashboard")

init_db()
attendance, scores, masterlist = load_data()
ensure_teams_in_db(scores["Team Name"].dropna().unique())
bonus_df = get_bonus_points()

scores = scores.merge(bonus_df, how="left", left_on="Team Name", right_on="team_name")
scores.rename(columns={"bonus": "Bonus_Points", "Average_Score": "Average_Score_Per_Event"}, inplace=True)

st.subheader("📊 Team Performance Overview")
st.dataframe(scores[["Team Name", "Total_Score", "bonus", "Average_Score", "Member_Attendance_Rate", "Coach_Attendance_Rate"]])

st.subheader("🔍 Team Explorer")
selected_team = st.selectbox("Select a team", scores["Team Name"].dropna().unique())
team_info = masterlist[masterlist["Team Name"] == selected_team]
st.write("**Team Members:**")
st.table(team_info[["Member Name", "Member Department"]])
st.write("**Coach:**", team_info["Coach/Consultant"].iloc[0])



st.subheader("🔍 Coach Search")
search_coach = st.text_input("Search for a coach by name")
if search_coach:
    coach_teams = masterlist[masterlist["Coach/Consultant"].str.contains(search_coach, case=False, na=False)]
    coach_team_names = coach_teams["Team Name"].dropna().unique()
    coach_scores = scores[scores["Team Name"].isin(coach_team_names)]
    st.write(f"**Performance Summary for Coach: {search_coach}**")
    st.dataframe(coach_scores[["Team Name", "Total_Score", "Bonus_Points", "Average_Score_Per_Event", "Member_Attendance_Rate", "Coach_Attendance_Rate"]])

    with st.expander("🔐 Admin Panel: Award Bonus Points"):
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

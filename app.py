
import streamlit as st
import pandas as pd
import sqlite3

ADMIN_PASSWORD = "vincent123"
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
    attendance = pd.read_excel("CirQit-TC-Attendance-AsOf-2025-08-23.xlsx", sheet_name=None, engine="openpyxl")
    scores = pd.read_csv("CirQit-TC-TeamScores-AsOf-2025-08-23.csv")
    masterlist = pd.read_csv("teams-masterlist.csv", encoding="ISO-8859-1")
    return attendance, scores, masterlist

def main():
    st.set_page_config("CirQit Hackathon Dashboard", layout="wide")
    st.title("🚀 CirQit Hackathon Dashboard")

    init_db()
    attendance, scores, masterlist = load_data()
    ensure_teams_in_db(scores["Team Name"].dropna().unique())
    bonus_df = get_bonus_points()

    scores = scores.merge(bonus_df, how="left", left_on="Team Name", right_on="team_name")
    scores["Total Score (with Bonus)"] = scores["Total_Score"] + scores["bonus"]

    st.subheader("📊 Team Performance Overview")
    st.dataframe(scores[["Team Name", "Total_Score", "bonus", "Total Score (with Bonus)", "Average_Score", "Member_Attendance_Rate", "Coach_Attendance_Rate"]])

    st.subheader("🔍 Team Explorer")
    selected_team = st.selectbox("Select a team", scores["Team Name"].dropna().unique())
    team_info = masterlist[masterlist["Team Name"] == selected_team]
    st.write("**Team Members:**")
    st.table(team_info[["Member Name", "Member Department"]])
    st.write("**Coach:**", team_info["Coach/Consultant"].iloc[0])

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

    with st.expander("📤 Upload New Attendance Data"):
        uploaded_file = st.file_uploader("Upload updated attendance Excel file", type=["xlsx"])
        if uploaded_file:
            with open("CirQit-TC-Attendance-AsOf-2025-08-23.xlsx", "wb") as f:
                f.write(uploaded_file.read())
            st.success("✅ File uploaded. Please refresh the page to see updated data.")

if __name__ == "__main__":
    main()

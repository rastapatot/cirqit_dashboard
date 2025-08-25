import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

ADMIN_PASSWORD = "cirqit2024"  # Hardcoded password for Streamlit Cloud
DB_FILE = "cirqit_dashboard.db"

def init_db():
    """Initialize database with new schema if needed"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if new tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='teams'")
    if not cursor.fetchone():
        # New schema doesn't exist, keep legacy system but add option to migrate
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bonus_points (
                team_name TEXT PRIMARY KEY,
                bonus INTEGER DEFAULT 0
            )
        """)
    
    conn.commit()
    conn.close()

@st.cache_data
def load_data_from_database():
    """Load data from the new database system"""
    conn = sqlite3.connect(DB_FILE)
    
    try:
        # Check if new tables exist
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='teams'")
        if cursor.fetchone():
            # Use new database system
            team_scores_df = pd.read_sql_query("SELECT * FROM team_scores ORDER BY final_score DESC", conn)
            individual_scores_df = pd.read_sql_query("SELECT * FROM individual_member_scores", conn)
            
            conn.close()
            return team_scores_df, individual_scores_df, True
        else:
            conn.close()
            return None, None, False
    except Exception:
        conn.close()
        return None, None, False

@st.cache_data  
def load_legacy_data():
    """Load data from CSV files (legacy system)"""
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

def migrate_to_new_system():
    """Execute the migration to the new database system"""
    try:
        import subprocess
        result = subprocess.run(['python3', 'migrate_to_new_scoring_system.py'], 
                              capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def add_new_event(event_name, event_date, member_points=1, coach_points=2):
    """Add a new event to the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO events (name, type, date_held, member_points_per_attendance, coach_points_per_attendance) VALUES (?, ?, ?, ?, ?)',
        (event_name, 'tech_sharing', event_date, member_points, coach_points)
    )
    
    conn.commit()
    conn.close()
    st.cache_data.clear()

def record_attendance(event_id, member_attendances, coach_attendances):
    """Record attendance for an event"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Record member attendances
    for member_id, attended in member_attendances.items():
        points = 1 if attended else 0  # Get from event settings
        cursor.execute(
            'INSERT INTO attendance (member_id, event_id, attended, points_earned, session_type) VALUES (?, ?, ?, ?, ?)',
            (member_id, event_id, attended, points, 'day')
        )
    
    # Record coach attendances  
    for coach_name, sessions_attended in coach_attendances.items():
        if sessions_attended > 0:
            cursor.execute(
                'INSERT INTO attendance (coach_name, event_id, attended, points_earned, session_type) VALUES (?, ?, ?, ?, ?)',
                (coach_name, event_id, True, sessions_attended * 2, 'day')
            )
    
    conn.commit()
    conn.close()
    st.cache_data.clear()

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
    
    # Try to load from new database system first
    team_scores_df, individual_scores_df, using_new_system = load_data_from_database()
    
    if not using_new_system:
        # Fall back to legacy system
        st.warning("⚠️ Using legacy CSV-based scoring system. Migrate to database for accurate individual tracking.")
        attendance, scores, masterlist = load_legacy_data()
        
        # Convert legacy data to display format (simplified version)
        team_scores_df = scores.copy()
        team_scores_df = team_scores_df.sort_values("Total_Score", ascending=False)
        individual_scores_df = pd.DataFrame()  # Empty for legacy
    
    st.sidebar.markdown("### System Status")
    if using_new_system:
        st.sidebar.success("✅ Database System Active")
        st.sidebar.info(f"Teams: {len(team_scores_df)}")
        st.sidebar.info(f"Individual Records: {len(individual_scores_df)}")
    else:
        st.sidebar.warning("⚠️ Legacy CSV System")
        st.sidebar.error("Individual scoring may be inaccurate")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Team Performance Overview", "Team Explorer", "Coach Explorer", "Admin Panel"])

    with tab1:
        st.subheader("📊 Team Performance Overview")
        
        if using_new_system:
            # Use accurate database scores
            display_cols = ['team_name', 'base_score', 'total_bonus_points', 'final_score', 'member_attendance_rate']
            display_df = team_scores_df[display_cols].copy()
            display_df.columns = ['Team Name', 'Base Score', 'Bonus Points', 'Final Score', 'Attendance Rate']
            display_df['Attendance Rate'] = display_df['Attendance Rate'].astype(str) + '%'
        else:
            # Use legacy CSV display
            display_df = team_scores_df[["Team Name", "Total_Score", "bonus", "Total_with_Bonus", "Member_Attendance_Rate"]].copy()
            display_df.columns = ['Team Name', 'Base Score', 'Bonus Points', 'Final Score', 'Attendance Rate']
        
        display_df.index = range(1, len(display_df) + 1)
        st.dataframe(display_df)

    with tab2:
        st.subheader("🔍 Team Explorer")
        
        if using_new_system:
            team_names = team_scores_df['team_name'].tolist()
        else:
            team_names = team_scores_df['Team Name'].tolist()
        
        selected_team = st.selectbox("Select a team", team_names)
        
        if using_new_system:
            # Show accurate individual scores
            team_info = team_scores_df[team_scores_df['team_name'] == selected_team].iloc[0]
            team_members = individual_scores_df[individual_scores_df['team_name'] == selected_team]
            
            st.write(f"**Team Score:** {team_info['base_score']} (Base) + {team_info['total_bonus_points']} (Bonus) = {team_info['final_score']} (Total)")
            st.write(f"**Attendance Rate:** {team_info['member_attendance_rate']}%")
            
            if len(team_members) > 0:
                member_display = team_members[['member_name', 'department', 'total_points', 'events_attended']].copy()
                member_display.columns = ['Member Name', 'Department', 'Total Points', 'Events Attended']
                member_display = member_display.sort_values('Total Points', ascending=False)
                member_display.index = range(1, len(member_display) + 1)
                st.dataframe(member_display)
            else:
                st.info("No individual member data available for this team")
        else:
            st.warning("⚠️ Individual member scores may be inaccurate in legacy mode. Please migrate to database system.")
            # Show legacy team info (simplified)
            team_info = team_scores_df[team_scores_df['Team Name'] == selected_team].iloc[0]
            st.write(f"**Team Score:** {team_info['Total_Score']}")

    with tab3:
        st.subheader("🎓 Coach Explorer")
        st.info("Coach explorer functionality available after migration to database system.")

    with tab4:
        st.subheader("🔐 Admin Panel")
        password = st.text_input("Enter admin password", type="password")
        
        if password == ADMIN_PASSWORD:
            if not using_new_system:
                st.markdown("### 🚀 Migrate to Accurate Database System")
                st.warning("**Current Issues with CSV System:**")
                st.write("- Inaccurate individual scoring (5th member problem)")
                st.write("- Inconsistent data between tabs")
                st.write("- Manual data entry prone to errors")
                st.write("- No individual attendance tracking")
                
                st.success("**New Database System Benefits:**")
                st.write("✅ Accurate individual member attendance")
                st.write("✅ Consistent scoring across all tabs") 
                st.write("✅ Easy addition of new events")
                st.write("✅ Detailed reporting capabilities")
                st.write("✅ Data integrity and validation")
                
                if st.button("🔄 Migrate to Database System"):
                    with st.spinner("Migrating data... This may take a moment."):
                        success, stdout, stderr = migrate_to_new_system()
                    
                    if success:
                        st.success("✅ Migration completed successfully!")
                        st.info("Please refresh the page to use the new system.")
                        st.code(stdout)
                        st.cache_data.clear()
                    else:
                        st.error("❌ Migration failed:")
                        st.code(stderr)
            else:
                st.success("✅ Using accurate database system!")
                
                st.markdown("### 📊 Add New Event")
                with st.form("add_event"):
                    event_name = st.text_input("Event Name (e.g., 'TechSharing4-NextJS')")
                    event_date = st.date_input("Event Date", datetime.now().date())
                    member_points = st.number_input("Points per member attendance", value=1, min_value=0)
                    coach_points = st.number_input("Points per coach attendance", value=2, min_value=0)
                    
                    if st.form_submit_button("Add Event"):
                        add_new_event(event_name, event_date, member_points, coach_points)
                        st.success(f"✅ Event '{event_name}' added!")
                        st.cache_data.clear()
                
                st.markdown("### 👥 Record Attendance")
                st.info("Use this section to record actual attendance for events")
                
                # Get events for attendance recording
                conn = sqlite3.connect(DB_FILE)
                events_df = pd.read_sql_query("SELECT id, name, date_held FROM events ORDER BY date_held DESC", conn)
                conn.close()
                
                if len(events_df) > 0:
                    selected_event = st.selectbox("Select Event", 
                                                 events_df['name'].tolist(),
                                                 format_func=lambda x: f"{x} ({events_df[events_df['name']==x]['date_held'].iloc[0]})")
                    
                    if st.button("Record Attendance for Selected Event"):
                        st.info(f"Attendance recording interface for '{selected_event}' would appear here")
                        st.write("This would show checkboxes for each team member and coach to mark attendance.")

        else:
            st.info("Enter the correct password to access admin features.")

if __name__ == "__main__":
    main()
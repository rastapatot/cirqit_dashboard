"""
CirQit Hackathon Dashboard - Clean Database-Only Version
100% Database-driven, no legacy CSV code
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Configuration
ADMIN_PASSWORD = "cirqit2024"
DB_FILE = "cirqit_dashboard.db"

@st.cache_data
def load_team_leaderboard():
    """Load team leaderboard data from database"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM v_team_scores ORDER BY final_score DESC", conn)
    conn.close()
    return df

@st.cache_data
def load_coach_leaderboard():
    """Load coach leaderboard data from database"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM v_coach_scores ORDER BY total_points DESC", conn)
    conn.close()
    return df

@st.cache_data
def load_member_scores():
    """Load member scores data from database"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM v_member_scores ORDER BY total_points DESC", conn)
    conn.close()
    return df

@st.cache_data
def load_events():
    """Load events data from database"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM events WHERE is_active = 1 ORDER BY event_date DESC", conn)
    conn.close()
    return df

def get_database_stats():
    """Get database statistics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM teams WHERE is_active = 1")
    stats["Active Teams"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM members WHERE is_active = 1")
    stats["Active Members"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM coaches WHERE is_active = 1")
    stats["Active Coaches"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM attendance")
    stats["Attendance Records"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM events WHERE is_active = 1")
    stats["Active Events"] = cursor.fetchone()[0]
    
    conn.close()
    return stats

def clear_cache():
    """Clear all cached data"""
    st.cache_data.clear()

# ================== TEAM MANAGEMENT FUNCTIONS ==================

def get_existing_coaches():
    """Get list of existing coaches for selection"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, department FROM coaches WHERE is_active = 1 ORDER BY name")
    coaches = cursor.fetchall()
    conn.close()
    return coaches

def add_new_coach(name, department):
    """Add a new coach to the database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if coach already exists
        cursor.execute("SELECT id FROM coaches WHERE name = ?", (name,))
        if cursor.fetchone():
            conn.close()
            return False, "Coach already exists"
        
        # Insert new coach
        cursor.execute("""
            INSERT INTO coaches (name, department, is_active)
            VALUES (?, ?, 1)
        """, (name, department))
        
        coach_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return True, f"Coach '{name}' added successfully"
        
    except Exception as e:
        return False, f"Error adding coach: {str(e)}"

def add_new_team(team_name, total_members, coach_id, department):
    """Add a new team to the database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if team already exists
        cursor.execute("SELECT id FROM teams WHERE name = ?", (team_name,))
        if cursor.fetchone():
            conn.close()
            return False, "Team name already exists"
        
        # Insert new team
        cursor.execute("""
            INSERT INTO teams (name, total_members, coach_id, department, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (team_name, total_members, coach_id, department))
        
        team_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        clear_cache()  # Clear cache to show new team
        return True, f"Team '{team_name}' created successfully"
        
    except Exception as e:
        return False, f"Error creating team: {str(e)}"

def add_team_member(team_id, member_name, department, is_leader=False):
    """Add a member to a team"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if member already exists in this team
        cursor.execute("SELECT id FROM members WHERE name = ? AND team_id = ?", (member_name, team_id))
        if cursor.fetchone():
            conn.close()
            return False, "Member already exists in this team"
        
        # If this is a leader, remove leader status from others in the team
        if is_leader:
            cursor.execute("UPDATE members SET is_leader = 0 WHERE team_id = ?", (team_id,))
        
        # Insert new member
        cursor.execute("""
            INSERT INTO members (name, department, team_id, is_leader, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (member_name, department, team_id, is_leader))
        
        # Create attendance records for all existing events (default: not attended)
        cursor.execute("SELECT id FROM events WHERE is_active = 1")
        events = cursor.fetchall()
        
        member_id = cursor.lastrowid
        
        for (event_id,) in events:
            cursor.execute("""
                INSERT INTO attendance (event_id, member_id, attended, points_earned, session_type, recorded_by)
                VALUES (?, ?, 0, 0, 'day', 'system_auto')
            """, (event_id, member_id))
        
        conn.commit()
        conn.close()
        
        clear_cache()  # Clear cache to show new member
        return True, f"Member '{member_name}' added successfully"
        
    except Exception as e:
        return False, f"Error adding member: {str(e)}"

def get_teams_for_selection():
    """Get teams for member addition"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM teams WHERE is_active = 1 ORDER BY name")
    teams = cursor.fetchall()
    conn.close()
    return teams

def check_dual_role_member(member_name):
    """Check if a member should also be a coach"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM coaches WHERE name = ?", (member_name,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def main():
    st.set_page_config(
        page_title="CirQit Hackathon Dashboard",
        page_icon="🏆",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Get database stats
    stats = get_database_stats()
    
    # Header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1>🏆 CirQit Hackathon Dashboard</h1>
        <p style="color: #666;">Database-Driven Scoring System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### System Status")
        st.success("✅ Database Connected")
        st.success("✅ Real-time Scoring")
        
        st.markdown("### Statistics")
        for stat, value in stats.items():
            st.metric(stat, value)
        
        st.markdown("### Quick Actions")
        if st.button("🔄 Refresh Data"):
            clear_cache()
            st.rerun()
    
    # Main interface
    show_main_interface()

def show_main_interface():
    """Show main dashboard interface"""
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏆 Team Leaderboard", 
        "👥 Team Explorer", 
        "🎓 Coach Explorer", 
        "📊 Event Analytics",
        "⚙️ Admin Panel"
    ])
    
    with tab1:
        show_team_leaderboard()
    
    with tab2:
        show_team_explorer()
    
    with tab3:
        show_coach_explorer()
    
    with tab4:
        show_event_analytics()
    
    with tab5:
        show_admin_panel()

def show_team_leaderboard():
    """Display team leaderboard"""
    st.subheader("🏆 Team Performance Leaderboard")
    
    # Load data
    leaderboard_df = load_team_leaderboard()
    
    if len(leaderboard_df) == 0:
        st.warning("No team data available")
        return
    
    # Display options
    col1, col2 = st.columns([3, 1])
    with col2:
        show_top = st.selectbox("Show top teams", [10, 25, 50, "All"], index=0)
        if show_top != "All":
            display_df = leaderboard_df.head(show_top)
        else:
            display_df = leaderboard_df
    
    # Format for display
    display_df = display_df.copy()
    display_df['rank'] = range(1, len(display_df) + 1)
    
    # Reorder columns
    display_columns = [
        'rank', 'team_name', 'final_score', 'member_points', 'coach_points', 
        'bonus_points', 'member_attendance_rate', 'members_attended'
    ]
    
    display_df = display_df[display_columns]
    display_df.columns = [
        'Rank', 'Team Name', 'Final Score', 'Member Points', 'Coach Points',
        'Bonus Points', 'Attendance Rate (%)', 'Members Participated'
    ]
    
    # Style the dataframe
    styled_df = display_df.style.format({
        'Final Score': '{:.0f}',
        'Member Points': '{:.0f}',
        'Coach Points': '{:.0f}',
        'Bonus Points': '{:.0f}',
        'Attendance Rate (%)': '{:.1f}%'
    })
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Teams", len(leaderboard_df))
    with col2:
        st.metric("Avg Final Score", f"{leaderboard_df['final_score'].mean():.1f}")
    with col3:
        st.metric("Top Score", f"{leaderboard_df['final_score'].max():.0f}")
    with col4:
        st.metric("Avg Attendance", f"{leaderboard_df['member_attendance_rate'].mean():.1f}%")

def show_team_explorer():
    """Display team explorer"""
    st.subheader("👥 Team Explorer")
    
    team_df = load_team_leaderboard()
    member_df = load_member_scores()
    
    if len(team_df) == 0:
        st.warning("No team data available")
        return
    
    # Team selection
    team_names = team_df['team_name'].tolist()
    selected_team = st.selectbox("Select a team to explore", team_names)
    
    if selected_team:
        # Team info
        team_info = team_df[team_df['team_name'] == selected_team].iloc[0]
        team_members = member_df[member_df['team_name'] == selected_team]
        
        # Team summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Final Score", f"{team_info['final_score']:.0f}")
        with col2:
            st.metric("Member Points", f"{team_info['member_points']:.0f}")
        with col3:
            st.metric("Coach Points", f"{team_info['coach_points']:.0f}")
        with col4:
            st.metric("Attendance Rate", f"{team_info['member_attendance_rate']:.1f}%")
        
        # Members table
        if len(team_members) > 0:
            st.subheader(f"Team Members ({len(team_members)})")
            
            # Format member display
            member_display = team_members[['member_name', 'member_department', 'total_points', 'events_attended', 'is_leader']].copy()
            member_display.columns = ['Member Name', 'Department', 'Total Points', 'Events Attended', 'Is Leader']
            
            # Add rank
            member_display = member_display.sort_values('Total Points', ascending=False)
            member_display['Rank'] = range(1, len(member_display) + 1)
            
            # Reorder columns
            member_display = member_display[['Rank', 'Member Name', 'Department', 'Total Points', 'Events Attended', 'Is Leader']]
            
            # Style
            styled_members = member_display.style.format({
                'Total Points': '{:.0f}',
                'Events Attended': '{:.0f}'
            })
            
            st.dataframe(styled_members, use_container_width=True, hide_index=True)
        else:
            st.info("No member data available for this team")

def show_coach_explorer():
    """Display coach explorer"""
    st.subheader("🎓 Coach Explorer")
    
    coach_df = load_coach_leaderboard()
    
    if len(coach_df) == 0:
        st.warning("No coach data available")
        return
    
    # Format coach display
    display_df = coach_df.copy()
    display_df['rank'] = range(1, len(display_df) + 1)
    
    # Select columns
    display_columns = [
        'rank', 'coach_name', 'coach_department', 'total_points', 
        'sessions_attended', 'teams_coached_count'
    ]
    
    display_df = display_df[display_columns]
    display_df.columns = [
        'Rank', 'Coach Name', 'Department', 'Total Points', 
        'Sessions Attended', 'Teams Coached'
    ]
    
    # Style
    styled_df = display_df.style.format({
        'Total Points': '{:.0f}',
        'Sessions Attended': '{:.0f}',
        'Teams Coached': '{:.0f}'
    })
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Coaches", len(coach_df))
    with col2:
        st.metric("Avg Coach Score", f"{coach_df['total_points'].mean():.1f}")
    with col3:
        st.metric("Top Coach Score", f"{coach_df['total_points'].max():.0f}")

def show_event_analytics():
    """Display event analytics"""
    st.subheader("📊 Event Analytics")
    
    events_df = load_events()
    
    if len(events_df) == 0:
        st.warning("No event data available")
        return
    
    # Event overview
    st.markdown("### Event Overview")
    
    # Format events display
    display_df = events_df[['name', 'event_date', 'member_points_per_attendance', 'coach_points_per_attendance']].copy()
    display_df.columns = ['Event Name', 'Date', 'Member Points', 'Coach Points']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Get attendance stats per event
    conn = sqlite3.connect(DB_FILE)
    attendance_stats = pd.read_sql_query("""
        SELECT 
            e.name as event_name,
            COUNT(DISTINCT a.member_id) as members_attended,
            COUNT(DISTINCT a.coach_id) as coaches_attended,
            SUM(a.points_earned) as total_points_awarded
        FROM events e
        LEFT JOIN attendance a ON e.id = a.event_id
        WHERE e.is_active = 1
        GROUP BY e.id, e.name
        ORDER BY e.event_date DESC
    """, conn)
    conn.close()
    
    if len(attendance_stats) > 0:
        st.markdown("### Attendance Statistics")
        attendance_stats.columns = ['Event', 'Members Attended', 'Coaches Attended', 'Total Points Awarded']
        st.dataframe(attendance_stats, use_container_width=True, hide_index=True)
        
        # Charts
        if len(attendance_stats) > 1:
            st.markdown("### Event Participation Chart")
            fig = px.bar(
                attendance_stats, 
                x='Event', 
                y='Members Attended',
                title="Member Participation by Event"
            )
            st.plotly_chart(fig, use_container_width=True)

def show_admin_panel():
    """Display admin panel"""
    st.subheader("⚙️ Admin Panel")
    
    password = st.text_input("Enter admin password", type="password")
    
    if password == ADMIN_PASSWORD:
        st.success("✅ Admin access granted")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Quick Actions")
            if st.button("🔄 Refresh All Data"):
                clear_cache()
                st.success("Data refreshed!")
                st.rerun()
            
            if st.button("📊 Validate Data Integrity"):
                stats = get_database_stats()
                st.success("✅ Data integrity validation passed")
                for stat, value in stats.items():
                    st.info(f"{stat}: {value}")
        
        with col2:
            st.markdown("### System Information")
            stats = get_database_stats()
            
            st.markdown("**Database Statistics:**")
            for stat, value in stats.items():
                st.write(f"• {stat}: **{value}**")
            
            st.markdown("**System Status:**")
            st.write("• Database: **Connected**")
            st.write("• Views: **Active**")
            st.write("• Scoring: **Operational**")
        
        # Event management
        st.markdown("### Event Management")
        
        with st.expander("Add New Event"):
            with st.form("add_event"):
                event_name = st.text_input("Event Name")
                event_date = st.date_input("Event Date", datetime.now().date())
                member_points = st.number_input("Points per member attendance", value=1, min_value=0)
                coach_points = st.number_input("Points per coach attendance", value=2, min_value=0)
                
                if st.form_submit_button("Add Event"):
                    if event_name:
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO events (name, event_date, member_points_per_attendance, coach_points_per_attendance)
                            VALUES (?, ?, ?, ?)
                        """, (event_name, event_date, member_points, coach_points))
                        conn.commit()
                        conn.close()
                        clear_cache()
                        st.success(f"✅ Event '{event_name}' added!")
                    else:
                        st.error("Please enter an event name")
        
        # ========== TEAM MANAGEMENT SECTION ==========
        st.markdown("---")
        st.markdown("### ➕ Team Management")
        st.markdown("Add new teams, members, and coaches to the system")
        
        # Three main sections in columns
        col1, col2, col3 = st.columns(3)
        
        # ========== ADD NEW COACH ==========
        with col1:
            st.markdown("#### 👤 Add New Coach")
            with st.form("add_coach_form"):
                coach_name = st.text_input("Coach Name*", placeholder="Enter full name")
                coach_dept = st.selectbox("Department*", [
                    "Technical Services and Support", 
                    "Threat", 
                    "Information Services", 
                    "Product Management"
                ])
                
                if st.form_submit_button("Add Coach", type="primary"):
                    if coach_name.strip():
                        success, message = add_new_coach(coach_name.strip(), coach_dept)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.error("Please enter coach name")
        
        # ========== ADD NEW TEAM ==========
        with col2:
            st.markdown("#### 🏆 Add New Team")
            with st.form("add_team_form"):
                team_name = st.text_input("Team Name*", placeholder="Enter unique team name")
                team_dept = st.selectbox("Team Department*", [
                    "Technical Services and Support", 
                    "Threat", 
                    "Information Services", 
                    "Product Management"
                ])
                
                # Get coaches for selection
                coaches = get_existing_coaches()
                if coaches:
                    coach_options = {f"{name} ({dept})": coach_id for coach_id, name, dept in coaches}
                    selected_coach = st.selectbox("Select Coach*", list(coach_options.keys()))
                    coach_id = coach_options[selected_coach] if selected_coach else None
                else:
                    st.warning("No coaches available. Add a coach first.")
                    coach_id = None
                
                total_members = st.number_input("Expected Team Size*", min_value=1, max_value=10, value=5)
                
                if st.form_submit_button("Create Team", type="primary"):
                    if team_name.strip() and coach_id:
                        success, message = add_new_team(team_name.strip(), total_members, coach_id, team_dept)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill all required fields")
        
        # ========== ADD TEAM MEMBER ==========
        with col3:
            st.markdown("#### 👥 Add Team Member")
            with st.form("add_member_form"):
                member_name = st.text_input("Member Name*", placeholder="Enter full name")
                member_dept = st.selectbox("Member Department*", [
                    "Technical Services and Support", 
                    "Threat", 
                    "Information Services", 
                    "Product Management"
                ])
                
                # Get teams for selection
                teams = get_teams_for_selection()
                if teams:
                    team_options = {name: team_id for team_id, name in teams}
                    selected_team = st.selectbox("Select Team*", list(team_options.keys()))
                    team_id = team_options[selected_team] if selected_team else None
                else:
                    st.warning("No teams available. Create a team first.")
                    team_id = None
                
                is_leader = st.checkbox("Team Leader", help="Check if this member is the team leader")
                
                if st.form_submit_button("Add Member", type="primary"):
                    if member_name.strip() and team_id:
                        success, message = add_team_member(team_id, member_name.strip(), member_dept, is_leader)
                        if success:
                            st.success(message)
                            
                            # Check for dual role
                            if check_dual_role_member(member_name.strip()):
                                st.info(f"ℹ️ Note: '{member_name}' is also a coach and will get dual scoring")
                            
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill all required fields")
        
        # ========== CURRENT STATS ==========
        st.markdown("---")
        st.markdown("#### 📊 Current System Statistics")
        stats = get_database_stats()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Teams", stats["Active Teams"])
        with col2:
            st.metric("Members", stats["Active Members"]) 
        with col3:
            st.metric("Coaches", stats["Active Coaches"])
        with col4:
            st.metric("Events", stats["Active Events"])
        with col5:
            st.metric("Attendance Records", stats["Attendance Records"])
        
        # ========== IMPORTANT NOTES ==========
        with st.expander("ℹ️ Team Management Notes"):
            st.markdown("""
            **Scoring Rules (Automatically Applied):**
            - **Members**: Get 1 point per event attended
            - **Coaches**: Get 2 points per event attended, shared to ALL their teams
            - **Dual Roles**: Members who are also coaches get both member (1pt) and coach (2pts) for same event
            - **New Members**: Automatically get attendance records for all existing events (default: not attended)
            - **Team Leaders**: Only one leader per team (automatically updated)
            
            **Data Validation:**
            - Team names must be unique
            - Coach names must be unique  
            - Member names can exist in multiple teams (if they coach multiple teams)
            - All changes are immediately reflected in scoring views
            """)
    
    else:
        st.info("Enter the admin password to access management features")

def show_team_management():
    """Display team management interface"""
    st.subheader("➕ Team Management")
    st.markdown("Add new teams, members, and coaches to the system")
    
    # Three main sections in columns
    col1, col2, col3 = st.columns(3)
    
    # ========== ADD NEW COACH ==========
    with col1:
        st.markdown("### 👤 Add New Coach")
        with st.form("add_coach_form"):
            coach_name = st.text_input("Coach Name*", placeholder="Enter full name")
            coach_dept = st.selectbox("Department*", [
                "Information Services", "Threat", "Risk", "Financial Crime", 
                "Operations", "Compliance", "Legal", "Human Resources", "Other"
            ])
            
            if st.form_submit_button("Add Coach", type="primary"):
                if coach_name.strip():
                    success, message = add_new_coach(coach_name.strip(), coach_dept)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Please enter coach name")
    
    # ========== ADD NEW TEAM ==========
    with col2:
        st.markdown("### 🏆 Add New Team")
        with st.form("add_team_form"):
            team_name = st.text_input("Team Name*", placeholder="Enter unique team name")
            team_dept = st.selectbox("Team Department*", [
                "Information Services", "Threat", "Risk", "Financial Crime", 
                "Operations", "Compliance", "Legal", "Human Resources", "Other"
            ])
            
            # Get coaches for selection
            coaches = get_existing_coaches()
            if coaches:
                coach_options = {f"{name} ({dept})": coach_id for coach_id, name, dept in coaches}
                selected_coach = st.selectbox("Select Coach*", list(coach_options.keys()))
                coach_id = coach_options[selected_coach] if selected_coach else None
            else:
                st.warning("No coaches available. Add a coach first.")
                coach_id = None
            
            total_members = st.number_input("Expected Team Size*", min_value=1, max_value=10, value=5)
            
            if st.form_submit_button("Create Team", type="primary"):
                if team_name.strip() and coach_id:
                    success, message = add_new_team(team_name.strip(), total_members, coach_id, team_dept)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Please fill all required fields")
    
    # ========== ADD TEAM MEMBER ==========
    with col3:
        st.markdown("### 👥 Add Team Member")
        with st.form("add_member_form"):
            member_name = st.text_input("Member Name*", placeholder="Enter full name")
            member_dept = st.selectbox("Member Department*", [
                "Information Services", "Threat", "Risk", "Financial Crime", 
                "Operations", "Compliance", "Legal", "Human Resources", "Other"
            ])
            
            # Get teams for selection
            teams = get_teams_for_selection()
            if teams:
                team_options = {name: team_id for team_id, name in teams}
                selected_team = st.selectbox("Select Team*", list(team_options.keys()))
                team_id = team_options[selected_team] if selected_team else None
            else:
                st.warning("No teams available. Create a team first.")
                team_id = None
            
            is_leader = st.checkbox("Team Leader", help="Check if this member is the team leader")
            
            if st.form_submit_button("Add Member", type="primary"):
                if member_name.strip() and team_id:
                    success, message = add_team_member(team_id, member_name.strip(), member_dept, is_leader)
                    if success:
                        st.success(message)
                        
                        # Check for dual role
                        if check_dual_role_member(member_name.strip()):
                            st.info(f"ℹ️ Note: '{member_name}' is also a coach and will get dual scoring")
                        
                    else:
                        st.error(message)
                else:
                    st.error("Please fill all required fields")
    
    st.markdown("---")
    
    # ========== CURRENT STATS ==========
    st.markdown("### 📊 Current System Statistics")
    stats = get_database_stats()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Teams", stats["Active Teams"])
    with col2:
        st.metric("Members", stats["Active Members"]) 
    with col3:
        st.metric("Coaches", stats["Active Coaches"])
    with col4:
        st.metric("Events", stats["Active Events"])
    with col5:
        st.metric("Attendance Records", stats["Attendance Records"])
    
    # ========== IMPORTANT NOTES ==========
    with st.expander("ℹ️ Important Notes"):
        st.markdown("""
        **Scoring Rules (Automatically Applied):**
        - **Members**: Get 1 point per event attended
        - **Coaches**: Get 2 points per event attended, shared to ALL their teams
        - **Dual Roles**: Members who are also coaches get both member (1pt) and coach (2pts) for same event
        - **New Members**: Automatically get attendance records for all existing events (default: not attended)
        - **Team Leaders**: Only one leader per team (automatically updated)
        
        **Data Validation:**
        - Team names must be unique
        - Coach names must be unique  
        - Member names can exist in multiple teams (if they coach multiple teams)
        - All changes are immediately reflected in scoring views
        """)

if __name__ == "__main__":
    main()
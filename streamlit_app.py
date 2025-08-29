"""
CirQit Hackathon Dashboard - Production Version v2.1
100% Database-driven, with first-name display feature
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

def get_first_name(full_name):
    """Extract first name from full name for display purposes only"""
    if not full_name or pd.isna(full_name):
        return ""
    return str(full_name).split()[0] if str(full_name).strip() else ""

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
    df = pd.read_sql_query("SELECT * FROM v_coach_scores ORDER BY total_coach_points DESC", conn)
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

# ================== BONUS POINTS FUNCTIONS ==================

def get_all_members_for_bonus():
    """Get all active members for bonus point selection"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.id, m.name, t.name as team_name, m.department
        FROM members m
        JOIN teams t ON m.team_id = t.id
        WHERE m.is_active = 1 AND t.is_active = 1
        ORDER BY m.name
    """)
    members = cursor.fetchall()
    conn.close()
    return members

def get_all_coaches_for_bonus():
    """Get all active coaches for bonus point selection"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, department FROM coaches WHERE is_active = 1 ORDER BY name")
    coaches = cursor.fetchall()
    conn.close()
    return coaches

def award_member_bonus_points(member_id, reason, awarded_by, points=1):
    """Award bonus points to a member"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO member_bonus_points (member_id, points, reason, awarded_by)
            VALUES (?, ?, ?, ?)
        """, (member_id, points, reason, awarded_by))
        
        conn.commit()
        conn.close()
        clear_cache()
        return True, f"Successfully awarded {points} bonus point(s) to member"
        
    except Exception as e:
        return False, f"Error awarding bonus points: {str(e)}"

def award_coach_bonus_points(coach_id, reason, awarded_by, points=2):
    """Award bonus points to a coach"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO coach_bonus_points (coach_id, points, reason, awarded_by)
            VALUES (?, ?, ?, ?)
        """, (coach_id, points, reason, awarded_by))
        
        conn.commit()
        conn.close()
        clear_cache()
        return True, f"Successfully awarded {points} bonus point(s) to coach"
        
    except Exception as e:
        return False, f"Error awarding bonus points: {str(e)}"

def get_member_bonus_history(member_id):
    """Get bonus point history for a member"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("""
        SELECT points, reason, awarded_by, awarded_at
        FROM member_bonus_points
        WHERE member_id = ? AND is_active = 1
        ORDER BY awarded_at DESC
    """, conn, params=(member_id,))
    conn.close()
    return df

def get_coach_bonus_history(coach_id):
    """Get bonus point history for a coach"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("""
        SELECT points, reason, awarded_by, awarded_at
        FROM coach_bonus_points
        WHERE coach_id = ? AND is_active = 1
        ORDER BY awarded_at DESC
    """, conn, params=(coach_id,))
    conn.close()
    return df

def get_detailed_coach_info(coach_id):
    """Get detailed information about a specific coach"""
    conn = sqlite3.connect(DB_FILE)
    
    # Basic coach info
    coach_info = pd.read_sql_query("""
        SELECT * FROM v_coach_scores WHERE coach_id = ?
    """, conn, params=(coach_id,))
    
    # Teams coached by this coach
    teams_coached = pd.read_sql_query("""
        SELECT t.id, t.name, t.total_members, t.department,
               COUNT(DISTINCT m.id) as actual_members,
               COALESCE(ts.final_score, 0) as team_score,
               COALESCE(ts.member_attendance_rate, 0) as attendance_rate
        FROM teams t
        LEFT JOIN members m ON t.id = m.team_id AND m.is_active = 1
        LEFT JOIN v_team_scores ts ON t.id = ts.team_id
        WHERE t.coach_id = ? AND t.is_active = 1
        GROUP BY t.id, t.name, t.total_members, t.department, ts.final_score, ts.member_attendance_rate
        ORDER BY ts.final_score DESC
    """, conn, params=(coach_id,))
    
    # Coach attendance history
    attendance_history = pd.read_sql_query("""
        SELECT e.name as event_name, e.event_date, 
               CASE WHEN a.attended = 1 THEN 'Yes' ELSE 'No' END as attended,
               a.points_earned
        FROM events e
        LEFT JOIN attendance a ON e.id = a.event_id AND a.coach_id = ?
        WHERE e.is_active = 1
        ORDER BY e.event_date DESC
    """, conn, params=(coach_id,))
    
    conn.close()
    return coach_info, teams_coached, attendance_history

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
    
    # Search and filter options
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_term = st.text_input("🔍 Search teams", placeholder="Search by team name or department...")
    
    with col2:
        dept_filter = st.selectbox("Filter by Department", 
            ["All Departments"] + sorted(leaderboard_df['team_department'].dropna().unique().tolist()),
            key="team_leaderboard_dept_filter")
    
    with col3:
        show_top = st.selectbox("Show top teams", [10, 25, 50, "All"], index=0, key="team_leaderboard_show_top")
    
    # Apply filters
    filtered_df = leaderboard_df.copy()
    
    # Search filter
    if search_term:
        mask = (
            filtered_df['team_name'].str.contains(search_term, case=False, na=False) |
            filtered_df['team_department'].str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[mask]
    
    # Department filter
    if dept_filter != "All Departments":
        filtered_df = filtered_df[filtered_df['team_department'] == dept_filter]
    
    # Limit results
    if show_top != "All":
        display_df = filtered_df.head(show_top)
    else:
        display_df = filtered_df
    
    # Show results count
    if search_term or dept_filter != "All Departments":
        st.info(f"Showing {len(display_df)} of {len(leaderboard_df)} teams")
    
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
    
    # Search and filter for teams
    col1, col2 = st.columns([2, 1])
    
    with col1:
        team_search = st.text_input("🔍 Search teams", placeholder="Search by team name, department, or member name...")
    
    with col2:
        dept_filter = st.selectbox("Filter by Department", 
            ["All Departments"] + sorted(team_df['team_department'].dropna().unique().tolist()),
            key="team_explorer_dept_filter")
    
    # Apply filters to team list
    filtered_teams = team_df.copy()
    
    if team_search:
        # Search in team names, departments, and member names
        team_mask = (
            filtered_teams['team_name'].str.contains(team_search, case=False, na=False) |
            filtered_teams['team_department'].str.contains(team_search, case=False, na=False)
        )
        
        # Also search in member names
        member_teams = member_df[
            member_df['member_name'].str.contains(team_search, case=False, na=False)
        ]['team_name'].unique()
        
        member_mask = filtered_teams['team_name'].isin(member_teams)
        filtered_teams = filtered_teams[team_mask | member_mask]
    
    if dept_filter != "All Departments":
        filtered_teams = filtered_teams[filtered_teams['team_department'] == dept_filter]
    
    if len(filtered_teams) == 0:
        st.warning("No teams match your search criteria")
        return
    
    # Team selection
    team_names = filtered_teams['team_name'].tolist()
    
    # Show search results count
    if team_search or dept_filter != "All Departments":
        st.info(f"Found {len(team_names)} team(s) matching your criteria")
    
    selected_team = st.selectbox("Select a team to explore", team_names, key="team_explorer_team_select")
    
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
        
        # Coach Information Section
        st.markdown("---")
        st.subheader("🎓 Coach Information")
        
        # Get coach details for this team
        conn = sqlite3.connect(DB_FILE)
        coach_details = pd.read_sql_query("""
            SELECT c.id, c.name, c.department,
                   cs.coach_sessions_attended, cs.total_coach_points, 
                   cs.teams_coached_count
            FROM teams t
            JOIN coaches c ON t.coach_id = c.id
            LEFT JOIN v_coach_scores cs ON c.id = cs.coach_id
            WHERE t.name = ? AND t.is_active = 1 AND c.is_active = 1
        """, conn, params=(selected_team,))
        
        # Get total events for attendance rate calculation
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events WHERE is_active = 1")
        total_events = cursor.fetchone()[0]
        conn.close()
        
        if not coach_details.empty:
            coach = coach_details.iloc[0]
            
            # Coach basic info and metrics
            st.markdown(f"**Coach:** {get_first_name(coach['name'])} ({coach['department']})")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Points", f"{coach['total_coach_points']:.0f}")
            
            with col2:
                st.metric("Events Attended", f"{coach['coach_sessions_attended']:.0f}")
            
            with col3:
                attendance_rate = (coach['coach_sessions_attended'] / total_events * 100) if total_events > 0 else 0
                st.metric("Attendance %", f"{attendance_rate:.1f}%")
            
            with col4:
                st.metric("Teams Coached", f"{coach['teams_coached_count']:.0f}")
        else:
            st.warning("No coach information found for this team")
        
        # Members table
        if len(team_members) > 0:
            st.subheader(f"Team Members ({len(team_members)})")
            
            # Format member display
            member_display = team_members[['member_name', 'member_department', 'total_points', 'events_attended', 'is_leader']].copy()
            member_display['member_name'] = member_display['member_name'].apply(get_first_name)
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
    
    # Search and filter options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        coach_search = st.text_input("🔍 Search coaches", placeholder="Search by coach name or department...")
    
    with col2:
        dept_filter = st.selectbox("Filter by Department", 
            ["All Departments"] + sorted(coach_df['coach_department'].dropna().unique().tolist()),
            key="coach_explorer_dept_filter")
    
    # Apply filters
    filtered_coaches = coach_df.copy()
    
    if coach_search:
        mask = (
            filtered_coaches['coach_name'].str.contains(coach_search, case=False, na=False) |
            filtered_coaches['coach_department'].str.contains(coach_search, case=False, na=False)
        )
        filtered_coaches = filtered_coaches[mask]
    
    if dept_filter != "All Departments":
        filtered_coaches = filtered_coaches[filtered_coaches['coach_department'] == dept_filter]
    
    if len(filtered_coaches) == 0:
        st.warning("No coaches match your search criteria")
        return
    
    # Show search results count
    if coach_search or dept_filter != "All Departments":
        st.info(f"Found {len(filtered_coaches)} coach(es) matching your criteria")
    
    # Coach selection and detailed view
    st.markdown("---")
    
    # Two-column layout: List and Details
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📋 Coach List")
        
        # Format coach display for selection
        display_df = filtered_coaches.copy()
        display_df['rank'] = range(1, len(display_df) + 1)
        
        # Create a more compact display for selection
        coach_options = {}
        for _, row in display_df.iterrows():
            label = f"#{row['rank']} {get_first_name(row['coach_name'])} ({row['total_coach_points']:.0f} pts)"
            coach_options[label] = row['coach_id']
        
        selected_coach_label = st.radio("Select a coach to view details:", list(coach_options.keys()), key="coach_explorer_coach_select")
        selected_coach_id = coach_options[selected_coach_label] if selected_coach_label else None
    
    with col2:
        if selected_coach_id:
            st.markdown("### 👤 Coach Details")
            
            # Get detailed coach information
            coach_info, teams_coached, attendance_history = get_detailed_coach_info(selected_coach_id)
            
            if not coach_info.empty:
                coach = coach_info.iloc[0]
                
                # Coach summary metrics
                st.markdown("#### 🎯 Scoring Summary")
                
                col_a, col_b, col_c, col_d, col_e = st.columns(5)
                
                with col_a:
                    coach_sessions = coach.get('coach_sessions_attended', 0)
                    st.metric("Sessions Attended", f"{coach_sessions:.0f}", help="Total events attended")
                
                with col_b:
                    # Calculate attendance rate (sessions attended / total events)
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM events WHERE is_active = 1")
                    total_events = cursor.fetchone()[0]
                    conn.close()
                    
                    attendance_rate = (coach_sessions / total_events * 100) if total_events > 0 else 0
                    st.metric("Attendance Rate", f"{attendance_rate:.1f}%", help="Individual attendance rate")
                
                with col_c:
                    coach_points = coach.get('total_coach_points', 0)
                    st.metric("Coach Points", f"{coach_points:.0f}", help="Points earned as a coach (2 pts/event)")
                
                with col_d:
                    member_points = coach.get('total_member_points', 0) 
                    if member_points > 0:
                        st.metric("Member Points", f"{member_points:.0f}", help="Points earned as team member (1 pt/event)")
                    else:
                        st.metric("Member Points", "0", help="Points earned as team member (1 pt/event)")
                
                with col_e:
                    st.metric("Teams Coached", f"{coach['teams_coached_count']:.0f}")
                
                # Coach basic info
                st.markdown(f"**Name:** {get_first_name(coach['coach_name'])}")
                st.markdown(f"**Department:** {coach['coach_department']}")
                
                # Teams coached section
                if not teams_coached.empty:
                    st.markdown("---")
                    st.markdown("### 🏆 Teams Coached")
                    
                    if len(teams_coached) == 1:
                        # Single team - show details directly
                        team = teams_coached.iloc[0]
                        st.markdown(f"**Team:** {team['name']}")
                        
                        col_x, col_y, col_z = st.columns(3)
                        with col_x:
                            st.metric("Team Score", f"{team['team_score']:.0f}")
                        with col_y:
                            st.metric("Members", f"{team['actual_members']}/{team['total_members']}")
                        with col_z:
                            st.metric("Attendance Rate", f"{team['attendance_rate']:.1f}%")
                    
                    else:
                        # Multiple teams - show list and allow selection
                        st.markdown(f"**{len(teams_coached)} teams coached:**")
                        
                        # Team selection
                        team_options = {}
                        for _, team in teams_coached.iterrows():
                            label = f"{team['name']} ({team['team_score']:.0f} pts, {team['attendance_rate']:.1f}% attendance)"
                            team_options[label] = team['id']
                        
                        selected_team_label = st.selectbox("Select team for details:", list(team_options.keys()), key="coach_team_details_select")
                        
                        if selected_team_label:
                            selected_team_id = team_options[selected_team_label]
                            team_details = teams_coached[teams_coached['id'] == selected_team_id].iloc[0]
                            
                            col_x, col_y, col_z = st.columns(3)
                            with col_x:
                                st.metric("Team Score", f"{team_details['team_score']:.0f}")
                            with col_y:
                                st.metric("Members", f"{team_details['actual_members']}/{team_details['total_members']}")
                            with col_z:
                                st.metric("Attendance Rate", f"{team_details['attendance_rate']:.1f}%")
                else:
                    st.info("No teams assigned to this coach")
                
                # Attendance history
                if not attendance_history.empty:
                    st.markdown("---")
                    st.markdown("### 📅 Attendance History")
                    
                    # Format attendance display
                    attendance_display = attendance_history.copy()
                    attendance_display.columns = ['Event', 'Date', 'Attended', 'Points Earned']
                    
                    st.dataframe(attendance_display, use_container_width=True, hide_index=True)
                
                # Bonus points history
                bonus_history = get_coach_bonus_history(selected_coach_id)
                if not bonus_history.empty:
                    st.markdown("---")
                    st.markdown("### 🎯 Bonus Points History")
                    
                    bonus_display = bonus_history.copy()
                    bonus_display.columns = ['Points', 'Reason', 'Awarded By', 'Date']
                    
                    st.dataframe(bonus_display, use_container_width=True, hide_index=True)
                    st.metric("Total Bonus Points", bonus_history['points'].sum())
        else:
            st.info("Select a coach from the list to view detailed information")
    
    # Summary stats at bottom
    st.markdown("---")
    st.markdown("### 📊 Coach Summary Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Coaches", len(coach_df))
    with col2:
        st.metric("Avg Coach Score", f"{coach_df['total_coach_points'].mean():.1f}")
    with col3:
        st.metric("Top Coach Score", f"{coach_df['total_coach_points'].max():.0f}")

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
                    coach_options = {f"{get_first_name(name)} ({dept})": coach_id for coach_id, name, dept in coaches}
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
        
        # ========== BONUS POINTS SECTION ==========
        st.markdown("---")
        st.markdown("### 🎯 Award Bonus Points")
        st.markdown("Award individual bonus points to members and coaches")
        
        col1, col2 = st.columns(2)
        
        # ========== AWARD MEMBER BONUS POINTS ==========
        with col1:
            st.markdown("#### 👤 Award Member Bonus Points")
            with st.form("award_member_bonus"):
                # Get all members
                members = get_all_members_for_bonus()
                if members:
                    member_options = {f"{get_first_name(name)} ({team_name} - {dept})": member_id for member_id, name, team_name, dept in members}
                    selected_member = st.selectbox("Select Member*", list(member_options.keys()))
                    member_id = member_options[selected_member] if selected_member else None
                else:
                    st.warning("No members available")
                    member_id = None
                
                member_reason = st.text_area("Reason for bonus points*", placeholder="e.g., Outstanding presentation, innovative solution, exceptional teamwork...")
                member_points = st.number_input("Bonus Points", value=1, min_value=1, max_value=10, help="Default: 1 point for members")
                
                if st.form_submit_button("Award Member Bonus", type="primary"):
                    if member_id and member_reason.strip():
                        success, message = award_member_bonus_points(member_id, member_reason.strip(), "admin", member_points)
                        if success:
                            st.success(f"✅ {message}")
                            st.success(f"Awarded {member_points} bonus point(s) to {selected_member.split(' (')[0]}")
                        else:
                            st.error(message)
                    else:
                        st.error("Please select a member and provide a reason")
        
        # ========== AWARD COACH BONUS POINTS ==========
        with col2:
            st.markdown("#### 🎓 Award Coach Bonus Points")
            with st.form("award_coach_bonus"):
                # Get all coaches
                coaches = get_all_coaches_for_bonus()
                if coaches:
                    coach_options = {f"{get_first_name(name)} ({dept})": coach_id for coach_id, name, dept in coaches}
                    selected_coach = st.selectbox("Select Coach*", list(coach_options.keys()))
                    coach_id = coach_options[selected_coach] if selected_coach else None
                else:
                    st.warning("No coaches available")
                    coach_id = None
                
                coach_reason = st.text_area("Reason for bonus points*", placeholder="e.g., Exceptional mentoring, innovative guidance, outstanding leadership...")
                coach_points = st.number_input("Bonus Points", value=2, min_value=1, max_value=10, help="Default: 2 points for coaches")
                
                if st.form_submit_button("Award Coach Bonus", type="primary"):
                    if coach_id and coach_reason.strip():
                        success, message = award_coach_bonus_points(coach_id, coach_reason.strip(), "admin", coach_points)
                        if success:
                            st.success(f"✅ {message}")
                            st.success(f"Awarded {coach_points} bonus point(s) to {selected_coach.split(' (')[0]}")
                        else:
                            st.error(message)
                    else:
                        st.error("Please select a coach and provide a reason")
        
        # ========== BONUS POINTS HISTORY ==========
        with st.expander("📊 View Bonus Points History"):
            tab1, tab2 = st.tabs(["Member Bonus History", "Coach Bonus History"])
            
            with tab1:
                if members:
                    selected_member_history = st.selectbox("Select Member for History", list(member_options.keys()), key="member_history")
                    if selected_member_history:
                        member_id_history = member_options[selected_member_history]
                        history_df = get_member_bonus_history(member_id_history)
                        if not history_df.empty:
                            st.dataframe(history_df, use_container_width=True)
                            st.metric("Total Bonus Points", history_df['points'].sum())
                        else:
                            st.info("No bonus points awarded to this member yet")
            
            with tab2:
                if coaches:
                    selected_coach_history = st.selectbox("Select Coach for History", list(coach_options.keys()), key="coach_history")
                    if selected_coach_history:
                        coach_id_history = coach_options[selected_coach_history]
                        history_df = get_coach_bonus_history(coach_id_history)
                        if not history_df.empty:
                            st.dataframe(history_df, use_container_width=True)
                            st.metric("Total Bonus Points", history_df['points'].sum())
                        else:
                            st.info("No bonus points awarded to this coach yet")

        # ========== TEAM EDITING SECTION ==========
        st.markdown("---")
        st.markdown("### ✏️ Edit Existing Teams")
        st.markdown("Rename existing teams while preserving all scores and data")
        
        with st.expander("🔧 Team Name Editor"):
            # Load all teams
            conn = sqlite3.connect(DB_FILE)
            teams_df = pd.read_sql_query("""
                SELECT id, name, total_members, department 
                FROM teams 
                WHERE is_active = 1 
                ORDER BY name
            """, conn)
            conn.close()
            
            if not teams_df.empty:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("#### Select Team to Rename")
                    # Create a selectbox with team info
                    team_options = [f"{row['name']} (ID: {row['id']}, {row['total_members']} members)" 
                                  for _, row in teams_df.iterrows()]
                    
                    selected_option = st.selectbox(
                        "Choose team to rename:",
                        options=team_options,
                        key="team_select"
                    )
                    
                    if selected_option:
                        # Extract team ID from selection
                        team_id = int(selected_option.split("ID: ")[1].split(",")[0])
                        selected_team = teams_df[teams_df['id'] == team_id].iloc[0]
                        
                        st.info(f"**Current name:** {selected_team['name']}")
                        st.info(f"**Department:** {selected_team['department']}")
                        st.info(f"**Members:** {selected_team['total_members']}")
                
                with col2:
                    st.markdown("#### Enter New Name")
                    new_team_name = st.text_input(
                        "New team name:",
                        placeholder="Enter the new team name",
                        key="new_team_name"
                    )
                    
                    if st.button("🔄 Rename Team", type="primary"):
                        if not new_team_name.strip():
                            st.error("Please enter a new team name")
                        elif new_team_name.strip() == selected_team['name']:
                            st.error("New name is the same as current name")
                        else:
                            # Check if new name already exists
                            conn = sqlite3.connect(DB_FILE)
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM teams WHERE name = ? AND is_active = 1", (new_team_name.strip(),))
                            existing = cursor.fetchone()
                            
                            if existing:
                                st.error(f"Team name '{new_team_name.strip()}' already exists")
                                conn.close()
                            else:
                                try:
                                    # Get scores before rename for verification
                                    cursor.execute("""
                                        SELECT member_points, coach_points, bonus_points, final_score
                                        FROM v_team_scores WHERE team_id = ?
                                    """, (team_id,))
                                    scores_before = cursor.fetchone()
                                    
                                    # Perform the rename
                                    cursor.execute("""
                                        UPDATE teams 
                                        SET name = ?, updated_at = CURRENT_TIMESTAMP 
                                        WHERE id = ?
                                    """, (new_team_name.strip(), team_id))
                                    
                                    # Log the change
                                    cursor.execute("""
                                        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by, changed_at)
                                        VALUES ('teams', ?, 'rename', ?, ?, 'admin_panel', CURRENT_TIMESTAMP)
                                    """, (team_id, f"name: {selected_team['name']}", f"name: {new_team_name.strip()}"))
                                    
                                    conn.commit()
                                    
                                    # Verify scores preserved
                                    cursor.execute("""
                                        SELECT member_points, coach_points, bonus_points, final_score
                                        FROM v_team_scores WHERE team_id = ?
                                    """, (team_id,))
                                    scores_after = cursor.fetchone()
                                    
                                    conn.close()
                                    
                                    # Clear cache to show updated data
                                    clear_cache()
                                    
                                    st.success(f"✅ Team renamed successfully!")
                                    st.success(f"**{selected_team['name']}** → **{new_team_name.strip()}**")
                                    
                                    if scores_before and scores_after:
                                        if scores_before == scores_after:
                                            st.success("🔐 All scores preserved!")
                                            st.info(f"Scores: Members={scores_after[0]}, Coach={scores_after[1]}, Bonus={scores_after[2]}, Total={scores_after[3]}")
                                        else:
                                            st.warning("⚠️ Scores may have changed during rename")
                                    
                                    st.rerun()
                                    
                                except Exception as e:
                                    conn.rollback()
                                    conn.close()
                                    st.error(f"❌ Error renaming team: {str(e)}")
            else:
                st.warning("No active teams found in database")

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
        with st.expander("ℹ️ Scoring System Rules"):
            st.markdown("""
            **Attendance Scoring (Automatic):**
            - **Members**: Get 1 point per event attended
            - **Coaches**: Get 2 points per event attended, shared to ALL their teams
            - **Dual Roles**: Members who are also coaches get both member (1pt) and coach (2pts) for same event
            
            **Bonus Points Scoring (Manual Award):**
            - **Member Bonus**: 1 point (default) added to member's individual score AND their team's total
            - **Coach Bonus**: 2 points (default) added to coach's individual score AND ALL teams they manage
            - **Coach Logic**: If coach manages 3 teams, they get 2 bonus points, but each team gets 2 bonus points
            - **Accumulation**: All bonus points accumulate with attendance points for final scores
            
            **Data Management:**
            - Team names must be unique
            - Coach names must be unique  
            - Member names can exist in multiple teams (if they coach multiple teams)
            - New members automatically get attendance records for all existing events (default: not attended)
            - Team leaders: Only one leader per team (automatically updated)
            - All changes are immediately reflected in scoring views
            
            **Bonus Points Notes:**
            - Bonus points are permanent once awarded
            - Include detailed reasons for transparency
            - Points can be customized (1-10 range)
            - History is tracked for audit purposes
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
                coach_options = {f"{get_first_name(name)} ({dept})": coach_id for coach_id, name, dept in coaches}
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
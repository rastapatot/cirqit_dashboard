"""
CirQit Hackathon Dashboard - Production Application
Accurate scoring system with proper database backend
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from database import DatabaseManager, DataMigration
from services import ScoringService, EventManagementService

# Configuration
try:
    ADMIN_PASSWORD = st.secrets["admin_password"]
except KeyError:
    ADMIN_PASSWORD = "cirqit2024"  # Default password for deployment
    st.warning("⚠️ Using default admin password. Please configure 'admin_password' in Streamlit Cloud secrets for security.")

DB_FILE = "cirqit_dashboard.db"

@st.cache_resource
def initialize_services():
    """Initialize database and services"""
    db_manager = DatabaseManager(DB_FILE)
    scoring_service = ScoringService(db_manager)
    event_service = EventManagementService(db_manager)
    return db_manager, scoring_service, event_service

@st.cache_data
def load_team_leaderboard():
    """Load team leaderboard data"""
    _, scoring_service, _ = initialize_services()
    return scoring_service.get_team_leaderboard()

@st.cache_data
def load_coach_leaderboard():
    """Load coach leaderboard data"""
    _, scoring_service, _ = initialize_services()
    return scoring_service.get_coach_leaderboard()

@st.cache_data
def load_events():
    """Load events data"""
    _, _, event_service = initialize_services()
    return event_service.get_events()

def clear_cache():
    """Clear all cached data"""
    st.cache_data.clear()

def main():
    st.set_page_config(
        page_title="CirQit Hackathon Dashboard",
        page_icon="🏆",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize services
    db_manager, scoring_service, event_service = initialize_services()
    
    # Check if database is properly initialized
    schema_version = db_manager.get_schema_version()
    
    # Header
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 30px;">
        <img src="data:image/png;base64,{}" width="120"/>
        <div>
            <h1 style="margin: 0;">CirQit Hackathon Dashboard</h1>
            <p style="margin: 5px 0; color: #666;">Production Scoring System v{}</p>
        </div>
    </div>
    """.format(
        __import__('base64').b64encode(open('CirQit_Logo.png', 'rb').read()).decode(),
        schema_version
    ), unsafe_allow_html=True)
    
    # Sidebar status
    with st.sidebar:
        st.markdown("### System Status")
        
        if schema_version > 0:
            st.success("✅ Production Database")
            integrity_report = db_manager.validate_data_integrity()
            
            if integrity_report["valid"]:
                st.success("✅ Data Integrity Valid")
            else:
                st.error("❌ Data Integrity Issues")
                for issue in integrity_report["issues"]:
                    st.error(f"• {issue}")
            
            st.markdown("### Statistics")
            for stat, value in integrity_report["stats"].items():
                st.metric(stat.replace("_", " ").title(), value)
                
        else:
            st.error("❌ Database Not Initialized")
            st.warning("Please migrate data in Admin Panel")
        
        # Quick actions
        st.markdown("### Quick Actions")
        if st.button("🔄 Refresh Data"):
            clear_cache()
            st.rerun()
    
    # Main navigation
    if schema_version == 0:
        # Database not initialized - show migration interface
        show_migration_interface(db_manager)
    else:
        # Normal operation
        show_main_interface(scoring_service, event_service)

def show_migration_interface(db_manager):
    """Show database migration interface"""
    st.error("🚧 Database requires migration from CSV system")
    
    st.markdown("""
    ### Migration Required
    
    The dashboard needs to migrate from the CSV-based system to the production database.
    This will fix all scoring inconsistencies and enable accurate individual tracking.
    
    **What will be migrated:**
    - Team and member data from masterlist
    - Event attendance from CSV files
    - Individual member attendance records
    - Coach participation data
    - Existing bonus points
    
    **Benefits after migration:**
    - ✅ Accurate individual member scoring
    - ✅ Consistent data across all tabs
    - ✅ Easy addition of new events
    - ✅ Detailed reporting capabilities
    - ✅ Future-proof architecture
    """)
    
    if st.button("🚀 Start Migration", type="primary"):
        with st.spinner("Migrating data... This may take a moment."):
            migration = DataMigration(db_manager)
            success = migration.migrate_from_csv(
                "CirQit-TC-TeamScores-AsOf-2025-08-23.csv",
                "teams-masterlist.csv"
            )
        
        if success:
            st.success("✅ Migration completed successfully!")
            st.balloons()
            
            # Show migration report
            report = migration.get_migration_report()
            
            with st.expander("📋 Migration Report"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Steps", report["total_steps"])
                with col2:
                    st.metric("Successful", report["success_count"])
                with col3:
                    st.metric("Errors", report["error_count"])
                
                if report["error_count"] > 0:
                    st.warning("Some errors occurred during migration:")
                    for log in report["migration_log"]:
                        if log["status"] == "ERROR":
                            st.error(f"• {log['step']}: {log['details']}")
            
            st.info("🔄 Please refresh the page to use the new system.")
            
        else:
            st.error("❌ Migration failed. Please check the logs.")
            report = migration.get_migration_report()
            
            for log in report["migration_log"]:
                if log["status"] == "ERROR":
                    st.error(f"Error in {log['step']}: {log['details']}")

def show_main_interface(scoring_service, event_service):
    """Show main dashboard interface"""
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏆 Team Leaderboard", 
        "👥 Team Explorer", 
        "🎓 Coach Explorer", 
        "📊 Event Analytics",
        "⚙️ Admin Panel"
    ])
    
    with tab1:
        show_team_leaderboard(scoring_service)
    
    with tab2:
        show_team_explorer(scoring_service)
    
    with tab3:
        show_coach_explorer(scoring_service)
    
    with tab4:
        show_event_analytics(event_service, scoring_service)
    
    with tab5:
        show_admin_panel(scoring_service, event_service)

def show_team_leaderboard(scoring_service):
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
    
    # Reorder columns for better display
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
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Teams", len(leaderboard_df))
    with col2:
        avg_score = leaderboard_df['final_score'].mean()
        st.metric("Average Score", f"{avg_score:.1f}")
    with col3:
        avg_attendance = leaderboard_df['member_attendance_rate'].mean()
        st.metric("Average Attendance", f"{avg_attendance:.1f}%")
    with col4:
        total_points = leaderboard_df['final_score'].sum()
        st.metric("Total Points Awarded", f"{total_points:.0f}")

def show_team_explorer(scoring_service):
    """Display detailed team explorer"""
    st.subheader("👥 Team Explorer")
    
    # Load teams
    leaderboard_df = load_team_leaderboard()
    
    if len(leaderboard_df) == 0:
        st.warning("No team data available")
        return
    
    # Team selection
    team_names = leaderboard_df['team_name'].tolist()
    selected_team = st.selectbox("Select a team", team_names)
    
    # Get detailed team information
    team_details = scoring_service.get_team_details(selected_team)
    
    if not team_details:
        st.error("Team details not found")
        return
    
    team_info = team_details['team']
    members = team_details['members']
    coach_info = team_details['coach']
    
    # Team overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Final Score", f"{team_info['final_score']:.0f}")
    with col2:
        st.metric("Member Points", f"{team_info['member_points']:.0f}")
    with col3:
        st.metric("Coach Points", f"{team_info['coach_points']:.0f}")
    with col4:
        st.metric("Attendance Rate", f"{team_info['member_attendance_rate']:.1f}%")
    
    # Enhanced Coach Information (highlighted prominently)
    if coach_info:
        st.markdown("### 🎓 Coach Performance")
        
        # Create highlighted coach container
        with st.container():
            st.markdown("""
            <div style="
                background: linear-gradient(90deg, #ff6b6b, #4ecdc4);
                padding: 20px;
                border-radius: 10px;
                color: white;
                margin: 10px 0;
            ">
                <h4 style="margin: 0; color: white;">👨‍🏫 Coach Details</h4>
            </div>
            """, unsafe_allow_html=True)
            
            coach_col1, coach_col2, coach_col3, coach_col4 = st.columns(4)
            with coach_col1:
                st.markdown(f"**👤 Name**  \n{coach_info['coach_name']}")
            with coach_col2:
                st.markdown(f"**🏢 Department**  \n{coach_info['coach_department']}")
            with coach_col3:
                st.markdown(f"**🏆 Coach Points**  \n{coach_info['coach_points']:.0f} points")
            with coach_col4:
                sessions = coach_info.get('sessions_attended', 0)
                st.markdown(f"**📅 Sessions**  \n{sessions} attended")
            
            # Coach performance breakdown
            if coach_info['coach_points'] > 0:
                st.info(f"💡 **Coach Scoring**: {sessions} sessions × 2 points = {coach_info['coach_points']:.0f} points")
    
    # Team composition
    st.markdown("### 👥 Team Members")
    
    if members:
        members_df = pd.DataFrame(members)
        
        # Format member data for display
        display_cols = ['member_name', 'member_department', 'is_leader', 'total_points', 'events_attended']
        members_display = members_df[display_cols].copy()
        members_display.columns = ['Name', 'Department', 'Leader', 'Points', 'Events Attended']
        members_display['Leader'] = members_display['Leader'].map({True: '👑', False: ''})
        
        st.dataframe(members_display, use_container_width=True, hide_index=True)
        
        # Member performance chart
        if len(members_df) > 1:
            fig = px.bar(
                members_df, 
                x='member_name', 
                y='total_points',
                title='Individual Member Performance',
                labels={'member_name': 'Member', 'total_points': 'Points Earned'},
                color_discrete_sequence=['#3498db']
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        # Combined team performance visualization
        if coach_info and coach_info['coach_points'] > 0:
            st.markdown("### 📊 Complete Team Performance")
            
            # Create combined chart showing members + coach
            combined_data = []
            
            # Add member data
            for member in members:
                combined_data.append({
                    'name': member['member_name'],
                    'points': member['total_points'],
                    'type': 'Member',
                    'color': '#3498db'
                })
            
            # Add coach data
            combined_data.append({
                'name': f"🎓 {coach_info['coach_name']} (Coach)",
                'points': coach_info['coach_points'],
                'type': 'Coach',
                'color': '#e74c3c'
            })
            
            combined_df = pd.DataFrame(combined_data)
            
            fig = px.bar(
                combined_df,
                x='name',
                y='points', 
                color='type',
                title='Team Performance: Members + Coach',
                labels={'name': 'Team Member', 'points': 'Points Earned'},
                color_discrete_map={'Member': '#3498db', 'Coach': '#e74c3c'}
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

def show_coach_explorer(scoring_service):
    """Display coach search and details interface"""
    st.subheader("🎓 Coach Explorer")
    
    # Load coaches
    coach_df = load_coach_leaderboard()
    
    if len(coach_df) == 0:
        st.warning("No coach data available")
        return
    
    # Coach search and selection
    st.markdown("### 🔍 Search Coach")
    
    # Search options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Coach selection dropdown with search
        coach_names = sorted(coach_df['coach_name'].tolist())
        selected_coach = st.selectbox(
            "Select a coach to view their details", 
            coach_names,
            help="Choose a coach to see their performance and teams"
        )
    
    with col2:
        # Quick stats
        total_coaches = len(coach_df)
        active_coaches = len(coach_df[coach_df['total_points'] > 0])
        st.metric("Total Coaches", total_coaches)
        st.metric("Active Coaches", active_coaches)
    
    # Display selected coach details
    if selected_coach:
        coach_details = scoring_service.get_coach_details(selected_coach)
        
        if coach_details:
            coach_info = coach_details['coach']
            teams = coach_details['teams']
            
            # Coach profile header
            st.markdown("---")
            st.markdown(f"## 👨‍🏫 {coach_info['coach_name']}")
            
            # Coach performance metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "📊 Total Points", 
                    f"{coach_info['total_points']:.0f}",
                    help="Points earned from attending tech sharing sessions"
                )
            with col2:
                st.metric(
                    "📅 Sessions Attended", 
                    coach_info['sessions_attended'],
                    help="Number of tech sharing sessions attended"
                )
            with col3:
                st.metric(
                    "👥 Teams Coached", 
                    len(teams),
                    help="Number of teams under this coach"
                )
            with col4:
                if coach_info['sessions_attended'] > 0:
                    avg_points = coach_info['total_points'] / coach_info['sessions_attended']
                    st.metric(
                        "⭐ Points/Session", 
                        f"{avg_points:.1f}",
                        help="Average points earned per session"
                    )
                else:
                    st.metric("⭐ Points/Session", "0.0")
            
            # Department info
            st.info(f"🏢 **Department:** {coach_info['coach_department']}")
            
            # Teams coached section
            if teams and len(teams) > 0:
                st.markdown("### 🏆 Teams Under This Coach")
                
                # Create enhanced teams display
                teams_df = pd.DataFrame(teams)
                
                # Format teams data for better display
                teams_display = teams_df[['team_name', 'final_score', 'member_points', 'coach_points', 'member_attendance_rate']].copy()
                teams_display.columns = ['Team Name', 'Final Score', 'Member Points', 'Coach Points', 'Attendance Rate (%)']
                teams_display = teams_display.sort_values('Final Score', ascending=False)
                teams_display.index = range(1, len(teams_display) + 1)
                
                # Display teams table
                st.dataframe(
                    teams_display, 
                    use_container_width=True,
                    column_config={
                        "Final Score": st.column_config.NumberColumn(
                            "Final Score",
                            help="Total team score (member + coach + bonus points)"
                        ),
                        "Attendance Rate (%)": st.column_config.NumberColumn(
                            "Attendance Rate (%)",
                            help="Percentage of team members who attended sessions",
                            format="%.1f%%"
                        )
                    }
                )
                
                # Team performance visualization
                if len(teams_df) > 1:
                    st.markdown("#### 📈 Team Performance Comparison")
                    
                    fig = px.bar(
                        teams_df,
                        x='team_name',
                        y='final_score',
                        title=f'Performance of Teams Coached by {coach_info["coach_name"]}',
                        labels={'team_name': 'Team', 'final_score': 'Final Score'},
                        color='final_score',
                        color_continuous_scale='viridis'
                    )
                    fig.update_layout(
                        xaxis_tickangle=-45,
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Summary stats for this coach's teams
                st.markdown("#### 📊 Coaching Summary")
                summary_col1, summary_col2, summary_col3 = st.columns(3)
                
                with summary_col1:
                    avg_team_score = teams_df['final_score'].mean()
                    st.metric("Average Team Score", f"{avg_team_score:.1f}")
                
                with summary_col2:
                    avg_attendance = teams_df['member_attendance_rate'].mean()
                    st.metric("Average Team Attendance", f"{avg_attendance:.1f}%")
                
                with summary_col3:
                    total_members = teams_df['member_points'].sum() / 1  # Assuming 1 point per member per session
                    best_team = teams_df.loc[teams_df['final_score'].idxmax(), 'team_name']
                    st.metric("Best Performing Team", best_team)
                    
            else:
                st.info("🔍 This coach is not currently assigned to any teams.")
                
            # Additional coach insights
            if coach_info['total_points'] > 0:
                st.markdown("### 💡 Coach Insights")
                
                insights = []
                
                # Performance insights
                if coach_info['sessions_attended'] == 3:
                    insights.append("🌟 **Perfect Attendance**: Attended all tech sharing sessions!")
                elif coach_info['sessions_attended'] >= 2:
                    insights.append("✅ **Good Attendance**: Attended most tech sharing sessions")
                else:
                    insights.append("📝 **Limited Attendance**: Consider attending more sessions")
                
                # Team performance insights
                if teams and len(teams) > 0:
                    top_team_score = teams_df['final_score'].max()
                    if top_team_score >= 20:
                        insights.append("🏆 **Excellent Coaching**: Has teams with high scores!")
                    elif top_team_score >= 15:
                        insights.append("👍 **Good Coaching**: Teams showing solid performance")
                
                for insight in insights:
                    st.success(insight)

def show_event_analytics(event_service, scoring_service):
    """Display event analytics"""
    st.subheader("📊 Event Analytics")
    
    # Load events
    events_df = load_events()
    
    if len(events_df) == 0:
        st.warning("No events found")
        return
    
    # Event statistics
    event_stats = scoring_service.get_event_statistics()
    
    if len(event_stats) > 0:
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Events", len(event_stats))
        with col2:
            total_member_attendance = event_stats['members_attended'].sum()
            st.metric("Total Member Attendances", total_member_attendance)
        with col3:
            total_coach_attendance = event_stats['coaches_attended'].sum()
            st.metric("Total Coach Attendances", total_coach_attendance)
        with col4:
            total_points = event_stats['member_points_awarded'].sum() + event_stats['coach_points_awarded'].sum()
            st.metric("Total Points Awarded", f"{total_points:.0f}")
        
        # Event comparison chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Member Attendance',
            x=event_stats['event_name'],
            y=event_stats['members_attended'],
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name='Coach Attendance',
            x=event_stats['event_name'],
            y=event_stats['coaches_attended'],
            marker_color='darkblue'
        ))
        
        fig.update_layout(
            title='Event Attendance Comparison',
            xaxis_title='Event',
            yaxis_title='Attendees',
            barmode='group'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed event statistics
        st.markdown("### 📋 Event Details")
        
        display_stats = event_stats.copy()
        display_stats.columns = [
            'Event Name', 'Date', 'Members Attended', 'Coaches Attended',
            'Member Points', 'Coach Points', 'Teams Participated'
        ]
        
        st.dataframe(display_stats, use_container_width=True, hide_index=True)

def show_admin_panel(scoring_service, event_service):
    """Display admin panel"""
    st.subheader("⚙️ Admin Panel")
    
    password = st.text_input("Enter admin password", type="password")
    
    if password != ADMIN_PASSWORD:
        st.info("Enter the correct password to access admin features.")
        return
    
    st.success("✅ Admin access granted")
    
    # Admin sections
    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "➕ Add Event", "🎁 Bonus Points", "📥 Import Data", "🔧 System"
    ])
    
    with admin_tab1:
        show_add_event_interface(event_service)
    
    with admin_tab2:
        show_bonus_points_interface(scoring_service)
    
    with admin_tab3:
        show_import_interface(event_service)
    
    with admin_tab4:
        show_system_interface(scoring_service)

def show_add_event_interface(event_service):
    """Show add event interface"""
    st.markdown("### ➕ Create New Event")
    
    with st.form("add_event_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            event_name = st.text_input("Event Name*", placeholder="e.g., TechSharing4-NextJS")
            event_date = st.date_input("Event Date*", datetime.now().date())
            event_type = st.selectbox("Event Type", ["tech_sharing", "workshop", "hackathon", "presentation"])
        
        with col2:
            description = st.text_area("Description", placeholder="Brief description of the event")
            member_points = st.number_input("Points per member attendance", value=1, min_value=0)
            coach_points = st.number_input("Points per coach attendance", value=2, min_value=0)
        
        if st.form_submit_button("Create Event", type="primary"):
            if event_name and event_date:
                success = event_service.create_event(
                    name=event_name,
                    description=description,
                    event_date=event_date,
                    event_type=event_type,
                    member_points=member_points,
                    coach_points=coach_points
                )
                
                if success:
                    st.success(f"✅ Event '{event_name}' created successfully!")
                    clear_cache()
                else:
                    st.error("❌ Failed to create event. Event name might already exist.")
            else:
                st.error("Please fill in all required fields (*)")

def show_bonus_points_interface(scoring_service):
    """Show bonus points interface"""
    st.markdown("### 🎁 Award Bonus Points")
    
    # Load teams for selection
    leaderboard_df = load_team_leaderboard()
    team_names = leaderboard_df['team_name'].tolist() if len(leaderboard_df) > 0 else []
    
    with st.form("bonus_points_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            selected_team = st.selectbox("Select Team", team_names)
            points = st.number_input("Bonus Points", value=1, min_value=1, max_value=10)
        
        with col2:
            reason = st.text_input("Reason*", placeholder="e.g., Outstanding presentation")
            awarded_by = st.text_input("Awarded by*", placeholder="Admin name")
        
        if st.form_submit_button("Award Bonus Points", type="primary"):
            if selected_team and reason and awarded_by:
                success = scoring_service.add_bonus_points(
                    team_name=selected_team,
                    points=points,
                    reason=reason,
                    awarded_by=awarded_by
                )
                
                if success:
                    st.success(f"✅ Awarded {points} bonus points to {selected_team}!")
                    clear_cache()
                else:
                    st.error("❌ Failed to award bonus points")
            else:
                st.error("Please fill in all required fields (*)")

def show_import_interface(event_service):
    """Show data import interface"""
    st.markdown("### 📥 Import Attendance Data")
    
    # Load events for selection
    events_df = load_events()
    
    if len(events_df) == 0:
        st.warning("No events available. Create an event first.")
        return
    
    event_options = [(row['id'], f"{row['name']} ({row['event_date']})") for _, row in events_df.iterrows()]
    
    selected_event_id = st.selectbox(
        "Select Event",
        options=[opt[0] for opt in event_options],
        format_func=lambda x: next(opt[1] for opt in event_options if opt[0] == x)
    )
    
    st.markdown("#### CSV Format")
    st.info("""
    Expected CSV columns:
    - `team_name`: Team name (must match exactly)
    - `member_name`: Member name (must match exactly)  
    - `attended`: True/False or 1/0
    - `points_earned`: Optional, will use default if not provided
    """)
    
    uploaded_file = st.file_uploader("Upload attendance CSV", type=['csv'])
    
    if uploaded_file and selected_event_id:
        try:
            attendance_df = pd.read_csv(uploaded_file)
            
            st.markdown("#### Preview")
            st.dataframe(attendance_df.head(), use_container_width=True)
            
            if st.button("Import Attendance Data", type="primary"):
                with st.spinner("Importing attendance data..."):
                    success, message = event_service.bulk_import_attendance(selected_event_id, attendance_df)
                
                if success:
                    st.success(f"✅ {message}")
                    clear_cache()
                else:
                    st.error(f"❌ {message}")
                    
        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")

def show_system_interface(scoring_service):
    """Show system management interface"""
    st.markdown("### 🔧 System Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Data Validation")
        if st.button("🔍 Validate All Scores"):
            with st.spinner("Validating scores..."):
                validation_result = scoring_service.recalculate_all_scores()
            
            if validation_result['integrity_valid']:
                st.success("✅ All scores are valid and consistent")
            else:
                st.error("❌ Score validation failed:")
                for issue in validation_result['integrity_issues']:
                    st.error(f"• {issue}")
            
            st.json(validation_result['statistics'])
    
    with col2:
        st.markdown("#### Cache Management")
        if st.button("🔄 Clear All Caches"):
            clear_cache()
            st.success("✅ All caches cleared")
        
        st.markdown("#### Data Export")
        if st.button("📤 Export Team Data"):
            leaderboard_df = load_team_leaderboard()
            csv = leaderboard_df.to_csv(index=False)
            st.download_button(
                label="Download Team Data CSV",
                data=csv,
                file_name=f"cirqit_team_scores_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
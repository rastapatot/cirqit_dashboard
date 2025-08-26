#!/usr/bin/env python3
"""
Export all historical data from production database to local
This script creates a comprehensive export of all attendance data
"""

import pandas as pd
import sqlite3
from datetime import datetime

def export_production_data(production_db_path="cirqit_dashboard.db", export_prefix="production_export"):
    """Export all production data to CSV files for backup/sync"""
    
    try:
        conn = sqlite3.connect(production_db_path)
        
        print("🔄 Exporting production database to CSV files...")
        
        # Export all events
        events_df = pd.read_sql_query("""
            SELECT * FROM events ORDER BY event_date
        """, conn)
        events_file = f"{export_prefix}_events.csv"
        events_df.to_csv(events_file, index=False)
        print(f"✅ Events exported: {events_file} ({len(events_df)} records)")
        
        # Export all teams
        teams_df = pd.read_sql_query("""
            SELECT * FROM teams ORDER BY name
        """, conn)
        teams_file = f"{export_prefix}_teams.csv"
        teams_df.to_csv(teams_file, index=False)
        print(f"✅ Teams exported: {teams_file} ({len(teams_df)} records)")
        
        # Export all members
        members_df = pd.read_sql_query("""
            SELECT m.*, t.name as team_name 
            FROM members m 
            JOIN teams t ON m.team_id = t.id 
            ORDER BY t.name, m.name
        """, conn)
        members_file = f"{export_prefix}_members.csv"
        members_df.to_csv(members_file, index=False)
        print(f"✅ Members exported: {members_file} ({len(members_df)} records)")
        
        # Export all coaches
        coaches_df = pd.read_sql_query("""
            SELECT * FROM coaches ORDER BY name
        """, conn)
        coaches_file = f"{export_prefix}_coaches.csv"
        coaches_df.to_csv(coaches_file, index=False)
        print(f"✅ Coaches exported: {coaches_file} ({len(coaches_df)} records)")
        
        # Export ALL attendance records
        attendance_df = pd.read_sql_query("""
            SELECT 
                a.*,
                e.name as event_name,
                e.event_date,
                CASE 
                    WHEN a.member_id IS NOT NULL THEN m.name 
                    WHEN a.coach_id IS NOT NULL THEN c.name 
                END as attendee_name,
                CASE 
                    WHEN a.member_id IS NOT NULL THEN t.name 
                    WHEN a.coach_id IS NOT NULL THEN 'COACH'
                END as team_name,
                CASE 
                    WHEN a.member_id IS NOT NULL THEN 'MEMBER'
                    WHEN a.coach_id IS NOT NULL THEN 'COACH'
                END as attendee_type
            FROM attendance a
            JOIN events e ON a.event_id = e.id
            LEFT JOIN members m ON a.member_id = m.id
            LEFT JOIN teams t ON m.team_id = t.id
            LEFT JOIN coaches c ON a.coach_id = c.id
            WHERE a.attended = 1
            ORDER BY e.event_date, attendee_type, team_name, attendee_name
        """, conn)
        attendance_file = f"{export_prefix}_attendance.csv"
        attendance_df.to_csv(attendance_file, index=False)
        print(f"✅ Attendance exported: {attendance_file} ({len(attendance_df)} records)")
        
        # Export bonus points
        bonus_df = pd.read_sql_query("""
            SELECT b.*, t.name as team_name 
            FROM bonus_points b 
            JOIN teams t ON b.team_id = t.id 
            ORDER BY b.created_at
        """, conn)
        bonus_file = f"{export_prefix}_bonus_points.csv"
        bonus_df.to_csv(bonus_file, index=False)
        print(f"✅ Bonus points exported: {bonus_file} ({len(bonus_df)} records)")
        
        # Export comprehensive summary
        summary_df = pd.read_sql_query("""
            SELECT 
                e.name as event_name,
                e.event_date,
                COUNT(CASE WHEN a.member_id IS NOT NULL THEN 1 END) as member_attendance,
                COUNT(CASE WHEN a.coach_id IS NOT NULL THEN 1 END) as coach_attendance,
                COUNT(*) as total_attendance,
                SUM(CASE WHEN a.member_id IS NOT NULL THEN a.points_earned ELSE 0 END) as member_points,
                SUM(CASE WHEN a.coach_id IS NOT NULL THEN a.points_earned ELSE 0 END) as coach_points,
                SUM(a.points_earned) as total_points
            FROM events e
            LEFT JOIN attendance a ON e.id = a.event_id AND a.attended = 1
            GROUP BY e.id, e.name, e.event_date
            ORDER BY e.event_date
        """, conn)
        summary_file = f"{export_prefix}_summary.csv"
        summary_df.to_csv(summary_file, index=False)
        print(f"✅ Summary exported: {summary_file} ({len(summary_df)} records)")
        
        conn.close()
        
        # Print summary statistics
        print(f"\n📊 EXPORT SUMMARY:")
        print(f"Events: {len(events_df)}")
        print(f"Teams: {len(teams_df)}")
        print(f"Members: {len(members_df)}")
        print(f"Coaches: {len(coaches_df)}")
        print(f"Total Attendance Records: {len(attendance_df)}")
        print(f"Bonus Points: {len(bonus_df)}")
        
        total_member_attendance = len(attendance_df[attendance_df['attendee_type'] == 'MEMBER'])
        total_coach_attendance = len(attendance_df[attendance_df['attendee_type'] == 'COACH'])
        print(f"\nAttendance Breakdown:")
        print(f"Member Attendance: {total_member_attendance}")
        print(f"Coach Attendance: {total_coach_attendance}")
        print(f"Total: {total_member_attendance + total_coach_attendance}")
        
        return True
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False

if __name__ == "__main__":
    success = export_production_data()
    if success:
        print("\n🎯 All production data exported successfully!")
        print("Use the import script to sync this data to your local database.")
    else:
        print("\n💥 Export failed!")
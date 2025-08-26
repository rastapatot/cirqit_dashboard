#!/usr/bin/env python3
"""
Import production data from CSV exports to local database
This ensures local database matches production exactly
"""

import pandas as pd
import sqlite3
from datetime import datetime
import os

def import_production_data(local_db_path="cirqit_dashboard.db", export_prefix="production_export"):
    """Import production data from CSV exports to local database"""
    
    try:
        # Check if export files exist
        required_files = [
            f"{export_prefix}_events.csv",
            f"{export_prefix}_teams.csv", 
            f"{export_prefix}_members.csv",
            f"{export_prefix}_coaches.csv",
            f"{export_prefix}_attendance.csv",
            f"{export_prefix}_bonus_points.csv"
        ]
        
        missing_files = [f for f in required_files if not os.path.exists(f)]
        if missing_files:
            print(f"❌ Missing export files: {missing_files}")
            print("Run export_production_data.py first on your production system")
            return False
        
        conn = sqlite3.connect(local_db_path)
        cursor = conn.cursor()
        
        print("🔄 Importing production data to local database...")
        
        # Create backup of current local database
        backup_name = f"local_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        cursor.execute(f"VACUUM INTO '{backup_name}'")
        print(f"💾 Local database backed up as: {backup_name}")
        
        # Clear existing data (but keep structure)
        print("🧹 Clearing existing data...")
        cursor.execute("DELETE FROM attendance")
        cursor.execute("DELETE FROM bonus_points") 
        cursor.execute("DELETE FROM members")
        cursor.execute("DELETE FROM coaches")
        cursor.execute("DELETE FROM teams")
        cursor.execute("DELETE FROM events")
        
        # Reset auto-increment counters
        cursor.execute("DELETE FROM sqlite_sequence")
        
        # Import events
        events_df = pd.read_csv(f"{export_prefix}_events.csv")
        events_df.to_sql('events', conn, if_exists='append', index=False)
        print(f"✅ Events imported: {len(events_df)} records")
        
        # Import teams  
        teams_df = pd.read_csv(f"{export_prefix}_teams.csv")
        teams_df.to_sql('teams', conn, if_exists='append', index=False)
        print(f"✅ Teams imported: {len(teams_df)} records")
        
        # Import coaches
        coaches_df = pd.read_csv(f"{export_prefix}_coaches.csv")
        coaches_df.to_sql('coaches', conn, if_exists='append', index=False)
        print(f"✅ Coaches imported: {len(coaches_df)} records")
        
        # Import members
        members_df = pd.read_csv(f"{export_prefix}_members.csv")
        # Remove team_name column as it's not in the table
        if 'team_name' in members_df.columns:
            members_df = members_df.drop('team_name', axis=1)
        members_df.to_sql('members', conn, if_exists='append', index=False)
        print(f"✅ Members imported: {len(members_df)} records")
        
        # Import attendance records
        attendance_df = pd.read_csv(f"{export_prefix}_attendance.csv")
        # Keep only the database columns
        db_columns = ['id', 'event_id', 'member_id', 'coach_id', 'attended', 'points_earned', 'session_type', 'recorded_by', 'recorded_at']
        attendance_clean = attendance_df[db_columns].copy()
        attendance_clean.to_sql('attendance', conn, if_exists='append', index=False)
        print(f"✅ Attendance imported: {len(attendance_clean)} records")
        
        # Import bonus points
        bonus_df = pd.read_csv(f"{export_prefix}_bonus_points.csv")
        if 'team_name' in bonus_df.columns:
            bonus_df = bonus_df.drop('team_name', axis=1)
        bonus_df.to_sql('bonus_points', conn, if_exists='append', index=False)
        print(f"✅ Bonus points imported: {len(bonus_df)} records")
        
        conn.commit()
        
        # Verify import
        print("\n🔍 Verifying import...")
        cursor.execute("SELECT COUNT(*) FROM events")
        events_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM teams")
        teams_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM members")
        members_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM coaches")
        coaches_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE attended = 1")
        attendance_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bonus_points")
        bonus_count = cursor.fetchone()[0]
        
        print(f"📊 IMPORT VERIFICATION:")
        print(f"Events: {events_count}")
        print(f"Teams: {teams_count}")  
        print(f"Members: {members_count}")
        print(f"Coaches: {coaches_count}")
        print(f"Attendance Records: {attendance_count}")
        print(f"Bonus Points: {bonus_count}")
        
        # Show attendance breakdown
        cursor.execute("""
            SELECT 
                e.name,
                COUNT(CASE WHEN a.member_id IS NOT NULL THEN 1 END) as members,
                COUNT(CASE WHEN a.coach_id IS NOT NULL THEN 1 END) as coaches,
                COUNT(*) as total
            FROM events e
            LEFT JOIN attendance a ON e.id = a.event_id AND a.attended = 1
            GROUP BY e.id, e.name
            ORDER BY e.event_date
        """)
        
        print(f"\n📅 ATTENDANCE BY EVENT:")
        for row in cursor.fetchall():
            event_name, members, coaches, total = row
            print(f"{event_name}: {members} members, {coaches} coaches = {total} total")
        
        conn.close()
        
        print(f"\n🎯 Production data successfully imported to local database!")
        print(f"Local database now matches production with {attendance_count} total attendance records")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    success = import_production_data()
    if success:
        print("\n✅ Local database now matches production!")
    else:
        print("\n💥 Import failed!")
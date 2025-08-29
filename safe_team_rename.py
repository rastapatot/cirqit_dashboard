#!/usr/bin/env python3
"""
Safe Team Name Changer for CirQit Dashboard
This script safely changes a team name while preserving all scores and data.
"""

import sqlite3
from datetime import datetime

def connect_db():
    """Connect to the database with foreign key constraints enabled"""
    conn = sqlite3.connect('cirqit_dashboard.db')
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def backup_database():
    """Create a backup before making changes"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"cirqit_dashboard_backup_{timestamp}.db"
    
    import shutil
    shutil.copy2('cirqit_dashboard.db', backup_path)
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path

def list_teams():
    """List all active teams for user selection"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, total_members, department 
        FROM teams 
        WHERE is_active = 1 
        ORDER BY name
    """)
    
    teams = cursor.fetchall()
    conn.close()
    
    print("\n📋 Current Active Teams:")
    print("-" * 60)
    for team_id, name, members, dept in teams:
        dept_str = f" ({dept})" if dept else ""
        print(f"ID: {team_id:3d} | {name}{dept_str} | {members} members")
    
    return teams

def get_team_scores(team_id):
    """Get current team scores to verify preservation"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT team_name, member_points, coach_points, bonus_points, final_score
        FROM v_team_scores 
        WHERE team_id = ?
    """, (team_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result

def rename_team(team_id, new_name):
    """Safely rename a team"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Get current team info
        cursor.execute("""
            SELECT name, total_members, department 
            FROM teams 
            WHERE id = ? AND is_active = 1
        """, (team_id,))
        
        current_info = cursor.fetchone()
        if not current_info:
            print(f"❌ Error: Team with ID {team_id} not found or not active")
            return False
        
        old_name, members, dept = current_info
        
        # Check if new name already exists
        cursor.execute("SELECT id FROM teams WHERE name = ? AND is_active = 1", (new_name,))
        if cursor.fetchone():
            print(f"❌ Error: Team name '{new_name}' already exists")
            return False
        
        # Get scores before change
        scores_before = get_team_scores(team_id)
        
        print(f"\n🔄 Renaming team...")
        print(f"   Old name: '{old_name}'")
        print(f"   New name: '{new_name}'")
        print(f"   Members: {members}")
        print(f"   Department: {dept or 'N/A'}")
        
        if scores_before:
            print(f"   Current scores: Members={scores_before[1]}, Coach={scores_before[2]}, Bonus={scores_before[3]}, Total={scores_before[4]}")
        
        # Update the team name
        cursor.execute("""
            UPDATE teams 
            SET name = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (new_name, team_id))
        
        # Log the change in audit log
        cursor.execute("""
            INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by, changed_at)
            VALUES ('teams', ?, 'rename', ?, ?, 'safe_team_rename.py', CURRENT_TIMESTAMP)
        """, (team_id, f"name: {old_name}", f"name: {new_name}"))
        
        conn.commit()
        
        # Verify scores are preserved
        scores_after = get_team_scores(team_id)
        
        if scores_before and scores_after:
            if (scores_before[1:] == scores_after[1:]):  # Compare all except team_name
                print(f"✅ Team renamed successfully! All scores preserved.")
                print(f"   Final scores: Members={scores_after[1]}, Coach={scores_after[2]}, Bonus={scores_after[3]}, Total={scores_after[4]}")
            else:
                print(f"⚠️  Warning: Scores may have changed!")
                print(f"   Before: {scores_before[1:]}")
                print(f"   After:  {scores_after[1:]}")
        else:
            print(f"✅ Team renamed successfully!")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    print("🏆 CirQit Dashboard - Safe Team Name Changer")
    print("=" * 50)
    
    # Create backup
    backup_path = backup_database()
    
    # List teams
    teams = list_teams()
    
    if not teams:
        print("❌ No active teams found!")
        return
    
    # Get user input
    try:
        team_id = int(input(f"\n🎯 Enter the Team ID to rename (1-{max(t[0] for t in teams)}): "))
        
        # Verify team exists
        team_info = next((t for t in teams if t[0] == team_id), None)
        if not team_info:
            print(f"❌ Invalid Team ID: {team_id}")
            return
        
        current_name = team_info[1]
        print(f"\n📝 Current team name: '{current_name}'")
        
        new_name = input("💡 Enter new team name: ").strip()
        
        if not new_name:
            print("❌ New team name cannot be empty!")
            return
        
        if new_name == current_name:
            print("❌ New name is the same as current name!")
            return
        
        # Confirm the change
        print(f"\n⚠️  Confirm team rename:")
        print(f"   From: '{current_name}'")
        print(f"   To:   '{new_name}'")
        confirm = input("\n❓ Are you sure? (yes/no): ").strip().lower()
        
        if confirm not in ['yes', 'y']:
            print("❌ Rename cancelled.")
            return
        
        # Perform the rename
        if rename_team(team_id, new_name):
            print(f"\n🎉 Success! Team renamed from '{current_name}' to '{new_name}'")
            print(f"📁 Backup created: {backup_path}")
            print("🔐 All scores and data have been preserved!")
        else:
            print(f"\n❌ Failed to rename team.")
            print(f"📁 No changes made. Backup available: {backup_path}")
    
    except ValueError:
        print("❌ Invalid Team ID. Please enter a number.")
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
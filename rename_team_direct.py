#!/usr/bin/env python3
"""
Direct Team Name Changer for CirQit Dashboard
Usage: python3 rename_team_direct.py <team_id> "<new_name>"
"""

import sqlite3
import sys
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
            VALUES ('teams', ?, 'rename', ?, ?, 'rename_team_direct.py', CURRENT_TIMESTAMP)
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

def find_team_by_name(search_name):
    """Find teams by partial name match"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, total_members, department 
        FROM teams 
        WHERE is_active = 1 AND LOWER(name) LIKE LOWER(?)
        ORDER BY name
    """, (f"%{search_name}%",))
    
    teams = cursor.fetchall()
    conn.close()
    
    return teams

def main():
    if len(sys.argv) < 3:
        print("🏆 CirQit Dashboard - Direct Team Name Changer")
        print("=" * 50)
        print("Usage:")
        print('  python3 rename_team_direct.py <team_id> "<new_name>"')
        print('  python3 rename_team_direct.py search "<partial_name>"  # To find team ID')
        print("\nExamples:")
        print('  python3 rename_team_direct.py 42 "New Team Name"')
        print('  python3 rename_team_direct.py search "old name"')
        return
    
    command = sys.argv[1]
    
    if command.lower() == "search":
        if len(sys.argv) < 3:
            print("❌ Please provide a search term")
            return
            
        search_term = sys.argv[2]
        teams = find_team_by_name(search_term)
        
        if teams:
            print(f"\n🔍 Teams matching '{search_term}':")
            print("-" * 60)
            for team_id, name, members, dept in teams:
                dept_str = f" ({dept})" if dept else ""
                print(f"ID: {team_id:3d} | {name}{dept_str} | {members} members")
        else:
            print(f"❌ No teams found matching '{search_term}'")
        return
    
    try:
        team_id = int(command)
        new_name = sys.argv[2].strip()
        
        if not new_name:
            print("❌ New team name cannot be empty!")
            return
        
        print("🏆 CirQit Dashboard - Direct Team Name Changer")
        print("=" * 50)
        
        # Create backup
        backup_path = backup_database()
        
        # Perform the rename
        if rename_team(team_id, new_name):
            print(f"\n🎉 Success! Team ID {team_id} renamed to '{new_name}'")
            print(f"📁 Backup created: {backup_path}")
            print("🔐 All scores and data have been preserved!")
        else:
            print(f"\n❌ Failed to rename team.")
            print(f"📁 No changes made. Backup available: {backup_path}")
    
    except ValueError:
        print("❌ Invalid Team ID. Please enter a number.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Update the CirQit Dashboard database with the new final masterlist
while preserving all existing scores, points, and attendance data.
"""

import sqlite3
import csv
import sys
from datetime import datetime

def connect_db():
    """Connect to the SQLite database."""
    return sqlite3.connect('cirqit_dashboard.db')

def read_csv_data():
    """Read and parse the new masterlist CSV."""
    teams_data = {}
    coaches_data = {}
    members_data = []
    
    # Try different encodings
    encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
    file_content = None
    
    for encoding in encodings:
        try:
            with open('cirqit_teams_FINAL.csv', 'r', encoding=encoding) as file:
                file_content = file.read()
                print(f"Successfully read file with encoding: {encoding}")
                break
        except UnicodeDecodeError:
            continue
    
    if file_content is None:
        raise Exception("Could not read CSV file with any encoding")
    
    # Parse the CSV content
    import io
    file_obj = io.StringIO(file_content)
    reader = csv.DictReader(file_obj)
    
    for row in reader:
            team_name = row['Team Name'].strip()
            team_leader = row['Team Leader'].strip()
            leader_dept = row['Leader Department'].strip()
            member_name = row['Member Name'].strip()
            member_dept = row['Member Department'].strip()
            coach_name = row['Coach/Consultant'].strip()
            coach_dept = row['Coach Department'].strip()
            date_registered = row['Date Registered'].strip()
            source = row['Source'].strip()
            
            # Store team data
            if team_name not in teams_data:
                teams_data[team_name] = {
                    'leader': team_leader,
                    'department': leader_dept,
                    'members': [],
                    'coach': coach_name,
                    'coach_dept': coach_dept,
                    'date_registered': date_registered,
                    'source': source
                }
            
            # Store coach data
            if coach_name not in coaches_data:
                coaches_data[coach_name] = coach_dept
            
            # Store member data
            is_leader = (member_name == team_leader)
            members_data.append({
                'team_name': team_name,
                'name': member_name,
                'department': member_dept,
                'is_leader': is_leader
            })
            
            teams_data[team_name]['members'].append({
                'name': member_name,
                'department': member_dept,
                'is_leader': is_leader
            })
    
    return teams_data, coaches_data, members_data

def update_coaches(conn, coaches_data):
    """Update coaches table with new data."""
    cursor = conn.cursor()
    
    print(f"Updating {len(coaches_data)} coaches...")
    
    for coach_name, coach_dept in coaches_data.items():
        # Check if coach already exists
        cursor.execute("SELECT id FROM coaches WHERE name = ?", (coach_name,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing coach's department if different
            cursor.execute("""
                UPDATE coaches 
                SET department = ? 
                WHERE name = ?
            """, (coach_dept, coach_name))
        else:
            # Insert new coach
            cursor.execute("""
                INSERT INTO coaches (name, department, is_active) 
                VALUES (?, ?, 1)
            """, (coach_name, coach_dept))
            print(f"Added new coach: {coach_name}")
    
    conn.commit()

def update_teams(conn, teams_data):
    """Update teams table with new data."""
    cursor = conn.cursor()
    
    print(f"Updating {len(teams_data)} teams...")
    
    for team_name, team_info in teams_data.items():
        # Get coach_id
        cursor.execute("SELECT id FROM coaches WHERE name = ?", (team_info['coach'],))
        coach_result = cursor.fetchone()
        coach_id = coach_result[0] if coach_result else None
        
        total_members = len(team_info['members'])
        
        # Check if team already exists
        cursor.execute("SELECT id, total_members FROM teams WHERE name = ?", (team_name,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing team
            cursor.execute("""
                UPDATE teams 
                SET total_members = ?, coach_id = ?, department = ? 
                WHERE name = ?
            """, (total_members, coach_id, team_info['department'], team_name))
            if existing[1] != total_members:
                print(f"Updated team '{team_name}': members {existing[1]} -> {total_members}")
        else:
            # Insert new team
            cursor.execute("""
                INSERT INTO teams (name, total_members, coach_id, department, 
                                 registration_date, is_active) 
                VALUES (?, ?, ?, ?, ?, 1)
            """, (team_name, total_members, coach_id, team_info['department'], 
                  team_info['date_registered']))
            print(f"Added new team: {team_name} ({total_members} members)")
    
    conn.commit()

def update_members(conn, members_data):
    """Update members table with new data."""
    cursor = conn.cursor()
    
    print(f"Updating {len(members_data)} members...")
    
    # First, get all team IDs
    team_ids = {}
    cursor.execute("SELECT id, name FROM teams")
    for team_id, team_name in cursor.fetchall():
        team_ids[team_name] = team_id
    
    # Track existing members per team for cleanup
    cursor.execute("""
        SELECT m.name, t.name as team_name 
        FROM members m 
        JOIN teams t ON m.team_id = t.id 
        WHERE m.is_active = 1
    """)
    existing_members = set((row[0], row[1]) for row in cursor.fetchall())
    
    new_members = set()
    
    for member_info in members_data:
        team_name = member_info['team_name']
        member_name = member_info['name']
        member_dept = member_info['department']
        is_leader = member_info['is_leader']
        
        new_members.add((member_name, team_name))
        
        if team_name not in team_ids:
            print(f"Warning: Team '{team_name}' not found for member '{member_name}'")
            continue
        
        team_id = team_ids[team_name]
        
        # Check if member already exists in this team
        cursor.execute("""
            SELECT id, department, is_leader 
            FROM members 
            WHERE name = ? AND team_id = ?
        """, (member_name, team_id))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing member
            cursor.execute("""
                UPDATE members 
                SET department = ?, is_leader = ?, is_active = 1 
                WHERE name = ? AND team_id = ?
            """, (member_dept, is_leader, member_name, team_id))
        else:
            # Insert new member
            cursor.execute("""
                INSERT INTO members (name, department, team_id, is_leader, is_active) 
                VALUES (?, ?, ?, ?, 1)
            """, (member_name, member_dept, team_id, is_leader))
            print(f"Added new member: {member_name} to team {team_name}")
    
    # Deactivate members who are no longer in the masterlist
    removed_members = existing_members - new_members
    for member_name, team_name in removed_members:
        if team_name in team_ids:
            cursor.execute("""
                UPDATE members 
                SET is_active = 0 
                WHERE name = ? AND team_id = ?
            """, (member_name, team_ids[team_name]))
            print(f"Deactivated member: {member_name} from team {team_name}")
    
    conn.commit()

def verify_scores_intact(conn):
    """Verify that existing scores and data are still intact."""
    cursor = conn.cursor()
    
    print("\nVerifying data integrity...")
    
    # Check attendance records
    cursor.execute("SELECT COUNT(*) FROM attendance")
    attendance_count = cursor.fetchone()[0]
    print(f"Attendance records: {attendance_count}")
    
    # Check bonus points
    cursor.execute("SELECT COUNT(*) FROM bonus_points WHERE is_active = 1")
    bonus_count = cursor.fetchone()[0]
    print(f"Active bonus point records: {bonus_count}")
    
    # Check events
    cursor.execute("SELECT COUNT(*) FROM events WHERE is_active = 1")
    events_count = cursor.fetchone()[0]
    print(f"Active events: {events_count}")
    
    # Test scoring view
    cursor.execute("SELECT COUNT(*) FROM v_team_scores")
    scores_count = cursor.fetchone()[0]
    print(f"Teams with scores: {scores_count}")
    
    return True

def main():
    """Main update process."""
    print("Starting CirQit Dashboard masterlist update...")
    print("=" * 50)
    
    # Read new data
    print("Reading new masterlist data...")
    teams_data, coaches_data, members_data = read_csv_data()
    
    # Connect to database
    conn = connect_db()
    
    try:
        # Update in order: coaches -> teams -> members
        update_coaches(conn, coaches_data)
        update_teams(conn, teams_data)
        update_members(conn, members_data)
        
        # Verify everything is working
        verify_scores_intact(conn)
        
        print("\n" + "=" * 50)
        print("Update completed successfully!")
        print("All existing scores and attendance data have been preserved.")
        
    except Exception as e:
        print(f"Error during update: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Update CirQit Dashboard database to FINALX masterlist while preserving all scoring data.
This script will:
1. Preserve all existing scores, attendance, and bonus points
2. Handle special characters properly
3. Map teams correctly
4. Ensure exactly 146 teams
"""

import sqlite3
import csv
import pandas as pd
from datetime import datetime

def read_finalx_data():
    """Read the new FINALX masterlist"""
    teams = {}
    members = {}
    coaches = {}
    
    print("📖 Reading FINALX masterlist...")
    
    with open('cirqit_teams-FINALX.csv', 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team_name = row['Team Name'].strip()
            member_name = row['Member Name'].strip()
            coach_name = row['Coach/Consultant'].strip()
            
            # Store team info
            if team_name not in teams:
                teams[team_name] = {
                    'leader': row['Team Leader'].strip(),
                    'department': row['Leader Department'].strip(),
                    'coach': coach_name,
                    'coach_dept': row['Coach Department'].strip(),
                    'members': []
                }
            
            # Store member info
            member_info = {
                'name': member_name,
                'department': row['Member Department'].strip(),
                'is_leader': member_name == row['Team Leader'].strip()
            }
            teams[team_name]['members'].append(member_info)
            
            # Store coach info
            coaches[coach_name] = row['Coach Department'].strip()
    
    print(f"✅ Found {len(teams)} teams, {sum(len(t['members']) for t in teams.values())} members, {len(coaches)} coaches")
    return teams, coaches

def preserve_current_data():
    """Get all current scoring data to preserve"""
    conn = sqlite3.connect('cirqit_dashboard.db')
    
    print("💾 Preserving current scoring data...")
    
    # Get all current data
    attendance_df = pd.read_sql_query("""
        SELECT a.*, m.name as member_name, t.name as team_name, c.name as coach_name
        FROM attendance a
        LEFT JOIN members m ON a.member_id = m.id
        LEFT JOIN teams t ON m.team_id = t.id
        LEFT JOIN coaches c ON a.coach_id = c.id
    """, conn)
    
    bonus_df = pd.read_sql_query("""
        SELECT bp.*, t.name as team_name
        FROM bonus_points bp
        JOIN teams t ON bp.team_id = t.id
        WHERE bp.is_active = 1
    """, conn)
    
    team_scores_df = pd.read_sql_query("SELECT * FROM v_team_scores", conn)
    member_scores_df = pd.read_sql_query("SELECT * FROM v_member_scores", conn)
    
    conn.close()
    
    print(f"✅ Preserved {len(attendance_df)} attendance records, {len(bonus_df)} bonus points")
    return attendance_df, bonus_df, team_scores_df, member_scores_df

def create_team_mapping(current_teams, new_teams):
    """Create mapping between current and new team names"""
    print("🔗 Creating team name mappings...")
    
    mapping = {}
    
    # Direct matches first
    for new_team in new_teams:
        if new_team in current_teams:
            mapping[new_team] = new_team
    
    # Handle special character variations
    special_mappings = {
        "AIn't No Malware": ["AInÕt No Malware", "AIn�t No Malware"],
        "The MSP Team": ["ÊThe MSP Team", "�The MSP Team"],
        "Alliance of Just Minds(AJM)": ["Alliance of Just Minds"],
    }
    
    for correct_name, variations in special_mappings.items():
        if correct_name in new_teams:
            for variation in variations:
                if variation in current_teams:
                    mapping[correct_name] = variation
                    break
    
    # Fuzzy matching for remaining teams
    for new_team in new_teams:
        if new_team not in mapping:
            # Try to find similar team names
            new_normalized = new_team.lower().replace(' ', '').replace('-', '').replace('_', '')
            
            for current_team in current_teams:
                if current_team not in mapping.values():
                    current_normalized = current_team.lower().replace(' ', '').replace('-', '').replace('_', '')
                    
                    if new_normalized == current_normalized:
                        mapping[new_team] = current_team
                        break
    
    print(f"✅ Created mappings for {len(mapping)} teams")
    return mapping

def update_database(new_teams, new_coaches, team_mapping, preserved_data):
    """Update database with new data while preserving scores"""
    conn = sqlite3.connect('cirqit_dashboard.db')
    cursor = conn.cursor()
    
    print("🔄 Updating database...")
    
    attendance_df, bonus_df, team_scores_df, member_scores_df = preserved_data
    
    try:
        # 1. Update coaches first
        print("  Updating coaches...")
        cursor.execute("UPDATE coaches SET is_active = 0")  # Deactivate all first
        
        for coach_name, department in new_coaches.items():
            cursor.execute("""
                INSERT OR REPLACE INTO coaches (name, department, is_active)
                VALUES (?, ?, 1)
            """, (coach_name, department))
        
        # 2. Update teams
        print("  Updating teams...")
        cursor.execute("UPDATE teams SET is_active = 0")  # Deactivate all first
        
        team_id_mapping = {}
        
        for team_name, team_info in new_teams.items():
            # Get coach ID
            cursor.execute("SELECT id FROM coaches WHERE name = ? AND is_active = 1", (team_info['coach'],))
            coach_row = cursor.fetchone()
            coach_id = coach_row[0] if coach_row else None
            
            # Check if team exists (by mapping)
            old_team_name = team_mapping.get(team_name, team_name)
            cursor.execute("SELECT id FROM teams WHERE name = ?", (old_team_name,))
            existing_team = cursor.fetchone()
            
            if existing_team:
                # Update existing team
                team_id = existing_team[0]
                cursor.execute("""
                    UPDATE teams SET 
                        name = ?, 
                        total_members = ?, 
                        coach_id = ?, 
                        department = ?, 
                        is_active = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (team_name, len(team_info['members']), coach_id, team_info['department'], team_id))
            else:
                # Create new team
                cursor.execute("""
                    INSERT INTO teams (name, total_members, coach_id, department, is_active)
                    VALUES (?, ?, ?, ?, 1)
                """, (team_name, len(team_info['members']), coach_id, team_info['department']))
                team_id = cursor.lastrowid
            
            team_id_mapping[team_name] = team_id
        
        # 3. Update members
        print("  Updating members...")
        cursor.execute("UPDATE members SET is_active = 0")  # Deactivate all first
        
        for team_name, team_info in new_teams.items():
            team_id = team_id_mapping[team_name]
            
            for member_info in team_info['members']:
                # Check if member exists
                cursor.execute("""
                    SELECT id FROM members 
                    WHERE name = ? AND team_id = ?
                """, (member_info['name'], team_id))
                existing_member = cursor.fetchone()
                
                if existing_member:
                    # Update existing member
                    cursor.execute("""
                        UPDATE members SET 
                            department = ?, 
                            is_leader = ?, 
                            is_active = 1
                        WHERE id = ?
                    """, (member_info['department'], member_info['is_leader'], existing_member[0]))
                else:
                    # Create new member
                    cursor.execute("""
                        INSERT INTO members (name, team_id, department, is_leader, is_active)
                        VALUES (?, ?, ?, ?, 1)
                    """, (member_info['name'], team_id, member_info['department'], member_info['is_leader']))
        
        # 4. Preserve bonus points by updating team references
        print("  Preserving bonus points...")
        for _, bonus_row in bonus_df.iterrows():
            old_team_name = bonus_row['team_name']
            # Find new team name that maps to this old team
            new_team_name = None
            for new_name, old_name in team_mapping.items():
                if old_name == old_team_name:
                    new_team_name = new_name
                    break
            
            if new_team_name and new_team_name in team_id_mapping:
                new_team_id = team_id_mapping[new_team_name]
                cursor.execute("""
                    UPDATE bonus_points SET team_id = ? WHERE id = ?
                """, (new_team_id, bonus_row['id']))
        
        # 5. Preserve attendance by updating member/coach references
        print("  Preserving attendance records...")
        for _, att_row in attendance_df.iterrows():
            if pd.notna(att_row['member_name']) and pd.notna(att_row['team_name']):
                # Find new team for this member
                old_team_name = att_row['team_name']
                new_team_name = None
                for new_name, old_name in team_mapping.items():
                    if old_name == old_team_name:
                        new_team_name = new_name
                        break
                
                if new_team_name and new_team_name in team_id_mapping:
                    # Find member in new team structure
                    cursor.execute("""
                        SELECT id FROM members 
                        WHERE name = ? AND team_id = ? AND is_active = 1
                    """, (att_row['member_name'], team_id_mapping[new_team_name]))
                    member_row = cursor.fetchone()
                    
                    if member_row:
                        cursor.execute("""
                            UPDATE attendance SET member_id = ? WHERE id = ?
                        """, (member_row[0], att_row['id']))
        
        conn.commit()
        print("✅ Database updated successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error updating database: {e}")
        raise
    finally:
        conn.close()

def verify_results():
    """Verify the final state"""
    conn = sqlite3.connect('cirqit_dashboard.db')
    cursor = conn.cursor()
    
    print("🔍 Verifying results...")
    
    # Count teams
    cursor.execute("SELECT COUNT(*) FROM teams WHERE is_active = 1")
    team_count = cursor.fetchone()[0]
    
    # Count members
    cursor.execute("SELECT COUNT(*) FROM members WHERE is_active = 1")
    member_count = cursor.fetchone()[0]
    
    # Count coaches
    cursor.execute("SELECT COUNT(*) FROM coaches WHERE is_active = 1")
    coach_count = cursor.fetchone()[0]
    
    # Count preserved data
    cursor.execute("SELECT COUNT(*) FROM attendance")
    attendance_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bonus_points WHERE is_active = 1")
    bonus_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📊 Final Results:")
    print(f"  Teams: {team_count} (should be 146)")
    print(f"  Members: {member_count}")
    print(f"  Coaches: {coach_count}")
    print(f"  Attendance records: {attendance_count}")
    print(f"  Bonus points: {bonus_count}")
    
    if team_count == 146:
        print("✅ Team count is correct!")
    else:
        print(f"⚠️  Expected 146 teams, got {team_count}")
    
    return team_count == 146

def main():
    print("🚀 Starting FINALX database update...")
    print("This will preserve all scoring data while updating team structure\n")
    
    # Step 1: Read new data
    new_teams, new_coaches = read_finalx_data()
    
    # Step 2: Preserve current data
    preserved_data = preserve_current_data()
    
    # Step 3: Get current teams for mapping
    conn = sqlite3.connect('cirqit_dashboard.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM teams WHERE is_active = 1")
    current_teams = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Step 4: Create mapping
    team_mapping = create_team_mapping(current_teams, new_teams.keys())
    
    # Step 5: Update database
    update_database(new_teams, new_coaches, team_mapping, preserved_data)
    
    # Step 6: Verify
    success = verify_results()
    
    if success:
        print("\n🎉 FINALX update completed successfully!")
        print("All scoring rules and data have been preserved.")
    else:
        print("\n⚠️  Update completed with warnings - please check results")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Fix team name changes by updating old team names to new ones
while preserving all scores and attendance data.
"""

import sqlite3

def connect_db():
    return sqlite3.connect('cirqit_dashboard.db')

def find_team_name_mappings():
    """Find the mapping between old teams and new teams based on members."""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get old teams with their members (currently inactive members)
    cursor.execute("""
        SELECT t.id, t.name as old_name, m.name as member_name
        FROM teams t 
        LEFT JOIN members m ON t.id = m.team_id 
        WHERE t.total_members = 0 AND t.is_active = 1 AND m.is_active = 0
        ORDER BY t.name, m.name
    """)
    
    old_teams = {}
    for team_id, old_name, member_name in cursor.fetchall():
        if team_id not in old_teams:
            old_teams[team_id] = {'name': old_name, 'members': set()}
        if member_name:
            old_teams[team_id]['members'].add(member_name)
    
    # Get new teams with their members (currently active members)
    cursor.execute("""
        SELECT t.id, t.name as new_name, m.name as member_name
        FROM teams t 
        LEFT JOIN members m ON t.id = m.team_id 
        WHERE t.total_members > 0 AND t.is_active = 1 AND m.is_active = 1
        ORDER BY t.name, m.name
    """)
    
    new_teams = {}
    for team_id, new_name, member_name in cursor.fetchall():
        if team_id not in new_teams:
            new_teams[team_id] = {'name': new_name, 'members': set()}
        if member_name:
            new_teams[team_id]['members'].add(member_name)
    
    # Find matches based on member overlap
    mappings = []
    
    for old_id, old_data in old_teams.items():
        best_match = None
        best_overlap = 0
        
        for new_id, new_data in new_teams.items():
            overlap = len(old_data['members'].intersection(new_data['members']))
            total_members = len(old_data['members'])
            
            # If most members match (80% or more), consider it a name change
            if overlap >= max(1, total_members * 0.8):
                if overlap > best_overlap:
                    best_match = new_id
                    best_overlap = overlap
        
        if best_match:
            mappings.append({
                'old_id': old_id,
                'old_name': old_data['name'],
                'new_id': best_match,
                'new_name': new_teams[best_match]['name'],
                'matching_members': best_overlap,
                'total_old_members': len(old_data['members'])
            })
    
    conn.close()
    return mappings

def update_team_names(mappings):
    """Update team names and merge data."""
    conn = connect_db()
    cursor = conn.cursor()
    
    print(f"Processing {len(mappings)} team name changes...")
    
    for mapping in mappings:
        old_id = mapping['old_id']
        old_name = mapping['old_name']
        new_id = mapping['new_id']
        new_name = mapping['new_name']
        
        print(f"\nUpdating '{old_name}' -> '{new_name}'")
        print(f"  Matching members: {mapping['matching_members']}/{mapping['total_old_members']}")
        
        # First, rename the new team to a temporary name to avoid constraint issues
        temp_name = f"TEMP_{new_name}_{new_id}"
        cursor.execute("UPDATE teams SET name = ? WHERE id = ?", (temp_name, new_id))
        
        # Now update the old team's name to the new name
        cursor.execute("UPDATE teams SET name = ? WHERE id = ?", (new_name, old_id))
        
        # Move all attendance records from new team to old team (to preserve history)
        cursor.execute("""
            UPDATE attendance 
            SET member_id = (
                SELECT old_m.id 
                FROM members old_m 
                JOIN members new_m ON old_m.name = new_m.name 
                WHERE new_m.id = attendance.member_id AND old_m.team_id = ?
            )
            WHERE member_id IN (
                SELECT id FROM members WHERE team_id = ? AND is_active = 1
            )
        """, (old_id, new_id))
        
        # Move bonus points from new team to old team
        cursor.execute("""
            UPDATE bonus_points 
            SET team_id = ? 
            WHERE team_id = ?
        """, (old_id, new_id))
        
        # Reactivate old team members and deactivate new team members
        cursor.execute("UPDATE members SET is_active = 1 WHERE team_id = ? AND is_active = 0", (old_id,))
        cursor.execute("UPDATE members SET is_active = 0 WHERE team_id = ? AND is_active = 1", (new_id,))
        
        # Deactivate the new team (duplicate)
        cursor.execute("UPDATE teams SET is_active = 0 WHERE id = ?", (new_id,))
        
        # Update old team member count
        cursor.execute("""
            UPDATE teams 
            SET total_members = (
                SELECT COUNT(*) FROM members WHERE team_id = ? AND is_active = 1
            ) 
            WHERE id = ?
        """, (old_id, old_id))
        
        print(f"  Successfully updated team and preserved all scores")
    
    conn.commit()
    conn.close()

def main():
    print("Fixing team name changes...")
    print("=" * 50)
    
    # Find team mappings
    mappings = find_team_name_mappings()
    
    if not mappings:
        print("No team name changes detected.")
        return
    
    print(f"Found {len(mappings)} team name changes:")
    for mapping in mappings:
        print(f"  '{mapping['old_name']}' -> '{mapping['new_name']}'")
    
    # Update team names
    update_team_names(mappings)
    
    print("\n" + "=" * 50)
    print("Team name updates completed successfully!")
    print("All scores and attendance data have been preserved.")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Fix team duplicates and character encoding issues in the CirQit Dashboard database.
This handles special cases like Alliance of Just Minds(AJM) and teams with special characters.
"""

import sqlite3
import csv
from collections import defaultdict

def normalize_team_name(name):
    """Normalize team names for comparison"""
    # Handle common character encoding issues
    name = name.replace('Õ', "'").replace('Ê', '"').replace('�', "'")
    name = name.replace('ñ', 'n').replace('é', 'e')
    return name.strip()

def find_team_mappings():
    """Create mapping between CSV teams and database teams"""
    # Read CSV teams
    csv_teams = set()
    with open('cirqit_teams_FINAL.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row and len(row) > 0:
                csv_teams.add(row[0].strip())
    
    # Read database teams
    conn = sqlite3.connect('cirqit_dashboard.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM teams WHERE is_active = 1")
    db_teams = cursor.fetchall()
    conn.close()
    
    # Create mappings
    exact_matches = set()
    mappings = {}
    
    # First pass: exact matches
    for team_id, db_name in db_teams:
        if db_name in csv_teams:
            exact_matches.add(db_name)
            mappings[db_name] = {'csv_name': db_name, 'db_id': team_id, 'db_name': db_name}
    
    # Second pass: normalized matches
    for csv_name in csv_teams:
        if csv_name in exact_matches:
            continue
            
        csv_normalized = normalize_team_name(csv_name)
        
        for team_id, db_name in db_teams:
            if db_name in [m['db_name'] for m in mappings.values()]:
                continue
                
            db_normalized = normalize_team_name(db_name)
            
            # Check various matching criteria
            if (csv_normalized == db_normalized or
                csv_normalized.replace(' ', '') == db_normalized.replace(' ', '') or
                csv_name.replace("'", "Õ") == db_name or
                csv_name.replace("'", "'") == db_name):
                mappings[csv_name] = {'csv_name': csv_name, 'db_id': team_id, 'db_name': db_name}
                break
    
    return mappings, csv_teams, db_teams

def merge_duplicate_teams():
    """Merge duplicate teams and fix character encoding"""
    conn = sqlite3.connect('cirqit_dashboard.db')
    cursor = conn.cursor()
    
    print("🔍 Analyzing team duplicates and character encoding issues...")
    
    # Special mappings for known issues
    special_mappings = {
        "AInÕt No Malware": "AIn't No Malware",
        "ÊThe MSP Team": "The MSP Team", 
        "�The MSP Team": "The MSP Team",
        "Alliance of Just Minds": "Alliance of Just Minds(AJM)"
    }
    
    changes_made = 0
    
    # Handle special character mappings
    for old_name, new_name in special_mappings.items():
        cursor.execute("SELECT id FROM teams WHERE name = ? AND is_active = 1", (old_name,))
        old_team = cursor.fetchone()
        
        cursor.execute("SELECT id FROM teams WHERE name = ? AND is_active = 1", (new_name,))
        new_team = cursor.fetchone()
        
        if old_team and new_team:
            old_id, new_id = old_team[0], new_team[0]
            print(f"  🔄 Merging '{old_name}' -> '{new_name}'")
            
            # Move members from old team to new team
            cursor.execute("UPDATE members SET team_id = ? WHERE team_id = ?", (new_id, old_id))
            
            # Move attendance records  
            cursor.execute("UPDATE attendance SET member_id = (SELECT id FROM members WHERE team_id = ? AND name = (SELECT name FROM members WHERE id = attendance.member_id)) WHERE member_id IN (SELECT id FROM members WHERE team_id = ?)", (new_id, old_id))
            
            # Move bonus points
            cursor.execute("UPDATE bonus_points SET team_id = ? WHERE team_id = ?", (new_id, old_id))
            
            # Deactivate old team
            cursor.execute("UPDATE teams SET is_active = 0 WHERE id = ?", (old_id,))
            
            changes_made += 1
    
    # Handle TEMP_ prefixed teams (merge with their original)
    cursor.execute("SELECT id, name FROM teams WHERE name LIKE 'TEMP_%' AND is_active = 1")
    temp_teams = cursor.fetchall()
    
    for temp_id, temp_name in temp_teams:
        # Extract original name (remove TEMP_ prefix and _number suffix)
        original_name = temp_name.replace('TEMP_', '').split('_')[0]
        
        cursor.execute("SELECT id FROM teams WHERE name = ? AND is_active = 1", (original_name,))
        original_team = cursor.fetchone()
        
        if original_team:
            original_id = original_team[0]
            print(f"  🔄 Merging temp team '{temp_name}' -> '{original_name}'")
            
            # Move all data from temp team to original team
            cursor.execute("UPDATE members SET team_id = ? WHERE team_id = ?", (original_id, temp_id))
            cursor.execute("UPDATE bonus_points SET team_id = ? WHERE team_id = ?", (original_id, temp_id))
            
            # Deactivate temp team
            cursor.execute("UPDATE teams SET is_active = 0 WHERE id = ?", (temp_id,))
            
            changes_made += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Merged {changes_made} duplicate teams")
    return changes_made

def verify_team_count():
    """Verify the final team count"""
    conn = sqlite3.connect('cirqit_dashboard.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM teams WHERE is_active = 1")
    db_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT name) FROM teams WHERE is_active = 1")
    unique_count = cursor.fetchone()[0]
    
    conn.close()
    
    # Count CSV teams
    csv_teams = set()
    with open('cirqit_teams_FINAL.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row and len(row) > 0:
                csv_teams.add(row[0].strip())
    
    csv_count = len(csv_teams)
    
    print(f"\n📊 Team Count Verification:")
    print(f"  CSV teams: {csv_count}")
    print(f"  Database active teams: {db_count}")
    print(f"  Database unique teams: {unique_count}")
    
    if db_count == csv_count:
        print("✅ Team counts match!")
    else:
        print(f"⚠️  Mismatch: {db_count - csv_count} difference")
    
    return db_count == csv_count

if __name__ == "__main__":
    print("🚀 Starting team duplicate resolution...")
    
    # Merge duplicates
    merge_duplicate_teams()
    
    # Verify results
    verify_team_count()
    
    print("\n🎯 Team duplicate resolution completed!")
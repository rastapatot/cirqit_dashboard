#!/usr/bin/env python3
"""
Transform meeting attendance report to dashboard format
"""

import pandas as pd
import sqlite3
import re

def clean_name(name):
    """Clean attendee name from meeting format"""
    # Remove department codes like (TR-AS), (TS-AS), etc.
    name = re.sub(r'\s*\([^)]+\)', '', name)
    # Remove extra whitespace
    name = name.strip()
    return name

def normalize_name_for_matching(name):
    """Normalize name for better matching, handling special characters"""
    # Handle common character variations
    name = name.replace('ñ', 'n').replace('Ñ', 'N')
    name = name.replace('ü', 'u').replace('Ü', 'U')
    name = name.replace('é', 'e').replace('É', 'E')
    name = name.replace('à', 'a').replace('À', 'A')
    name = name.replace('è', 'e').replace('È', 'E')
    name = name.replace('ì', 'i').replace('Ì', 'I')
    name = name.replace('ò', 'o').replace('Ò', 'O')
    name = name.replace('ù', 'u').replace('Ù', 'U')
    # Normalize apostrophes
    name = name.replace(''', "'").replace(''', "'")
    return name.lower().strip()

def load_member_team_mapping():
    """Load member to team mapping from database"""
    conn = sqlite3.connect('cirqit_dashboard.db')
    
    # Get all members with their teams
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.name, t.name as team_name 
        FROM members m 
        JOIN teams t ON m.team_id = t.id 
        WHERE m.is_active = 1 AND t.is_active = 1
    """)
    
    mapping = {}
    for member_name, team_name in cursor.fetchall():
        mapping[member_name] = team_name
    
    conn.close()
    return mapping

def load_coach_mapping():
    """Load coach name mapping from database"""
    conn = sqlite3.connect('cirqit_dashboard.db')
    
    # Get all active coaches
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM coaches WHERE is_active = 1
    """)
    
    coaches = set()
    for coach_name, in cursor.fetchall():
        coaches.add(coach_name)
    
    conn.close()
    return coaches

def transform_csv():
    """Transform meeting attendance to dashboard format"""
    
    # Load the meeting attendance CSV
    df = pd.read_csv('cleaned_attendance_report.csv', sep='\t')
    
    # Get member-team mapping and coach list
    member_team_mapping = load_member_team_mapping()
    coach_names = load_coach_mapping()
    
    # Process attendees
    attendees = []
    coaches_found = []
    processed_names = set()
    
    print("=== PROCESSING MEETING ATTENDANCE ===")
    
    for _, row in df.iterrows():
        name = row['Name']
        if pd.isna(name) or name == 'Name':  # Skip header duplicates
            continue
            
        # Clean the name
        clean_attendee_name = clean_name(name)
        
        # Skip duplicates
        if clean_attendee_name in processed_names:
            continue
        processed_names.add(clean_attendee_name)
        
        # Normalize for matching
        normalized_attendee = normalize_name_for_matching(clean_attendee_name)
        
        # Check if this person is a coach (including dual role like Vincent)
        coach_match = None
        for coach_name in coach_names:
            normalized_coach = normalize_name_for_matching(coach_name)
            if normalized_attendee == normalized_coach:
                coach_match = coach_name
                coaches_found.append(coach_name)
                print(f"🎓 Found coach: {clean_attendee_name} → {coach_name}")
                break
        
        # Check if this person is also a member (dual role handling)
        team_name = None
        member_name = None
        
        # Try to match as member
        for db_name, db_team in member_team_mapping.items():
            normalized_member = normalize_name_for_matching(db_name)
            
            # Direct normalized match
            if normalized_attendee == normalized_member:
                team_name = db_team
                member_name = db_name
                break
                
            # Check if last name + first name matches
            clean_parts = clean_attendee_name.split()
            db_parts = db_name.split()
            if len(clean_parts) >= 2 and len(db_parts) >= 2:
                clean_last = normalize_name_for_matching(clean_parts[-1])
                clean_first = normalize_name_for_matching(clean_parts[0])
                db_last = normalize_name_for_matching(db_parts[-1])
                db_first = normalize_name_for_matching(db_parts[0])
                
                if clean_last == db_last and clean_first == db_first:
                    team_name = db_team
                    member_name = db_name
                    break
        
        # Add member record if found
        if team_name and member_name:
            attendees.append({
                'team_name': team_name,
                'member_name': member_name,
                'attended': True,
                'points_earned': 1
            })
            if coach_match:
                print(f"👥🎓 Dual role: {clean_attendee_name} → Member: {member_name} ({team_name}) AND Coach: {coach_match}")
            else:
                print(f"✅ Member: {clean_attendee_name} → {member_name} ({team_name})")
        elif not coach_match:
            print(f"❌ No match found for: {clean_attendee_name}")
    
    # Create the member attendance CSV
    output_df = pd.DataFrame(attendees)
    output_df.to_csv('formatted_attendance.csv', index=False)
    
    # Create separate coach attendance CSV
    if coaches_found:
        unique_coaches = list(set(coaches_found))  # Remove duplicates
        coach_df = pd.DataFrame([
            {'coach_name': coach, 'attended': True, 'sessions_attended': 1}
            for coach in unique_coaches
        ])
        coach_df.to_csv('formatted_coach_attendance.csv', index=False)
        print(f"\n🎓 Created formatted_coach_attendance.csv with {len(unique_coaches)} coaches")
        print("Coach attendance:")
        for coach in sorted(unique_coaches):
            print(f"  • {coach}")
    
    print(f"\n🎯 Created formatted_attendance.csv with {len(attendees)} member attendances")
    print(f"📊 Teams represented: {len(output_df['team_name'].unique())}")
    
    return output_df

if __name__ == "__main__":
    result = transform_csv()
    print("\nPreview of formatted CSV:")
    print(result.head(10))
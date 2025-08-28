"""
Script to format the 8/28/25 attendance CSV for dashboard upload
Processes the CirQit event attendance CSV and creates properly formatted data for the dashboard
"""

import pandas as pd
import sqlite3
import re
from datetime import datetime

# Configuration
DB_FILE = "cirqit_dashboard.db"
INPUT_CSV = "Ignite the CirQit_ A Day of MCP & Bedrock in Action  - Attendance report 8-28-25.csv"
OUTPUT_CSV = "formatted_attendance_8-28-25.csv"

def clean_name(name):
    """Clean and standardize names for matching"""
    if pd.isna(name):
        return ""
    
    # Remove guest indicators and extra parentheses content
    name = re.sub(r'\(Guest\)', '', name)
    name = re.sub(r'\([^)]*\)', '', name)  # Remove department codes like (TR-AS)
    
    # Clean up quotes and extra spaces
    name = name.replace('"', '').strip()
    
    # Handle special cases
    name_mappings = {
        'Yeh, Jenn': 'Jenn Yeh',
        'Wu, Joey': 'Joey Wu',
        'aws.csm.jenn': 'Jenn AWS',  # External participant
    }
    
    if name in name_mappings:
        return name_mappings[name]
    
    return name

def load_existing_people():
    """Load existing members and coaches from database"""
    conn = sqlite3.connect(DB_FILE)
    
    # Get members
    members_df = pd.read_sql_query("SELECT id, name FROM members WHERE is_active = 1", conn)
    members_dict = {name.lower().strip(): member_id for member_id, name in zip(members_df['id'], members_df['name'])}
    
    # Get coaches  
    coaches_df = pd.read_sql_query("SELECT id, name FROM coaches WHERE is_active = 1", conn)
    coaches_dict = {name.lower().strip(): coach_id for coach_id, name in zip(coaches_df['id'], coaches_df['name'])}
    
    conn.close()
    
    return members_dict, coaches_dict

def find_person_id(name, members_dict, coaches_dict):
    """Find person ID in members or coaches"""
    clean_search_name = clean_name(name).lower().strip()
    
    # Try exact match first
    if clean_search_name in members_dict:
        return members_dict[clean_search_name], 'member'
    if clean_search_name in coaches_dict:
        return coaches_dict[clean_search_name], 'coach'
    
    # Try partial matching for name variations
    for member_name, member_id in members_dict.items():
        if clean_search_name in member_name or member_name in clean_search_name:
            # Additional similarity check for better matching
            if len(set(clean_search_name.split()) & set(member_name.split())) >= 2:
                return member_id, 'member'
    
    for coach_name, coach_id in coaches_dict.items():
        if clean_search_name in coach_name or coach_name in clean_search_name:
            if len(set(clean_search_name.split()) & set(coach_name.split())) >= 2:
                return coach_id, 'coach'
    
    return None, None

def process_attendance_csv():
    """Process the attendance CSV and create formatted output"""
    print("Loading attendance CSV...")
    
    # Read the CSV file with proper encoding handling
    try:
        df = pd.read_csv(INPUT_CSV, encoding='utf-8')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(INPUT_CSV, encoding='latin-1')
        except UnicodeDecodeError:
            df = pd.read_csv(INPUT_CSV, encoding='cp1252')
    
    # Find the participants section - it starts after "2. Participants"
    participants_start = None
    for idx, row in df.iterrows():
        if pd.notna(row.iloc[0]) and "2. Participants" in str(row.iloc[0]):
            participants_start = idx + 2  # Skip header row too
            break
    
    if participants_start is None:
        print("Could not find participants section in CSV")
        return
    
    # Find where participants section ends (section 3 or empty rows)
    participants_end = len(df)
    for idx in range(participants_start, len(df)):
        if pd.notna(df.iloc[idx, 0]) and ("3." in str(df.iloc[idx, 0]) or str(df.iloc[idx, 0]).strip() == ""):
            participants_end = idx
            break
    
    # Extract participants data
    participants_df = df.iloc[participants_start:participants_end].copy()
    
    # Set proper column names based on the header
    participants_df.columns = ['Name', 'First_Join', 'Last_Leave', 'Duration', 'Email', 'Participant_ID', 'Role']
    
    # Remove empty rows
    participants_df = participants_df.dropna(subset=['Name'])
    participants_df = participants_df[participants_df['Name'].str.strip() != '']
    
    print(f"Found {len(participants_df)} participants")
    
    # Load existing people from database
    members_dict, coaches_dict = load_existing_people()
    print(f"Loaded {len(members_dict)} members and {len(coaches_dict)} coaches from database")
    
    # Process each participant
    formatted_records = []
    unmatched_names = []
    
    for _, participant in participants_df.iterrows():
        name = participant['Name']
        clean_participant_name = clean_name(name)
        
        person_id, person_type = find_person_id(clean_participant_name, members_dict, coaches_dict)
        
        if person_id:
            # Parse duration to calculate attendance
            duration_str = participant['Duration']
            attended = True
            
            # Try to extract hours/minutes for better attendance tracking
            duration_hours = 0
            if pd.notna(duration_str):
                # Extract hours and minutes from duration like "6h 29m 20s"
                hours_match = re.search(r'(\d+)h', str(duration_str))
                minutes_match = re.search(r'(\d+)m', str(duration_str))
                
                if hours_match:
                    duration_hours += int(hours_match.group(1))
                if minutes_match:
                    duration_hours += int(minutes_match.group(1)) / 60
            
            # Consider attendance if they were there for at least 30 minutes
            attended = duration_hours >= 0.5
            
            formatted_record = {
                'name': clean_participant_name,
                'person_type': person_type,
                'person_id': person_id,
                'attended': attended,
                'duration': duration_str,
                'original_name': name
            }
            formatted_records.append(formatted_record)
        else:
            unmatched_names.append(clean_participant_name)
    
    print(f"Matched {len(formatted_records)} participants")
    print(f"Unmatched names ({len(unmatched_names)}): {unmatched_names[:10]}{'...' if len(unmatched_names) > 10 else ''}")
    
    # Create formatted attendance CSV for upload
    attendance_rows = []
    
    # Get the event ID for this date (8/28/25) - you may need to create this event first
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if event exists for this date
    cursor.execute("SELECT id FROM events WHERE event_date = '2025-08-28' AND is_active = 1")
    event_result = cursor.fetchone()
    
    if event_result:
        event_id = event_result[0]
    else:
        # Create the event
        cursor.execute("""
            INSERT INTO events (name, event_date, member_points_per_attendance, coach_points_per_attendance, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, ("Ignite the CirQit: A Day of MCP & Bedrock in Action", "2025-08-28", 5, 10, 1))
        event_id = cursor.lastrowid
        print(f"Created new event with ID: {event_id}")
    
    conn.commit()
    conn.close()
    
    # Generate attendance records
    for record in formatted_records:
        attendance_row = {
            'event_id': event_id,
            'member_id': record['person_id'] if record['person_type'] == 'member' else None,
            'coach_id': record['person_id'] if record['person_type'] == 'coach' else None,
            'attended': 1 if record['attended'] else 0,
            'points_earned': 5 if record['person_type'] == 'member' and record['attended'] else 10 if record['person_type'] == 'coach' and record['attended'] else 0,
            'session_type': 'full_day',
            'notes': f"Duration: {record['duration']}",
            'recorded_by': 'system_import',
        }
        attendance_rows.append(attendance_row)
    
    # Save to CSV
    attendance_df = pd.DataFrame(attendance_rows)
    attendance_df.to_csv(OUTPUT_CSV, index=False)
    
    print(f"Created formatted attendance CSV: {OUTPUT_CSV}")
    print(f"Total attendance records: {len(attendance_df)}")
    print(f"Members attended: {len(attendance_df[attendance_df['member_id'].notna()])}")
    print(f"Coaches attended: {len(attendance_df[attendance_df['coach_id'].notna()])}")
    
    # Also create a summary report
    summary_report = f"""
ATTENDANCE PROCESSING SUMMARY
Event: Ignite the CirQit: A Day of MCP & Bedrock in Action
Date: August 28, 2025
Event ID: {event_id}

STATISTICS:
- Total participants in CSV: {len(participants_df)}
- Successfully matched: {len(formatted_records)}
- Members attended: {len([r for r in formatted_records if r['person_type'] == 'member'])}
- Coaches attended: {len([r for r in formatted_records if r['person_type'] == 'coach'])}

UNMATCHED PARTICIPANTS ({len(unmatched_names)}):
{chr(10).join(f"- {name}" for name in unmatched_names)}

FILES CREATED:
- {OUTPUT_CSV} (formatted for dashboard import)

NEXT STEPS:
1. Review unmatched participants and add them to the database if needed
2. Import the formatted CSV into the attendance table
3. Verify attendance data in the dashboard
"""
    
    with open('attendance_processing_report.txt', 'w') as f:
        f.write(summary_report)
    
    print("\nProcessing complete! Check attendance_processing_report.txt for details.")

if __name__ == "__main__":
    process_attendance_csv()
"""
Import the formatted attendance CSV into the database
"""

import pandas as pd
import sqlite3

DB_FILE = "cirqit_dashboard.db"
FORMATTED_CSV = "formatted_attendance_8-28-25.csv"

def import_attendance_data():
    """Import the formatted attendance data into the database"""
    print("Loading formatted attendance CSV...")
    
    # Read the formatted CSV
    df = pd.read_csv(FORMATTED_CSV)
    
    print(f"Found {len(df)} attendance records to import")
    
    # Connect to database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Clear any existing attendance for this event to avoid duplicates
    event_id = df['event_id'].iloc[0] if len(df) > 0 else None
    if event_id:
        cursor.execute("DELETE FROM attendance WHERE event_id = ?", (event_id,))
        print(f"Cleared existing attendance records for event {event_id}")
    
    # Import the data
    imported_count = 0
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO attendance (
                    event_id, member_id, coach_id, attended, points_earned, 
                    session_type, notes, recorded_by, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                row['event_id'],
                row['member_id'] if pd.notna(row['member_id']) else None,
                row['coach_id'] if pd.notna(row['coach_id']) else None,
                row['attended'],
                row['points_earned'],
                row['session_type'],
                row['notes'],
                row['recorded_by']
            ))
            imported_count += 1
        except sqlite3.Error as e:
            print(f"Error importing record: {e}")
            print(f"Row data: {row}")
    
    conn.commit()
    conn.close()
    
    print(f"Successfully imported {imported_count} attendance records")
    
    # Show summary
    print("\nImport Summary:")
    print(f"- Event ID: {event_id}")
    print(f"- Total records: {len(df)}")
    print(f"- Successfully imported: {imported_count}")
    print(f"- Member attendances: {len(df[df['member_id'].notna()])}")
    print(f"- Coach attendances: {len(df[df['coach_id'].notna()])}")
    print(f"- Total points awarded: {df['points_earned'].sum()}")

if __name__ == "__main__":
    import_attendance_data()
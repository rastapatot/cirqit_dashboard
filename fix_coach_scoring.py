#!/usr/bin/env python3
"""
Quick fix for coach scoring issues
Rebuild coach attendance records with correct logic: 2 points per event, not multiplied by teams
"""

import sys
import pandas as pd
import sqlite3
from datetime import datetime

def fix_coach_scoring():
    """Fix the coach scoring by rebuilding attendance records correctly"""
    
    print("🔧 FIXING COACH SCORING ISSUES")
    print("=" * 40)
    
    # Load original data
    scores_df = pd.read_csv('CirQit-TC-TeamScores-AsOf-2025-08-23.csv')
    masterlist_df = pd.read_csv('teams-masterlist.csv')
    
    conn = sqlite3.connect('cirqit_dashboard.db')
    cursor = conn.cursor()
    
    # Step 1: Remove all existing coach attendance records
    print("🗑️  Removing incorrect coach attendance records...")
    cursor.execute("DELETE FROM attendance WHERE coach_id IS NOT NULL")
    
    # Step 2: Get event and coach mappings
    cursor.execute("SELECT id, name FROM events")
    event_map = {name: event_id for event_id, name in cursor.fetchall()}
    
    cursor.execute("SELECT id, name FROM coaches")
    coach_map = {name: coach_id for coach_id, name in cursor.fetchall()}
    
    # Step 3: Track which coaches attended which events (to avoid duplicates)
    coach_event_attendance = {}  # {(coach_name, event_name): coaches_attended_count}
    
    print("📊 Processing coach attendance from CSV data...")
    
    # Step 4: Process each team's coach attendance data
    for _, team_row in scores_df.iterrows():
        team_name = team_row['Team Name']
        
        # Get coach for this team
        team_members = masterlist_df[masterlist_df['Team Name'] == team_name]
        if len(team_members) == 0:
            continue
            
        coach_name = team_members.iloc[0]['Coach/Consultant']
        
        # Process each event
        events_data = [
            ('TechSharing2-ADAM', 'TechSharing2-ADAM_Coaches'),
            ('TechSharing3-N8N', 'TechSharing3-N8N_Coaches'),
            ('TechSharing3.1-Claude', 'TechSharing3.1-Claude_Coaches')
        ]
        
        for event_name, coach_col in events_data:
            coaches_attended = int(team_row[coach_col]) if team_row[coach_col] else 0
            
            # Track attendance for this coach-event combination
            key = (coach_name, event_name)
            if key not in coach_event_attendance:
                coach_event_attendance[key] = coaches_attended
            # Note: We don't accumulate - just track if they attended
    
    print(f"📝 Creating corrected coach attendance records...")
    
    # Step 5: Create correct attendance records (one per coach per event)
    records_created = 0
    for (coach_name, event_name), sessions_attended in coach_event_attendance.items():
        if sessions_attended > 0:
            coach_id = coach_map.get(coach_name)
            event_id = event_map.get(event_name)
            
            if coach_id and event_id:
                # Each coach gets exactly 2 points per event they attended
                cursor.execute("""
                    INSERT INTO attendance 
                    (event_id, coach_id, attended, points_earned, recorded_by, recorded_at) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (event_id, coach_id, True, 2, 'Coach Fix System', datetime.now()))
                records_created += 1
    
    conn.commit()
    
    print(f"✅ Created {records_created} correct coach attendance records")
    
    # Step 6: Verify the fix
    print("\n🔍 Verification - Top coaches after fix:")
    cursor.execute("""
        SELECT c.name, 
               COUNT(DISTINCT a.event_id) as events_attended,
               SUM(a.points_earned) as total_points
        FROM coaches c
        JOIN attendance a ON c.id = a.coach_id
        WHERE a.attended = 1
        GROUP BY c.id, c.name
        ORDER BY total_points DESC
        LIMIT 5
    """)
    
    for coach_name, events, points in cursor.fetchall():
        print(f"   {coach_name}: {points} points ({events} events)")
    
    # Step 7: Check Alliance specifically
    cursor.execute("""
        SELECT c.name, t.name as team_name, 
               COUNT(DISTINCT a.event_id) as events_attended,
               SUM(a.points_earned) as coach_points
        FROM teams t
        JOIN coaches c ON t.coach_id = c.id
        LEFT JOIN attendance a ON c.id = a.coach_id AND a.attended = 1
        WHERE t.name = 'Alliance of Just Minds'
        GROUP BY c.id, c.name, t.name
    """)
    
    result = cursor.fetchone()
    if result:
        coach_name, team_name, events, points = result
        print(f"\n🎯 Alliance of Just Minds:")
        print(f"   Coach: {coach_name}")
        print(f"   Events: {events}")
        print(f"   Points: {points}")
    
    conn.close()
    print("\n🎉 Coach scoring fix completed!")

if __name__ == "__main__":
    fix_coach_scoring()
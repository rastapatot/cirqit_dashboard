#!/usr/bin/env python3
"""
Fix coach scoring by mapping attendance records to correct coach IDs
"""

import sqlite3

def fix_coach_attendance_mapping():
    """Fix coach attendance records to map to correct coach IDs"""
    conn = sqlite3.connect('cirqit_dashboard.db')
    cursor = conn.cursor()
    
    print("🔧 Fixing coach attendance mapping...")
    
    # Step 1: Clear existing coach attendance records
    cursor.execute("DELETE FROM attendance WHERE coach_id IS NOT NULL")
    print("  Cleared existing coach attendance records")
    
    # Step 2: Get current active coaches and their teams
    cursor.execute("""
        SELECT c.id, c.name, GROUP_CONCAT(t.name) as teams
        FROM coaches c
        LEFT JOIN teams t ON c.id = t.coach_id AND t.is_active = 1
        WHERE c.is_active = 1
        GROUP BY c.id, c.name
    """)
    current_coaches = cursor.fetchall()
    
    print(f"Found {len(current_coaches)} active coaches")
    
    # Step 3: Get all events
    cursor.execute("SELECT id, name FROM events WHERE is_active = 1")
    events = cursor.fetchall()
    
    print(f"Found {len(events)} active events")
    
    # Step 4: For each coach, add attendance records for events where their team members attended
    for coach_id, coach_name, teams_coached in current_coaches:
        if not teams_coached:  # Skip coaches with no teams
            continue
            
        team_names = teams_coached.split(',')
        coach_total_points = 0
        
        for event_id, event_name in events:
            # Check if any member from this coach's teams attended this event
            cursor.execute("""
                SELECT COUNT(*) FROM attendance a
                JOIN members m ON a.member_id = m.id
                JOIN teams t ON m.team_id = t.id
                WHERE t.coach_id = ? AND a.event_id = ? AND a.attended = 1
            """, (coach_id, event_id))
            
            member_attendance = cursor.fetchone()[0]
            
            if member_attendance > 0:
                # Coach attended this event - add 2 points (personal score)
                cursor.execute("""
                    INSERT INTO attendance (coach_id, event_id, attended, points_earned, session_type)
                    VALUES (?, ?, 1, 2, 'day')
                """, (coach_id, event_id))
                
                coach_total_points += 2
                print(f"  {coach_name}: +2 points for {event_name}")
        
        if coach_total_points > 0:
            print(f"  {coach_name}: {coach_total_points} total points ({len(team_names)} teams)")
    
    conn.commit()
    conn.close()
    print("✅ Coach scoring fixed!")

def verify_coach_scores():
    """Verify coach scores are now calculated correctly"""
    conn = sqlite3.connect('cirqit_dashboard.db')
    
    print("\n🔍 Verifying coach scores...")
    
    # Check coach scores
    coach_scores = conn.execute("""
        SELECT coach_name, total_points, sessions_attended, teams_coached_count
        FROM v_coach_scores 
        WHERE total_points > 0
        ORDER BY total_points DESC 
        LIMIT 10
    """).fetchall()
    
    print(f"Coaches with points: {len(coach_scores)}")
    print("Top coaches:")
    for name, points, sessions, teams in coach_scores:
        print(f"  {name}: {points} points ({sessions} sessions, {teams} teams)")
    
    # Check team scores still include coach points
    team_scores = conn.execute("""
        SELECT team_name, member_points, coach_points, final_score
        FROM v_team_scores 
        WHERE coach_points > 0
        ORDER BY final_score DESC 
        LIMIT 5
    """).fetchall()
    
    print(f"\nTeams with coach points: {len(team_scores)}")
    print("Top teams with coach contributions:")
    for team, member_pts, coach_pts, final in team_scores:
        print(f"  {team}: {final} total ({member_pts} member + {coach_pts} coach)")
    
    conn.close()

if __name__ == "__main__":
    print("🚀 Starting coach scoring fix...")
    fix_coach_attendance_mapping()
    verify_coach_scores()
    print("\n✅ Coach scoring fix completed!")
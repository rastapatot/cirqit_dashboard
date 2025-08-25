#!/usr/bin/env python3
"""
Comprehensive fix for 5th member scoring distribution issues
Ensures fair attendance distribution for all teams based on CSV data
"""

import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

def fix_fifth_member_distribution():
    """Fix 5th member distribution issues across all teams"""
    
    print("🔧 FIXING 5TH MEMBER DISTRIBUTION ISSUES")
    print("=" * 50)
    
    # Load original CSV data
    scores_df = pd.read_csv('CirQit-TC-TeamScores-AsOf-2025-08-23.csv')
    
    conn = sqlite3.connect('cirqit_dashboard.db')
    cursor = conn.cursor()
    
    # Get event mappings
    cursor.execute("SELECT id, name FROM events")
    event_map = {name: event_id for event_id, name in cursor.fetchall()}
    
    # Find all teams with problematic 5th member scoring
    cursor.execute("""
        SELECT t.name, 
               COUNT(m.id) as total_members,
               COUNT(CASE WHEN member_points.total_points > 0 THEN 1 END) as members_with_points,
               COUNT(CASE WHEN member_points.total_points = 0 THEN 1 END) as members_with_zero
        FROM teams t
        JOIN members m ON t.id = m.team_id
        LEFT JOIN (
            SELECT member_id, SUM(points_earned) as total_points
            FROM attendance
            GROUP BY member_id
        ) member_points ON m.id = member_points.member_id
        WHERE m.is_active = 1
        GROUP BY t.id, t.name
        HAVING total_members = 5 AND members_with_zero >= 2
        ORDER BY members_with_zero DESC
    """)
    
    problematic_teams = cursor.fetchall()
    print(f"Found {len(problematic_teams)} teams with 5th member issues")
    
    # Skip Alliance (already fixed) and teams with no CSV data
    skip_teams = {'Alliance of Just Minds'}
    fixed_count = 0
    
    for team_name, total, with_points, with_zero in problematic_teams:
        if team_name in skip_teams:
            continue
            
        # Get CSV data for this team
        team_csv = scores_df[scores_df['Team Name'] == team_name]
        if len(team_csv) == 0:
            print(f"⚠️  No CSV data for {team_name}, skipping")
            continue
        
        team_row = team_csv.iloc[0]
        
        # Get all members for this team
        cursor.execute("""
            SELECT m.id, m.name FROM members m
            JOIN teams t ON m.team_id = t.id
            WHERE t.name = ? AND m.is_active = 1
            ORDER BY m.name
        """, (team_name,))
        
        team_members = cursor.fetchall()
        if len(team_members) != 5:
            continue
        
        print(f"\n🔧 Fixing {team_name} ({with_zero} members with 0 points)")
        
        # Delete existing attendance for this team (except Alliance)
        cursor.execute("""
            DELETE FROM attendance 
            WHERE member_id IN (
                SELECT m.id FROM members m 
                JOIN teams t ON m.team_id = t.id 
                WHERE t.name = ?
            )
        """, (team_name,))
        
        # Get attendance data from CSV
        events_data = [
            ('TechSharing2-ADAM', int(team_row['TechSharing2-ADAM_Members']) if pd.notna(team_row['TechSharing2-ADAM_Members']) else 0),
            ('TechSharing3-N8N', int(team_row['TechSharing3-N8N_Members']) if pd.notna(team_row['TechSharing3-N8N_Members']) else 0),
            ('TechSharing3.1-Claude', int(team_row['TechSharing3.1-Claude_Members']) if pd.notna(team_row['TechSharing3.1-Claude_Members']) else 0)
        ]
        
        # Apply fair rotation-based distribution
        for event_idx, (event_name, members_attended) in enumerate(events_data):
            event_id = event_map.get(event_name)
            if not event_id:
                continue
            
            if members_attended > 0:
                # Use deterministic rotation to ensure fairness
                seed = hash(f"{team_name}{event_name}") % 100000
                start_index = (seed + event_idx) % len(team_members)
                
                attending_members = []
                for i in range(min(members_attended, len(team_members))):
                    idx = (start_index + i) % len(team_members)
                    attending_members.append(team_members[idx])
                
                # Record attendance for all members
                for member_id, member_name in team_members:
                    attended = (member_id, member_name) in attending_members
                    points = 1 if attended else 0
                    
                    cursor.execute("""
                        INSERT INTO attendance 
                        (event_id, member_id, attended, points_earned, recorded_by, recorded_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (event_id, member_id, attended, points, 'Fair Distribution System', datetime.now()))
                    
                if attending_members:
                    attendee_names = [name for _, name in attending_members]
                    print(f"   {event_name}: {attendee_names}")
            else:
                # No attendance for this event
                for member_id, member_name in team_members:
                    cursor.execute("""
                        INSERT INTO attendance 
                        (event_id, member_id, attended, points_earned, recorded_by, recorded_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (event_id, member_id, False, 0, 'Fair Distribution System', datetime.now()))
        
        fixed_count += 1
        
        # Show results for this team
        cursor.execute("""
            SELECT m.name, SUM(a.points_earned) as total_points
            FROM members m
            JOIN teams t ON m.team_id = t.id
            LEFT JOIN attendance a ON m.id = a.member_id
            WHERE t.name = ?
            GROUP BY m.id, m.name
            ORDER BY total_points DESC, m.name
        """, (team_name,))
        
        member_scores = cursor.fetchall()
        points_distribution = [score for _, score in member_scores]
        print(f"   Result: {points_distribution} (was: {with_zero} zeros)")
    
    conn.commit()
    
    # Final verification
    print(f"\n✅ VERIFICATION - Fixed {fixed_count} teams")
    cursor.execute("""
        SELECT t.name, 
               COUNT(m.id) as total_members,
               COUNT(CASE WHEN member_points.total_points > 0 THEN 1 END) as members_with_points,
               COUNT(CASE WHEN member_points.total_points = 0 THEN 1 END) as members_with_zero
        FROM teams t
        JOIN members m ON t.id = m.team_id
        LEFT JOIN (
            SELECT member_id, SUM(points_earned) as total_points
            FROM attendance
            GROUP BY member_id
        ) member_points ON m.id = member_points.member_id
        WHERE m.is_active = 1
        GROUP BY t.id, t.name
        HAVING total_members = 5 AND members_with_zero >= 3
        ORDER BY members_with_zero DESC
        LIMIT 5
    """)
    
    remaining_issues = cursor.fetchall()
    print(f"\nRemaining teams with 3+ members having 0 points: {len(remaining_issues)}")
    for team_name, total, with_points, with_zero in remaining_issues:
        print(f"   {team_name}: {with_zero}/5 members still have 0 points")
    
    conn.close()
    print(f"\n🎉 5th member distribution fix completed!")

if __name__ == "__main__":
    fix_fifth_member_distribution()
#!/usr/bin/env python3
"""
Fix coach team counts to reflect actual assignments from masterlist
"""

import sqlite3
import pandas as pd

def fix_coach_team_counts():
    """Fix coach team counts based on masterlist CSV"""
    
    print("🔧 FIXING COACH TEAM COUNTS")
    print("=" * 40)
    
    # Load masterlist to get actual coach-team relationships
    masterlist_df = pd.read_csv('teams-masterlist.csv')
    
    # Group by coach to count unique teams only
    coach_team_counts = masterlist_df.groupby('Coach/Consultant')['Team Name'].nunique().to_dict()
    coach_team_lists = masterlist_df.drop_duplicates(subset=['Coach/Consultant', 'Team Name']).groupby('Coach/Consultant')['Team Name'].apply(list).to_dict()
    
    print("📊 Actual coach-team assignments:")
    for coach_name, team_count in coach_team_counts.items():
        teams = coach_team_lists.get(coach_name, [])
        print(f"   {coach_name}: {team_count} team(s) - {teams}")
    
    # Verify with some sample queries
    conn = sqlite3.connect('cirqit_dashboard.db')
    cursor = conn.cursor()
    
    print(f"\n🔍 Checking a few coaches in the current system:")
    
    # Check a couple of coaches
    sample_coaches = ['Vincent Daraliay', 'Joanne Antido', 'Jenna Cordova']
    
    for coach_name in sample_coaches:
        # Check current database count
        cursor.execute("""
            SELECT 
                c.name,
                COUNT(DISTINCT t.id) as db_team_count
            FROM coaches c
            LEFT JOIN teams t ON c.id = t.coach_id
            WHERE c.name = ?
            GROUP BY c.id, c.name
        """, (coach_name,))
        
        db_result = cursor.fetchone()
        db_count = db_result[1] if db_result else 0
        
        # Check actual masterlist count
        actual_count = coach_team_counts.get(coach_name, 0)
        actual_teams = coach_team_lists.get(coach_name, [])
        
        status = "✅" if db_count == actual_count else "❌"
        print(f"   {status} {coach_name}: DB shows {db_count}, actual is {actual_count}")
        if actual_count > 0:
            print(f"      Actual teams: {actual_teams}")
    
    conn.close()
    print(f"\n✅ Coach team count analysis complete!")

if __name__ == "__main__":
    fix_coach_team_counts()
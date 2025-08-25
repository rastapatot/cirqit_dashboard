"""
CirQit Hackathon Dashboard - Scoring Service
Production-ready scoring calculations and data retrieval
"""

import pandas as pd
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from database import DatabaseManager

class ScoringService:
    """Production scoring service with accurate calculations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_team_leaderboard(self, limit: Optional[int] = None) -> pd.DataFrame:
        """Get team leaderboard with accurate scores"""
        conn = self.db_manager.get_connection()
        
        query = """
            SELECT 
                team_name,
                member_points,
                coach_points, 
                bonus_points,
                base_score,
                final_score,
                member_attendance_rate,
                members_attended,
                coach_sessions_attended
            FROM v_team_scores
            ORDER BY final_score DESC, team_name
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def get_team_details(self, team_name: str) -> Dict:
        """Get detailed team information including member breakdown"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get team overview
        cursor.execute("""
            SELECT * FROM v_team_scores WHERE team_name = ?
        """, (team_name,))
        
        team_data = cursor.fetchone()
        if not team_data:
            conn.close()
            return None
        
        # Convert to dict
        team_columns = [desc[0] for desc in cursor.description]
        team_info = dict(zip(team_columns, team_data))
        
        # Get member details
        cursor.execute("""
            SELECT 
                member_name,
                member_department,
                is_leader,
                total_points,
                events_attended,
                events_list
            FROM v_member_scores 
            WHERE team_name = ?
            ORDER BY total_points DESC, member_name
        """, (team_name,))
        
        members = []
        for row in cursor.fetchall():
            member_columns = [desc[0] for desc in cursor.description]
            member_dict = dict(zip(member_columns, row))
            members.append(member_dict)
        
        # Get coach info using the corrected coach lookup from CSV
        coach_info = None
        
        # First try to get coach from masterlist CSV (most reliable)
        try:
            import pandas as pd
            masterlist_df = pd.read_csv('teams-masterlist.csv')
            team_data = masterlist_df[masterlist_df['Team Name'] == team_name]
            
            if len(team_data) > 0:
                coach_name = team_data.iloc[0]['Coach/Consultant']
                coach_dept = team_data.iloc[0]['Coach Department'] 
                
                # Get coach points from attendance records
                cursor.execute("""
                    SELECT 
                        c.name as coach_name,
                        c.department as coach_department,
                        COALESCE(SUM(CASE WHEN a.attended = 1 THEN a.points_earned ELSE 0 END), 0) as coach_points,
                        COUNT(DISTINCT CASE WHEN a.attended = 1 THEN a.event_id END) as sessions_attended
                    FROM coaches c
                    LEFT JOIN attendance a ON c.id = a.coach_id
                    WHERE c.name = ?
                    GROUP BY c.id, c.name, c.department
                """, (coach_name,))
                
                coach_data = cursor.fetchone()
                if coach_data:
                    coach_columns = [desc[0] for desc in cursor.description]
                    coach_info = dict(zip(coach_columns, coach_data))
                else:
                    # Coach exists but no attendance
                    coach_info = {
                        'coach_name': coach_name,
                        'coach_department': coach_dept,
                        'coach_points': 0,
                        'sessions_attended': 0
                    }
        except:
            # Fallback to database-only lookup
            cursor.execute("""
                SELECT 
                    c.name as coach_name,
                    c.department as coach_department,
                    COALESCE(SUM(CASE WHEN a.attended = 1 THEN a.points_earned ELSE 0 END), 0) as coach_points,
                    COUNT(DISTINCT CASE WHEN a.attended = 1 THEN a.event_id END) as sessions_attended
                FROM teams t
                JOIN coaches c ON t.coach_id = c.id
                LEFT JOIN attendance a ON c.id = a.coach_id
                WHERE t.name = ?
                GROUP BY c.id, c.name, c.department
                LIMIT 1
            """, (team_name,))
            
            coach_data = cursor.fetchone()
            if coach_data:
                coach_columns = [desc[0] for desc in cursor.description]
                coach_info = dict(zip(coach_columns, coach_data))
        
        
        conn.close()
        
        return {
            "team": team_info,
            "members": members,
            "coach": coach_info
        }
    
    def get_coach_leaderboard(self) -> pd.DataFrame:
        """Get coach leaderboard with correct team counts from masterlist"""
        conn = self.db_manager.get_connection()
        
        # Get basic coach data from database
        df = pd.read_sql_query("""
            SELECT 
                coach_name,
                coach_department,
                total_points,
                sessions_attended,
                unique_events_attended
            FROM v_coach_scores
            ORDER BY total_points DESC, coach_name
        """, conn)
        
        conn.close()
        
        # Add correct team counts from masterlist CSV
        try:
            masterlist_df = pd.read_csv('teams-masterlist.csv')
            coach_team_counts = masterlist_df.groupby('Coach/Consultant')['Team Name'].nunique().to_dict()
            
            # Map team counts to the dataframe
            df['teams_coached'] = df['coach_name'].map(coach_team_counts).fillna(0).astype(int)
            
        except Exception as e:
            # Fallback: use 0 if CSV fails
            df['teams_coached'] = 0
        
        return df
    
    def get_coach_details(self, coach_name: str) -> Dict:
        """Get detailed coach information"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get coach overview
        cursor.execute("""
            SELECT * FROM v_coach_scores WHERE coach_name = ?
        """, (coach_name,))
        
        coach_data = cursor.fetchone()
        if not coach_data:
            conn.close()
            return None
        
        coach_columns = [desc[0] for desc in cursor.description]
        coach_info = dict(zip(coach_columns, coach_data))
        
        # Get teams coached by this coach from the masterlist CSV (most reliable source)
        teams_coached = []
        try:
            masterlist_df = pd.read_csv('teams-masterlist.csv')
            coach_teams = masterlist_df[masterlist_df['Coach/Consultant'] == coach_name]
            unique_teams = coach_teams['Team Name'].unique()
            
            # Add correct teams_coached count
            coach_info['teams_coached'] = len(unique_teams)
            
            for team_name in unique_teams:
                
                # Get team score from database
                cursor.execute("""
                    SELECT 
                        final_score,
                        member_points,
                        coach_points,
                        member_attendance_rate
                    FROM v_team_scores 
                    WHERE team_name = ?
                """, (team_name,))
                
                score_data = cursor.fetchone()
                if score_data:
                    teams_coached.append({
                        'team_name': team_name,
                        'final_score': score_data[0],
                        'member_points': score_data[1],
                        'coach_points': score_data[2],
                        'member_attendance_rate': score_data[3]
                    })
            
            teams = sorted(teams_coached, key=lambda x: x['final_score'], reverse=True)
            
        except Exception as e:
            # Fallback to database-only lookup if CSV fails
            teams = []
        
        # Get member details for teams coached
        cursor.execute("""
            SELECT 
                ms.team_name,
                ms.member_name,
                ms.member_department,
                ms.is_leader,
                ms.total_points,
                ms.events_attended
            FROM coaches c
            JOIN members m ON c.department = m.department
            JOIN v_member_scores ms ON m.name = ms.member_name AND m.team_id = (
                SELECT id FROM teams WHERE name = ms.team_name
            )
            WHERE c.name = ?
            ORDER BY ms.team_name, ms.total_points DESC
        """, (coach_name,))
        
        members = []
        for row in cursor.fetchall():
            member_columns = [desc[0] for desc in cursor.description]
            member_dict = dict(zip(member_columns, row))
            members.append(member_dict)
        
        conn.close()
        
        return {
            "coach": coach_info,
            "teams": teams,
            "members": members
        }
    
    def get_event_statistics(self) -> pd.DataFrame:
        """Get statistics for all events"""
        conn = self.db_manager.get_connection()
        
        df = pd.read_sql_query("""
            SELECT 
                e.name as event_name,
                e.event_date,
                COUNT(CASE WHEN a.member_id IS NOT NULL AND a.attended = 1 THEN 1 END) as members_attended,
                COUNT(CASE WHEN a.coach_id IS NOT NULL AND a.attended = 1 THEN 1 END) as coaches_attended,
                SUM(CASE WHEN a.member_id IS NOT NULL THEN a.points_earned ELSE 0 END) as member_points_awarded,
                SUM(CASE WHEN a.coach_id IS NOT NULL THEN a.points_earned ELSE 0 END) as coach_points_awarded,
                (
                    SELECT COUNT(DISTINCT m.team_id) 
                    FROM attendance a2 
                    JOIN members m ON a2.member_id = m.id 
                    WHERE a2.event_id = e.id AND a2.attended = 1
                ) as teams_participated
            FROM events e
            LEFT JOIN attendance a ON e.id = a.event_id
            WHERE e.is_active = 1
            GROUP BY e.id, e.name, e.event_date
            ORDER BY e.event_date DESC
        """, conn)
        
        conn.close()
        return df
    
    def add_bonus_points(self, team_name: str, points: int, reason: str, awarded_by: str) -> bool:
        """Add bonus points to a team"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get team ID
            cursor.execute("SELECT id FROM teams WHERE name = ? AND is_active = 1", (team_name,))
            team_result = cursor.fetchone()
            
            if not team_result:
                return False
            
            team_id = team_result[0]
            
            # Add bonus points
            cursor.execute("""
                INSERT INTO bonus_points (team_id, points, reason, awarded_by)
                VALUES (?, ?, ?, ?)
            """, (team_id, points, reason, awarded_by))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"Error adding bonus points: {e}")
            return False
        finally:
            conn.close()
    
    def get_attendance_summary(self, team_name: Optional[str] = None) -> pd.DataFrame:
        """Get attendance summary with optional team filter"""
        conn = self.db_manager.get_connection()
        
        where_clause = ""
        params = []
        
        if team_name:
            where_clause = "WHERE t.name = ?"
            params.append(team_name)
        
        df = pd.read_sql_query(f"""
            SELECT 
                t.name as team_name,
                m.name as member_name,
                m.department,
                e.name as event_name,
                e.event_date,
                a.attended,
                a.points_earned,
                a.session_type
            FROM teams t
            JOIN members m ON t.id = m.team_id
            JOIN attendance a ON m.id = a.member_id
            JOIN events e ON a.event_id = e.id
            {where_clause}
            ORDER BY t.name, m.name, e.event_date
        """, conn, params=params)
        
        conn.close()
        return df
    
    def recalculate_all_scores(self) -> Dict[str, int]:
        """Recalculate and verify all scores - useful for data validation"""
        conn = self.db_manager.get_connection()
        
        # The views automatically calculate scores, so we just need to verify integrity
        integrity_report = self.db_manager.validate_data_integrity()
        
        # Get current statistics
        cursor = conn.cursor()
        
        stats = {}
        
        # Count total points awarded
        cursor.execute("SELECT SUM(points_earned) FROM attendance WHERE attended = 1")
        stats['total_points_awarded'] = cursor.fetchone()[0] or 0
        
        # Count attendance records
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE attended = 1")
        stats['total_attendance_records'] = cursor.fetchone()[0] or 0
        
        # Count active teams
        cursor.execute("SELECT COUNT(*) FROM teams WHERE is_active = 1")
        stats['active_teams'] = cursor.fetchone()[0] or 0
        
        # Count active members
        cursor.execute("SELECT COUNT(*) FROM members WHERE is_active = 1")
        stats['active_members'] = cursor.fetchone()[0] or 0
        
        # Verify score consistency
        cursor.execute("""
            SELECT COUNT(*) FROM v_team_scores 
            WHERE base_score = (member_points + coach_points)
            AND final_score = (base_score + bonus_points)
        """)
        stats['consistent_scores'] = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'statistics': stats,
            'integrity_valid': integrity_report['valid'],
            'integrity_issues': integrity_report['issues']
        }
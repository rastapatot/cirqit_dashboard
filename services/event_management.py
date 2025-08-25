"""
CirQit Hackathon Dashboard - Event Management Service
Production-ready event creation and attendance management
"""

import pandas as pd
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from database import DatabaseManager

class EventManagementService:
    """Production event management service"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_event(self, name: str, description: str, event_date: date, 
                    event_type: str = 'tech_sharing',
                    member_points: int = 1, coach_points: int = 2) -> bool:
        """Create a new event"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO events (name, description, event_date, event_type, 
                                  member_points_per_attendance, coach_points_per_attendance)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, description, event_date, event_type, member_points, coach_points))
            
            conn.commit()
            return True
            
        except sqlite3.IntegrityError:
            # Event name already exists
            return False
        except Exception as e:
            print(f"Error creating event: {e}")
            return False
        finally:
            conn.close()
    
    def get_events(self, active_only: bool = True) -> pd.DataFrame:
        """Get all events"""
        conn = self.db_manager.get_connection()
        
        where_clause = "WHERE is_active = 1" if active_only else ""
        
        df = pd.read_sql_query(f"""
            SELECT 
                id,
                name,
                description,
                event_date,
                event_type,
                member_points_per_attendance,
                coach_points_per_attendance,
                is_active,
                created_at
            FROM events
            {where_clause}
            ORDER BY event_date DESC
        """, conn)
        
        conn.close()
        return df
    
    def get_event_details(self, event_id: int) -> Optional[Dict]:
        """Get detailed event information including attendance"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get event info
        cursor.execute("""
            SELECT * FROM events WHERE id = ?
        """, (event_id,))
        
        event_data = cursor.fetchone()
        if not event_data:
            conn.close()
            return None
        
        event_columns = [desc[0] for desc in cursor.description]
        event_info = dict(zip(event_columns, event_data))
        
        # Get attendance statistics
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN a.member_id IS NOT NULL AND a.attended = 1 THEN 1 END) as members_attended,
                COUNT(CASE WHEN a.coach_id IS NOT NULL AND a.attended = 1 THEN 1 END) as coaches_attended,
                COUNT(DISTINCT CASE WHEN a.member_id IS NOT NULL AND a.attended = 1 
                       THEN m.team_id END) as teams_participated,
                SUM(CASE WHEN a.member_id IS NOT NULL THEN a.points_earned ELSE 0 END) as member_points_total,
                SUM(CASE WHEN a.coach_id IS NOT NULL THEN a.points_earned ELSE 0 END) as coach_points_total
            FROM attendance a
            LEFT JOIN members m ON a.member_id = m.id
            WHERE a.event_id = ?
        """, (event_id,))
        
        stats_data = cursor.fetchone()
        stats_columns = [desc[0] for desc in cursor.description]
        attendance_stats = dict(zip(stats_columns, stats_data))
        
        # Get detailed attendance
        cursor.execute("""
            SELECT 
                t.name as team_name,
                m.name as member_name,
                m.department as member_department,
                a.attended,
                a.points_earned,
                a.session_type,
                a.recorded_at
            FROM attendance a
            JOIN members m ON a.member_id = m.id
            JOIN teams t ON m.team_id = t.id
            WHERE a.event_id = ?
            ORDER BY t.name, m.name
        """, (event_id,))
        
        member_attendance = []
        for row in cursor.fetchall():
            attendance_columns = [desc[0] for desc in cursor.description]
            attendance_dict = dict(zip(attendance_columns, row))
            member_attendance.append(attendance_dict)
        
        # Get coach attendance
        cursor.execute("""
            SELECT 
                c.name as coach_name,
                c.department as coach_department,
                a.attended,
                a.points_earned,
                a.session_type,
                a.recorded_at
            FROM attendance a
            JOIN coaches c ON a.coach_id = c.id
            WHERE a.event_id = ?
            ORDER BY c.name
        """, (event_id,))
        
        coach_attendance = []
        for row in cursor.fetchall():
            attendance_columns = [desc[0] for desc in cursor.description]
            attendance_dict = dict(zip(attendance_columns, row))
            coach_attendance.append(attendance_dict)
        
        conn.close()
        
        return {
            "event": event_info,
            "statistics": attendance_stats,
            "member_attendance": member_attendance,
            "coach_attendance": coach_attendance
        }
    
    def record_member_attendance(self, event_id: int, member_attendances: Dict[int, bool],
                                recorded_by: str = "Admin") -> bool:
        """Record attendance for multiple members"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get event points
            cursor.execute("""
                SELECT member_points_per_attendance FROM events WHERE id = ?
            """, (event_id,))
            event_data = cursor.fetchone()
            if not event_data:
                return False
            
            points_per_attendance = event_data[0]
            
            # Record each member's attendance
            for member_id, attended in member_attendances.items():
                points = points_per_attendance if attended else 0
                
                cursor.execute("""
                    INSERT OR REPLACE INTO attendance 
                    (event_id, member_id, attended, points_earned, recorded_by)
                    VALUES (?, ?, ?, ?, ?)
                """, (event_id, member_id, attended, points, recorded_by))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"Error recording member attendance: {e}")
            return False
        finally:
            conn.close()
    
    def record_coach_attendance(self, event_id: int, coach_attendances: Dict[int, int],
                               recorded_by: str = "Admin") -> bool:
        """Record attendance for coaches (with session counts)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get event points
            cursor.execute("""
                SELECT coach_points_per_attendance FROM events WHERE id = ?
            """, (event_id,))
            event_data = cursor.fetchone()
            if not event_data:
                return False
            
            points_per_session = event_data[0]
            
            # Record each coach's attendance
            for coach_id, sessions_attended in coach_attendances.items():
                attended = sessions_attended > 0
                points = sessions_attended * points_per_session
                
                cursor.execute("""
                    INSERT OR REPLACE INTO attendance 
                    (event_id, coach_id, attended, points_earned, recorded_by)
                    VALUES (?, ?, ?, ?, ?)
                """, (event_id, coach_id, attended, points, recorded_by))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"Error recording coach attendance: {e}")
            return False
        finally:
            conn.close()
    
    def get_teams_for_attendance(self) -> pd.DataFrame:
        """Get all teams with their members for attendance recording"""
        conn = self.db_manager.get_connection()
        
        df = pd.read_sql_query("""
            SELECT 
                t.id as team_id,
                t.name as team_name,
                m.id as member_id,
                m.name as member_name,
                m.department as member_department,
                m.is_leader
            FROM teams t
            JOIN members m ON t.id = m.team_id
            WHERE t.is_active = 1 AND m.is_active = 1
            ORDER BY t.name, m.name
        """, conn)
        
        conn.close()
        return df
    
    def get_coaches_for_attendance(self) -> pd.DataFrame:
        """Get all coaches for attendance recording"""
        conn = self.db_manager.get_connection()
        
        df = pd.read_sql_query("""
            SELECT 
                id as coach_id,
                name as coach_name,
                department as coach_department
            FROM coaches
            WHERE is_active = 1
            ORDER BY name
        """, conn)
        
        conn.close()
        return df
    
    def bulk_import_attendance(self, event_id: int, attendance_data: pd.DataFrame) -> Tuple[bool, str]:
        """
        Bulk import attendance from CSV/Excel
        Expected columns: team_name, member_name, attended (bool), points_earned (optional)
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Validate event exists
            cursor.execute("SELECT id, member_points_per_attendance FROM events WHERE id = ?", (event_id,))
            event_data = cursor.fetchone()
            if not event_data:
                return False, "Event not found"
            
            default_points = event_data[1]
            
            # Get member IDs for lookup
            cursor.execute("""
                SELECT m.id, m.name, t.name as team_name
                FROM members m
                JOIN teams t ON m.team_id = t.id
                WHERE m.is_active = 1
            """)
            
            member_lookup = {}
            for member_id, member_name, team_name in cursor.fetchall():
                member_lookup[(team_name, member_name)] = member_id
            
            # Process attendance data
            records_processed = 0
            errors = []
            
            for _, row in attendance_data.iterrows():
                team_name = row.get('team_name', '').strip()
                member_name = row.get('member_name', '').strip()
                attended = bool(row.get('attended', False))
                points = row.get('points_earned', default_points if attended else 0)
                
                member_id = member_lookup.get((team_name, member_name))
                if not member_id:
                    errors.append(f"Member not found: {member_name} from {team_name}")
                    continue
                
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO attendance 
                        (event_id, member_id, attended, points_earned, recorded_by)
                        VALUES (?, ?, ?, ?, ?)
                    """, (event_id, member_id, attended, int(points), "Bulk Import"))
                    records_processed += 1
                    
                except Exception as e:
                    errors.append(f"Error recording {member_name}: {str(e)}")
            
            conn.commit()
            
            if errors:
                error_summary = f"Processed {records_processed} records with {len(errors)} errors"
                return True, error_summary
            else:
                return True, f"Successfully processed {records_processed} attendance records"
                
        except Exception as e:
            conn.rollback()
            return False, f"Import failed: {str(e)}"
        finally:
            conn.close()
    
    def update_event(self, event_id: int, **kwargs) -> bool:
        """Update event details"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Build update query dynamically
            valid_fields = ['name', 'description', 'event_date', 'event_type', 
                           'member_points_per_attendance', 'coach_points_per_attendance', 'is_active']
            
            update_fields = []
            values = []
            
            for field, value in kwargs.items():
                if field in valid_fields:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
            
            if not update_fields:
                return False
            
            values.append(event_id)
            
            cursor.execute(f"""
                UPDATE events 
                SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            print(f"Error updating event: {e}")
            return False
        finally:
            conn.close()
    
    def delete_event(self, event_id: int, soft_delete: bool = True) -> bool:
        """Delete event (soft delete by default)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            if soft_delete:
                cursor.execute("""
                    UPDATE events SET is_active = 0 WHERE id = ?
                """, (event_id,))
            else:
                # Hard delete - this will cascade to attendance records
                cursor.execute("""
                    DELETE FROM events WHERE id = ?
                """, (event_id,))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            print(f"Error deleting event: {e}")
            return False
        finally:
            conn.close()
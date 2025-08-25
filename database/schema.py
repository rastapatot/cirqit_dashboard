"""
CirQit Hackathon Dashboard - Production Database Schema
This module defines the complete database schema for accurate scoring and event management
"""

import sqlite3
from typing import List, Dict, Any
from datetime import datetime, date
import pandas as pd

class DatabaseManager:
    """Production-ready database manager for CirQit Dashboard"""
    
    def __init__(self, db_path: str = "cirqit_dashboard.db"):
        self.db_path = db_path
        self.version = 1  # Database schema version for future migrations
    
    def get_connection(self):
        """Get database connection with proper settings"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        return conn
    
    def initialize_database(self):
        """Initialize database with complete schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create all tables
        self._create_teams_table(cursor)
        self._create_members_table(cursor)
        self._create_coaches_table(cursor)
        self._create_events_table(cursor)
        self._create_attendance_table(cursor)
        self._create_bonus_points_table(cursor)
        self._create_audit_log_table(cursor)
        self._create_schema_version_table(cursor)
        
        # Create indexes for performance
        self._create_indexes(cursor)
        
        # Create views for easy querying
        self._create_views(cursor)
        
        # Insert initial schema version
        cursor.execute(
            "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
            (self.version, datetime.now())
        )
        
        conn.commit()
        conn.close()
        print("✅ Database schema initialized successfully")
    
    def _create_teams_table(self, cursor):
        """Create teams table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                total_members INTEGER NOT NULL,
                coach_id INTEGER,
                department TEXT,
                registration_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (coach_id) REFERENCES coaches(id)
            )
        """)
    
    def _create_members_table(self, cursor):
        """Create members table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT,
                team_id INTEGER NOT NULL,
                is_leader BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                UNIQUE(name, team_id)
            )
        """)
    
    def _create_coaches_table(self, cursor):
        """Create coaches table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coaches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                department TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def _create_events_table(self, cursor):
        """Create events table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                event_type TEXT NOT NULL DEFAULT 'tech_sharing',
                event_date DATE NOT NULL,
                member_points_per_attendance INTEGER DEFAULT 1,
                coach_points_per_attendance INTEGER DEFAULT 2,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def _create_attendance_table(self, cursor):
        """Create attendance table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                member_id INTEGER,
                coach_id INTEGER,
                attended BOOLEAN NOT NULL DEFAULT TRUE,
                points_earned INTEGER NOT NULL DEFAULT 0,
                session_type TEXT DEFAULT 'day',
                notes TEXT,
                recorded_by TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
                FOREIGN KEY (coach_id) REFERENCES coaches(id) ON DELETE CASCADE,
                CHECK (member_id IS NOT NULL OR coach_id IS NOT NULL),
                UNIQUE(event_id, member_id, coach_id)
            )
        """)
    
    def _create_bonus_points_table(self, cursor):
        """Create bonus points table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bonus_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                points INTEGER NOT NULL,
                reason TEXT NOT NULL,
                awarded_by TEXT NOT NULL,
                awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
            )
        """)
    
    def _create_audit_log_table(self, cursor):
        """Create audit log for tracking changes"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                old_values TEXT,
                new_values TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def _create_schema_version_table(self, cursor):
        """Create schema version table for migrations"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
    
    def _create_indexes(self, cursor):
        """Create performance indexes"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_members_team ON members(team_id)",
            "CREATE INDEX IF NOT EXISTS idx_members_active ON members(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_event ON attendance(event_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_member ON attendance(member_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_coach ON attendance(coach_id)",
            "CREATE INDEX IF NOT EXISTS idx_bonus_team ON bonus_points(team_id)",
            "CREATE INDEX IF NOT EXISTS idx_bonus_active ON bonus_points(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date)",
            "CREATE INDEX IF NOT EXISTS idx_events_active ON events(is_active)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    def _create_views(self, cursor):
        """Create database views for easy querying"""
        
        # Team scores view - the main scoring calculation
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_team_scores AS
            SELECT 
                t.id as team_id,
                t.name as team_name,
                t.total_members,
                t.department as team_department,
                
                -- Member scoring
                COALESCE(member_stats.total_points, 0) as member_points,
                COALESCE(member_stats.unique_attendees, 0) as members_attended,
                ROUND(
                    CAST(COALESCE(member_stats.unique_attendees, 0) AS FLOAT) / t.total_members * 100, 1
                ) as member_attendance_rate,
                
                -- Coach scoring  
                COALESCE(coach_stats.total_points, 0) as coach_points,
                COALESCE(coach_stats.sessions_attended, 0) as coach_sessions_attended,
                
                -- Bonus points
                COALESCE(bonus_stats.total_bonus, 0) as bonus_points,
                
                -- Total scores
                (COALESCE(member_stats.total_points, 0) + COALESCE(coach_stats.total_points, 0)) as base_score,
                (COALESCE(member_stats.total_points, 0) + COALESCE(coach_stats.total_points, 0) + COALESCE(bonus_stats.total_bonus, 0)) as final_score,
                
                t.created_at
                
            FROM teams t
            
            -- Member statistics
            LEFT JOIN (
                SELECT 
                    m.team_id,
                    SUM(a.points_earned) as total_points,
                    COUNT(DISTINCT CASE WHEN a.attended = 1 THEN m.id END) as unique_attendees,
                    COUNT(DISTINCT a.event_id) as events_participated
                FROM members m
                LEFT JOIN attendance a ON m.id = a.member_id
                WHERE m.is_active = 1
                GROUP BY m.team_id
            ) member_stats ON t.id = member_stats.team_id
            
            -- Coach statistics
            LEFT JOIN (
                SELECT 
                    t.id as team_id,
                    SUM(a.points_earned) as total_points,
                    COUNT(DISTINCT a.event_id) as sessions_attended
                FROM teams t
                JOIN coaches c ON t.coach_id = c.id
                JOIN attendance a ON c.id = a.coach_id
                WHERE a.attended = 1
                GROUP BY t.id
            ) coach_stats ON t.id = coach_stats.team_id
            
            -- Bonus points
            LEFT JOIN (
                SELECT 
                    team_id,
                    SUM(points) as total_bonus
                FROM bonus_points
                WHERE is_active = 1
                GROUP BY team_id
            ) bonus_stats ON t.id = bonus_stats.team_id
            
            WHERE t.is_active = 1
            ORDER BY final_score DESC, team_name
        """)
        
        # Individual member scores view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_member_scores AS
            SELECT 
                m.id as member_id,
                m.name as member_name,
                m.department as member_department,
                t.id as team_id,
                t.name as team_name,
                m.is_leader,
                
                COALESCE(SUM(a.points_earned), 0) as total_points,
                COUNT(CASE WHEN a.attended = 1 THEN 1 END) as events_attended,
                COUNT(DISTINCT a.event_id) as unique_events_attended,
                
                -- Event breakdown (using GROUP_CONCAT for SQLite)
                GROUP_CONCAT(
                    CASE WHEN a.attended = 1 THEN e.name END, ', '
                ) as events_list
                
            FROM members m
            JOIN teams t ON m.team_id = t.id
            LEFT JOIN attendance a ON m.id = a.member_id
            LEFT JOIN events e ON a.event_id = e.id
            WHERE m.is_active = 1 AND t.is_active = 1
            GROUP BY m.id, m.name, m.department, t.id, t.name, m.is_leader
            ORDER BY t.name, total_points DESC, m.name
        """)
        
        # Coach scores view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_coach_scores AS
            SELECT 
                c.id as coach_id,
                c.name as coach_name,
                c.department as coach_department,
                
                COALESCE(SUM(CASE WHEN a.attended = 1 THEN a.points_earned ELSE 0 END), 0) as total_points,
                COUNT(CASE WHEN a.attended = 1 THEN 1 END) as sessions_attended,
                COUNT(DISTINCT CASE WHEN a.attended = 1 THEN a.event_id END) as unique_events_attended,
                
                -- Teams coached (direct relationship)
                GROUP_CONCAT(DISTINCT t.name) as teams_coached
                
            FROM coaches c
            LEFT JOIN teams t ON c.id = t.coach_id
            LEFT JOIN attendance a ON c.id = a.coach_id
            WHERE c.is_active = 1
            GROUP BY c.id, c.name, c.department
            ORDER BY total_points DESC, c.name
        """)
    
    def get_schema_version(self) -> int:
        """Get current database schema version"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            return result[0] if result[0] else 0
        except sqlite3.OperationalError:
            return 0
        finally:
            conn.close()
    
    def backup_database(self, backup_path: str = None) -> str:
        """Create a backup of the database"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"cirqit_dashboard_backup_{timestamp}.db"
        
        import shutil
        shutil.copy2(self.db_path, backup_path)
        return backup_path
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate database integrity and return report"""
        conn = self.get_connection()
        
        integrity_report = {
            "valid": True,
            "issues": [],
            "stats": {}
        }
        
        try:
            # Check foreign key constraints
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()
            
            if fk_violations:
                integrity_report["valid"] = False
                integrity_report["issues"].append(f"Foreign key violations: {len(fk_violations)}")
            
            # Get basic statistics
            stats_queries = {
                "teams": "SELECT COUNT(*) FROM teams WHERE is_active = 1",
                "members": "SELECT COUNT(*) FROM members WHERE is_active = 1", 
                "coaches": "SELECT COUNT(*) FROM coaches WHERE is_active = 1",
                "events": "SELECT COUNT(*) FROM events WHERE is_active = 1",
                "attendance_records": "SELECT COUNT(*) FROM attendance"
            }
            
            for stat_name, query in stats_queries.items():
                cursor.execute(query)
                integrity_report["stats"][stat_name] = cursor.fetchone()[0]
                
        except Exception as e:
            integrity_report["valid"] = False
            integrity_report["issues"].append(f"Database error: {str(e)}")
        finally:
            conn.close()
        
        return integrity_report

if __name__ == "__main__":
    # Initialize database when run directly
    db_manager = DatabaseManager()
    db_manager.initialize_database()
    
    # Validate integrity
    report = db_manager.validate_data_integrity()
    print(f"Database integrity: {'✅ Valid' if report['valid'] else '❌ Issues found'}")
    for issue in report["issues"]:
        print(f"  ⚠️ {issue}")
    
    print("\nDatabase Statistics:")
    for stat, value in report["stats"].items():
        print(f"  {stat}: {value}")
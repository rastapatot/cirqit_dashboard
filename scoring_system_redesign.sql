-- CirQit Hackathon Scoring System Database Schema
-- This replaces the flawed CSV-based approach with proper relational data

-- Teams table
CREATE TABLE teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    total_members INTEGER NOT NULL,
    coach_name TEXT,
    coach_department TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Members table  
CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department TEXT,
    team_id INTEGER NOT NULL,
    is_leader BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

-- Events/Sessions table
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- 'tech_sharing', 'workshop', etc.
    date_held DATE,
    member_points_per_attendance INTEGER DEFAULT 1,
    coach_points_per_attendance INTEGER DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Individual attendance records (the key to accuracy)
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER,
    coach_name TEXT, -- for coach attendance
    event_id INTEGER NOT NULL,
    attended BOOLEAN NOT NULL DEFAULT TRUE,
    points_earned INTEGER NOT NULL,
    session_type TEXT, -- 'day', 'night'
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (event_id) REFERENCES events(id)
);

-- Bonus points (existing functionality)
CREATE TABLE bonus_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    points INTEGER NOT NULL,
    reason TEXT,
    awarded_by TEXT,
    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

-- Create indexes for performance
CREATE INDEX idx_members_team ON members(team_id);
CREATE INDEX idx_attendance_member ON attendance(member_id);
CREATE INDEX idx_attendance_event ON attendance(event_id);
CREATE INDEX idx_bonus_team ON bonus_points(team_id);

-- Views for easy scoring calculations
CREATE VIEW team_scores AS
SELECT 
    t.id as team_id,
    t.name as team_name,
    t.total_members,
    t.coach_name,
    COALESCE(member_points.total, 0) as total_member_points,
    COALESCE(coach_points.total, 0) as total_coach_points,
    COALESCE(bonus.total, 0) as total_bonus_points,
    (COALESCE(member_points.total, 0) + COALESCE(coach_points.total, 0)) as base_score,
    (COALESCE(member_points.total, 0) + COALESCE(coach_points.total, 0) + COALESCE(bonus.total, 0)) as final_score,
    ROUND(
        (CAST(COALESCE(member_attendees.unique_count, 0) AS FLOAT) / t.total_members) * 100, 1
    ) as member_attendance_rate
FROM teams t
LEFT JOIN (
    -- Total member points per team
    SELECT m.team_id, SUM(a.points_earned) as total
    FROM members m
    JOIN attendance a ON m.id = a.member_id
    GROUP BY m.team_id
) member_points ON t.id = member_points.team_id
LEFT JOIN (
    -- Total coach points per team  
    SELECT t.id as team_id, SUM(a.points_earned) as total
    FROM teams t
    JOIN attendance a ON t.coach_name = a.coach_name
    GROUP BY t.id
) coach_points ON t.id = coach_points.team_id
LEFT JOIN (
    -- Total bonus points per team
    SELECT team_id, SUM(points) as total
    FROM bonus_points
    GROUP BY team_id  
) bonus ON t.id = bonus.team_id
LEFT JOIN (
    -- Count unique members who attended any event
    SELECT m.team_id, COUNT(DISTINCT m.id) as unique_count
    FROM members m
    JOIN attendance a ON m.id = a.member_id
    WHERE a.attended = TRUE
    GROUP BY m.team_id
) member_attendees ON t.id = member_attendees.team_id;

CREATE VIEW individual_member_scores AS
SELECT 
    m.id as member_id,
    m.name as member_name,
    m.department,
    t.name as team_name,
    COALESCE(SUM(a.points_earned), 0) as total_points,
    COUNT(CASE WHEN a.attended = TRUE THEN 1 END) as events_attended
FROM members m
JOIN teams t ON m.team_id = t.id
LEFT JOIN attendance a ON m.id = a.member_id
GROUP BY m.id, m.name, m.department, t.name;
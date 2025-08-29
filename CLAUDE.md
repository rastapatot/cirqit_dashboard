# Claude Code Notes

## Current State (2025-08-29)

**Main Application File**: `streamlit_app.py`
- This is the ONLY dashboard file - all others have been removed
- Contains the complete CirQit Hackathon Dashboard with database-driven scoring
- Includes first-name-only display feature (scoring logic unchanged)

**Key Features**:
- Team Leaderboard
- Team Explorer  
- Coach Explorer
- Event Analytics
- Admin Panel

**Running the Dashboard**:
```bash
streamlit run streamlit_app.py --server.port 8501
```

**Admin Access**: Password is `cirqit2024`

## Recent Changes

### Name Display Update (2025-08-29)
- Added `get_first_name()` helper function
- All member and coach names now display first names only
- Team names remain unchanged
- Database and scoring logic unchanged - still uses full names
- Updated locations:
  - Team Explorer member tables
  - Coach Explorer displays
  - Admin panel selection dropdowns
  - Bonus point award confirmations

### File Cleanup (2025-08-29)
- Removed outdated files: `app.py`, `app_production.py`, `app_updated.py`
- Renamed `app_clean.py` → `streamlit_app.py` (standard entry point)
- Updated all documentation references

**IMPORTANT**: Always work on `streamlit_app.py` going forward - it's the single source of truth.
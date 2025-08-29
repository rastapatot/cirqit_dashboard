#!/usr/bin/env python3
"""
Simple migration runner for CirQit Dashboard
Run this script to migrate from CSV to production database
"""

import sys
import os

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager, DataMigration

def main():
    print("🚀 CirQit Dashboard Migration Tool")
    print("=" * 50)
    
    # Initialize database manager
    db_manager = DatabaseManager("cirqit_dashboard.db")
    
    # Check current status
    current_version = db_manager.get_schema_version()
    print(f"Current database version: {current_version}")
    
    if current_version > 0:
        print("✅ Database already migrated!")
        
        # Show current statistics
        integrity_report = db_manager.validate_data_integrity()
        print(f"Database integrity: {'✅ Valid' if integrity_report['valid'] else '❌ Issues'}")
        
        print("\nCurrent statistics:")
        for stat, value in integrity_report["stats"].items():
            print(f"  {stat}: {value}")
        
        return
    
    print("Starting fresh migration...")
    
    # Check if CSV files exist
    csv_files = [
        "CirQit-TC-TeamScores-AsOf-2025-08-23.csv",
        "teams-masterlist.csv"
    ]
    
    missing_files = []
    for file in csv_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required CSV files:")
        for file in missing_files:
            print(f"  - {file}")
        return
    
    print("✅ Found required CSV files")
    
    # Run migration
    migration = DataMigration(db_manager)
    
    print("\n📊 Starting data migration...")
    success = migration.migrate_from_csv(
        "CirQit-TC-TeamScores-AsOf-2025-08-23.csv",
        "teams-masterlist.csv"
    )
    
    # Show results
    report = migration.get_migration_report()
    
    print(f"\n{'='*50}")
    print("MIGRATION RESULTS")
    print(f"{'='*50}")
    print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"Total steps: {report['total_steps']}")
    print(f"Successful: {report['success_count']}")
    print(f"Errors: {report['error_count']}")
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now run the production dashboard with:")
        print("  streamlit run streamlit_app.py")
        
        # Validate final result
        integrity_report = db_manager.validate_data_integrity()
        print(f"\nFinal validation: {'✅ PASSED' if integrity_report['valid'] else '❌ FAILED'}")
        
        if integrity_report['valid']:
            print("\nDatabase statistics:")
            for stat, value in integrity_report["stats"].items():
                print(f"  {stat}: {value}")
    else:
        print("\n❌ Migration failed!")
        print("Errors encountered:")
        for log in report['migration_log']:
            if log['status'] == 'ERROR':
                print(f"  - {log['step']}: {log['details']}")

if __name__ == "__main__":
    main()
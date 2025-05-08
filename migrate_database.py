"""
migrate_database.py - Run this script to migrate data from JSON to SQLite
"""
import os
import sys
from database_manager import initialize_database, migrate_from_json

def main():
    print("Starting database migration...")
    
    # Initialize database
    if initialize_database():
        print("Database structure created successfully.")
    else:
        print("Failed to create database structure.")
        sys.exit(1)
    
    # Migrate data
    if migrate_from_json():
        print("Data migration completed successfully.")
    else:
        print("Data migration failed.")
        sys.exit(1)
    
    print("Migration complete! Your application is now using SQLite for storage.")
    print("You can safely delete the user_database.json file and the conversation_histories folder after confirming everything works correctly.")

if __name__ == "__main__":
    main()
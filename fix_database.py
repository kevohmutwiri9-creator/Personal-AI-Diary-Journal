#!/usr/bin/env python3
"""
Database schema fix script for password reset functionality.
Run this script to add the required email columns to the user table.
"""

import sqlite3
import os

def fix_database_schema():
    """Add missing columns to the user table for password reset functionality."""

    db_path = 'instance/diary.db'

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database file not found at: {db_path}")
        print("Please make sure your Flask application has created the database.")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("🔧 Fixing database schema for password reset functionality...")

        # Check current schema
        cursor.execute("PRAGMA table_info(user)")
        existing_columns = [row[1] for row in cursor.fetchall()]

        print(f"📋 Current columns: {existing_columns}")

        # Define required columns for password reset
        required_columns = {
            'email': 'VARCHAR(120)',
            'email_verified': 'BOOLEAN DEFAULT 0',
            'reset_token': 'VARCHAR(100)',
            'reset_token_expires': 'DATETIME'
        }

        # Add missing columns
        added_columns = []
        for col_name, col_type in required_columns.items():
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}")
                    added_columns.append(col_name)
                    print(f"✅ Added column: {col_name} ({col_type})")
                except sqlite3.OperationalError as e:
                    print(f"⚠️  Could not add column {col_name}: {e}")
            else:
                print(f"ℹ️  Column {col_name} already exists")

        if added_columns:
            conn.commit()
            print(f"\n🎉 Successfully added {len(added_columns)} columns: {', '.join(added_columns)}")
        else:
            print("\nℹ️  All required columns already exist!")

        # Verify final schema
        cursor.execute("PRAGMA table_info(user)")
        final_columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Final columns: {final_columns}")

        # Check if we have all required columns
        missing_columns = [col for col in required_columns.keys() if col not in final_columns]

        if missing_columns:
            print(f"\n❌ Still missing columns: {missing_columns}")
            return False
        else:
            print("\n✅ Database schema is now complete for password reset functionality!")
            return True

    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("\n🚀 You can now test the password reset functionality!")
        print("   1. Start your Flask app: python app.py")
        print("   2. Go to: http://127.0.0.1:5000")
        print("   3. Click 'Login' → 'Forgot your password?'")
        print("   4. Enter your email and test the reset flow")
    else:
        print("\n⚠️  Database schema fix incomplete. Please check the errors above.")

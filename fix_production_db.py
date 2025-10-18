#!/usr/bin/env python3
"""
Emergency database fix script for production deployment.
Run this if migrations don't apply automatically.
"""

import os
import sys

# Set up Flask environment
os.environ['FLASK_APP'] = 'app.py'

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

from app import app, db

def fix_database():
    """Fix missing columns in production database"""
    with app.app_context():
        try:
            # Check if theme_preference column exists
            result = db.session.execute("""
                SELECT sql FROM sqlite_master
                WHERE type='table' AND name='user'
            """).fetchone()

            if result and 'theme_preference' not in result[0]:
                print("🔧 Adding missing theme_preference column...")

                # Add the missing column
                db.session.execute("""
                    ALTER TABLE user ADD COLUMN theme_preference VARCHAR(10) DEFAULT 'light'
                """)
                db.session.commit()
                print("✅ theme_preference column added successfully!")
            else:
                print("✅ theme_preference column already exists")

            # Verify the fix
            try:
                test_user = db.session.execute("""
                    SELECT theme_preference FROM user LIMIT 1
                """).fetchone()
                print("✅ Database fix verified - theme_preference column accessible")
            except Exception as e:
                print(f"❌ Database verification failed: {e}")
                return False

            return True

        except Exception as e:
            print(f"❌ Database fix failed: {e}")
            return False

if __name__ == "__main__":
    print("🚀 Starting emergency database fix...")
    success = fix_database()

    if success:
        print("🎉 Database fix completed successfully!")
        print("Your application should now work properly.")
    else:
        print("❌ Database fix failed. Manual intervention may be required.")
        sys.exit(1)

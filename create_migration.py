#!/usr/bin/env python3
import os
import sys

# Set up Flask environment
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'production'

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

from flask import Flask
from flask_migrate import Migrate
from app import app, db

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Create migration
with app.app_context():
    from flask_migrate import upgrade
    from alembic.command import revision, upgrade as alembic_upgrade
    from alembic.config import Config

    # Create a new migration
    alembic_cfg = Config("migrations/alembic.ini")
    revision(alembic_cfg, message="Add theme_preference column to user table", rev_id=None)

print("Migration created successfully!")

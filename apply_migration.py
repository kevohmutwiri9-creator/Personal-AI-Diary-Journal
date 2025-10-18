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

# Apply the migration
with app.app_context():
    from flask_migrate import upgrade
    upgrade()

print("Migration applied successfully!")

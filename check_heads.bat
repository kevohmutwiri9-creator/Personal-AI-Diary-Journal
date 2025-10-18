@echo off
set FLASK_APP=app.py
python -m flask db heads

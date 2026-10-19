@echo off
REM Right-click this file -> "Run as administrator" for full automated-check coverage.
cd /d "%~dp0"
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
streamlit run app.py
pause

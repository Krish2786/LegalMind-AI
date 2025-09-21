@echo off
TITLE LegalMind AI Backend Server
echo Starting the server...

REM Activate the virtual environment
call .\venv\Scripts\activate

REM Run the Python application
echo Starting Flask app (app.py)...
python app.py

REM Keep the window open if the script finishes or fails
pause
@echo off

REM Change drive
F:

REM Navigate to project folder
cd "F:\SNU HC Products\ClaimIQ"

echo ============================
echo Pulling latest code from GitHub...
echo ============================
git pull

REM Check if virtual environment exists
if not exist .venv (
    echo ============================
    echo Creating virtual environment...
    echo ============================
    python -m venv .venv
)

echo ============================
echo Activating virtual environment...
echo ============================
call .venv\Scripts\activate

echo ============================
echo Installing/updating requirements...
echo ============================
python.exe -m pip install --upgrade pip
pip install -r requirements.txt

echo ============================
echo Starting application...
echo ============================
uvicorn main:app --port 8000

pause
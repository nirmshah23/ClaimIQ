@echo off

REM Change drive to F:
F:

REM Change directory to the project folder
cd "F:\SNU HC Products\ClaimIQ"

REM Run uvicorn
uvicorn main:app --reload

pause
@echo off

REM Change drive to G:
G:

REM Change directory to the project folder
cd "G:\My Drive\Python Projects\ClaimCraft"

REM Run uvicorn
uvicorn main:app --reload

pause

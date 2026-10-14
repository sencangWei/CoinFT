@echo off
cd /d "%~dp0"
"D:\conda\python.exe" coinft_demo.py --port COM6
if errorlevel 1 pause

@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0startup.ps1" -Enable
pause

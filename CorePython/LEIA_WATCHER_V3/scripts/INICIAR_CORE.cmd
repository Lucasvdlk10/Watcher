@echo off
set "PY=%LOCALAPPDATA%\Programs\LEIAWatcher\.venv\Scripts\python.exe"
if not exist "%PY%" (
 echo Programa nao instalado. Execute INSTALAR_WINDOWS.cmd primeiro.
 pause
 exit /b 1
)
"%PY%" -m leia_watcher.main
pause

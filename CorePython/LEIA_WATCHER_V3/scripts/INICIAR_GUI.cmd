@echo off
set "PY=%LOCALAPPDATA%\Programs\LEIAWatcher\.venv\Scripts\pythonw.exe"
if not exist "%PY%" (
 echo Programa nao instalado. Execute INSTALAR_WINDOWS.cmd primeiro.
 pause
 exit /b 1
)
start "LEIA Watcher UI" "%PY%" -m leia_watcher.ui

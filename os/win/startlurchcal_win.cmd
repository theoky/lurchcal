@echo off
setlocal

cd /d "%~dp0"

rem Optional overrides: LURCHCAL_WEB_PORT (8000), LURCHCAL_TASK_SERVER_PORT (8001)
set "LURCHCAL_WEB_HOST=127.0.0.1"
set "LURCHCAL_TASK_SERVER_HOST=127.0.0.1"
if not defined LURCHCAL_WEB_PORT set "LURCHCAL_WEB_PORT=8000"
if not defined LURCHCAL_TASK_SERVER_PORT set "LURCHCAL_TASK_SERVER_PORT=8001"
set "LURCHCAL_URL=http://%LURCHCAL_WEB_HOST%:%LURCHCAL_WEB_PORT%"

call C:\apps\ac3\Scripts\activate.bat C:\apps\ac3
if errorlevel 1 goto :environment_error
call conda activate lurchcal
if errorlevel 1 goto :environment_error

set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
set "LURCHCAL_TASK_SERVER_CONFIG=%LOCALAPPDATA%\LurchCal\task_server.ini"

rem Reuse any service already listening on the configured port.
python "%~dp0scripts\check_port.py" LURCHCAL_TASK_SERVER_HOST LURCHCAL_TASK_SERVER_PORT

if errorlevel 1 (
    echo Starting task server...
    start "LurchCal Task Server" /D "%~dp0src" cmd /k "python -m task_server"
)

python "%~dp0scripts\check_port.py" LURCHCAL_WEB_HOST LURCHCAL_WEB_PORT

if errorlevel 1 (
    echo Starting web server...
    start "LurchCal Web Server" /D "%~dp0src" cmd /k "python -m lurchcal.web_server"
)

echo Waiting for LurchCal at %LURCHCAL_URL% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='%LURCHCAL_URL%'; for($i=0;$i -lt 40;$i++){try{$r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 $u; if($r.StatusCode -eq 200){Start-Process $u; exit 0}}catch{}; Start-Sleep -Seconds 1}; exit 1"
if errorlevel 1 goto :readiness_error
echo LurchCal is open in your default browser.
echo To stop the services, close the two LurchCal service command windows.
exit /b 0

:environment_error
echo Could not activate the configured Python environment (C:\apps\ac3, lurchcal).
exit /b 1

:startup_error
echo A service could not be started. Check the LurchCal service command windows.
exit /b 1

:readiness_error
echo LurchCal did not become reachable at %LURCHCAL_URL% within 40 seconds.
echo Check the service command windows and configured ports.
exit /b 1
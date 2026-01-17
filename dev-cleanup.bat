@echo off
echo === QT Video SaaS - Port Cleanup ===
echo.

echo Killing processes on port 3001-3009 (Next.js loose instances)...
for /L %%p in (3001,1,3009) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%p ^| findstr LISTENING 2^>nul') do (
        echo Killing PID %%a on port %%p
        taskkill /F /PID %%a 2>nul
    )
)

echo.
echo Killing processes on port 8001-8009 (Backend loose instances)...
for /L %%p in (8001,1,8009) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%p ^| findstr LISTENING 2^>nul') do (
        echo Killing PID %%a on port %%p
        taskkill /F /PID %%a 2>nul
    )
)

echo.
echo === Cleanup Complete ===
echo Docker services (3000, 8000) preserved.
echo.
pause

@echo off
REM ===========================================
REM QT Video SaaS - Development Mode (로컬 개발)
REM ===========================================
REM Docker 없이 로컬에서 개발 (Backend + Frontend 분리)
echo.
echo QT Video SaaS 개발 모드
echo.
echo [선택] 어떤 서비스를 실행할까요?
echo   1. Backend Only (FastAPI + Celery)
echo   2. Frontend Only (Next.js)
echo   3. Both (새 창에서 각각 실행)
echo   4. Docker 전체 (docker-compose)
echo.
set /p choice="번호 입력 (1-4): "

if "%choice%"=="1" goto backend
if "%choice%"=="2" goto frontend
if "%choice%"=="3" goto both
if "%choice%"=="4" goto docker
goto end

:backend
echo.
echo [Backend] FastAPI 서버 시작...
cd backend
call pip install -r requirements.txt
echo.
echo Redis 필요! 다른 터미널에서 실행: docker run -p 6379:6379 redis:7-alpine
echo.
start cmd /k "celery -A app.celery_app worker --loglevel=info"
timeout /t 2 /nobreak > nul
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
goto end

:frontend
echo.
echo [Frontend] Next.js 개발 서버 시작...
cd frontend
call npm install
npm run dev
goto end

:both
echo.
echo [Backend + Frontend] 두 서버 모두 시작...
start cmd /k "cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
start cmd /k "cd backend && celery -A app.celery_app worker --loglevel=info"
timeout /t 3 /nobreak > nul
start cmd /k "cd frontend && npm install && npm run dev"
echo.
echo 세 개의 터미널이 열렸습니다:
echo - FastAPI: http://localhost:8000
echo - Celery Worker
echo - Next.js: http://localhost:3000
echo.
echo Redis 필요! 다른 터미널에서: docker run -p 6379:6379 redis:7-alpine
goto end

:docker
echo.
echo [Docker] 전체 서비스 시작...
docker-compose up --build
goto end

:end
echo.
pause

@echo off
REM ===========================================
REM QT Video SaaS - Setup Script (Windows)
REM ===========================================
echo.
echo [1/4] 환경변수 파일 설정...
if not exist "backend\.env" (
    copy env.example backend\.env
    echo     backend\.env 생성됨 - API 키를 입력하세요!
    echo.
    echo     필요한 API 키:
    echo     - GROQ_API_KEY: https://console.groq.com
    echo     - R2_ACCESS_KEY_ID: https://dash.cloudflare.com
    echo     - SUPABASE_URL/KEY: https://supabase.com
    echo.
    notepad backend\.env
    pause
) else (
    echo     backend\.env 이미 존재함
)

echo.
echo [2/4] Docker 컨테이너 빌드...
docker-compose build

echo.
echo [3/4] Docker 컨테이너 시작...
docker-compose up -d

echo.
echo [4/4] 서비스 상태 확인...
timeout /t 5 /nobreak > nul
docker-compose ps

echo.
echo ===========================================
echo 설정 완료!
echo.
echo 접속 URL:
echo - Frontend: http://localhost:3000
echo - Backend API: http://localhost:8000
echo - Flower (작업 모니터링): http://localhost:5555
echo - API 문서: http://localhost:8000/docs
echo.
echo 로그 확인: docker-compose logs -f
echo 종료: docker-compose down
echo ===========================================
pause

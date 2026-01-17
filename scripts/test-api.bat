@echo off
REM ===========================================
REM QT Video SaaS - API Test Script
REM ===========================================
echo.
echo API 테스트 시작...
echo.

echo [1] Health Check...
curl -s http://localhost:8000/health
echo.
echo.

echo [2] API Docs 확인...
echo API 문서: http://localhost:8000/docs
echo.

echo [3] Frontend 확인...
curl -s -o nul -w "Frontend Status: %%{http_code}\n" http://localhost:3000
echo.

echo ===========================================
echo 테스트 완료!
echo.
echo 다음 단계:
echo 1. http://localhost:3000 접속
echo 2. MP3 파일 업로드 테스트
echo 3. 진행 상황 폴링 확인
echo ===========================================
pause

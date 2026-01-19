@echo off
REM PIL 텍스트 렌더링 적용 스크립트 (Windows)
REM 영상 생성 완료 후 실행

echo ======================================
echo PIL 텍스트 렌더링 적용 시작
echo ======================================
echo.

REM Step 1: 현재 디렉토리 확인
cd /d "%~dp0"

REM Step 2: 컨테이너 중지 및 삭제
echo [1/3] 기존 컨테이너 중지 및 삭제 중...
docker compose down
echo 완료!
echo.

REM Step 3: 이미지 재빌드 (Pillow 설치)
echo [2/3] Docker 이미지 빌드 중 (Pillow 설치)...
echo 이 작업은 3-5분 정도 걸릴 수 있습니다.
docker compose build api worker
echo 완료!
echo.

REM Step 4: 컨테이너 시작
echo [3/3] 새 컨테이너 시작 중...
docker compose up -d
echo 완료!
echo.

REM Step 5: 잠시 대기 후 로그 확인
echo ======================================
echo 적용 완료!
echo ======================================
echo.
echo API 서버 로그 확인 중...
timeout /t 5 /nobreak >nul
docker compose logs api --tail 30

echo.
echo ======================================
echo 확인 사항
echo ======================================
echo 1. ModuleNotFoundError가 없으면 성공!
echo 2. "Application startup complete" 메시지 확인
echo 3. 브라우저 새로고침 후 새 영상 생성 테스트
echo.
pause

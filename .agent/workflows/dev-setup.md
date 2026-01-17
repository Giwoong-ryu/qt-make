---
description: 개발 환경 포트 및 설정 표준 - 다른 AI 도구와 작업 시 포트/설정 충돌 방지
---

# QT Video SaaS 개발 환경 표준

> ⚠️ **경고**: 이 문서의 설정값은 절대 변경하지 마세요!  
> Claude Code, Gemini, 기타 AI 도구와 협업 시 충돌 방지를 위한 표준입니다.

---

## 📌 포트 표준

| 서비스 | 포트 | 비고 |
|--------|------|------|
| **Frontend (Next.js)** | `3000` | npm run dev |
| **Backend (FastAPI)** | `8000` | uvicorn |
| **Redis** | `6379` | Celery broker |
| **Flower (Celery 모니터링)** | `5555` | 선택적 |

---

## 📌 API URL 설정

### Frontend → Backend 통신
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```
- 파일 위치: `frontend/.env.local`
- **절대 변경 금지!**

### Docker Compose 모드
```
NEXT_PUBLIC_API_URL=http://api:8000
```
- Docker 내부 네트워크에서만 사용

---

## 📌 환경 변수 파일 위치

| 파일 | 위치 | 용도 |
|------|------|------|
| `.env` | 프로젝트 루트 | 공통 API 키 (Supabase, R2, Groq) |
| `frontend/.env.local` | frontend/ | Next.js 환경 변수 |
| `backend/.env` | backend/ | FastAPI 환경 변수 |

---

## 🚫 변경 금지 항목

1. **포트 번호** - 위 표준 포트 유지
2. **API URL** - 하드코딩 절대 금지, 환경 변수 사용
3. **docker-compose.yml 포트 매핑** - 현재 설정 유지
4. **CORS 설정** - `backend/app/main.py`의 origins 유지

---

## ✅ 새 기능 개발 시 체크리스트

- [ ] 새 포트가 필요한 경우 이 문서에 먼저 추가
- [ ] API URL은 환경 변수로 참조 (`process.env.NEXT_PUBLIC_API_URL`)
- [ ] 하드코딩된 `localhost:XXXX` 패턴 사용 금지

---

## 🔧 개발 환경 실행 방법

### 로컬 개발 (권장)
```bash
# 1. Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Frontend (새 터미널)
cd frontend
npm install
npm run dev

# 3. Redis (Docker)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 4. Celery Worker (새 터미널)
cd backend
celery -A app.celery_app worker --loglevel=info
```

### Docker Compose (전체 환경)
```bash
docker-compose up -d
```

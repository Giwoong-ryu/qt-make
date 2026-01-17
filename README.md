# QT Video SaaS - 교회 묵상 영상 자동화

> 목사님 음성(MP3) → 10분 내 배경 영상 자동 생성

## 프로젝트 개요

- **목적**: 교회 QT(Quiet Time) 영상 제작 자동화
- **타겟**: 자체 제작 교회 (월 2시간 편집 부담 해소)
- **가격**: 월 30,000원 (지인 추천 시 3만원)

## 기술 스택

| 레이어 | 기술 | 버전 |
|--------|------|------|
| Frontend | Next.js 15 | Latest |
| Backend | FastAPI | Latest |
| Queue | Celery + Redis | Latest |
| AI (STT) | Groq Whisper Large v3 Turbo | API |
| Storage | Cloudflare R2 | S3-compatible |
| Database | Supabase | PostgreSQL |
| Container | Docker + FFmpeg | Latest |
| Hosting (FE) | Vercel | Hobby (Free) |
| Hosting (BE) | Render | Free Tier |

## 비용 구조 (월)

- **Groq Whisper**: $0.04/hour × 4.67시간 = 2,428원
- **기타 인프라**: 0원 (Free tier)
- **총 비용**: 2,428원/월 (교회 10개 기준)

## 프로젝트 구조

```
qt-video-saas/
├── backend/              # FastAPI + Celery
│   ├── app/
│   │   ├── main.py      # FastAPI entry
│   │   ├── tasks.py     # Celery tasks
│   │   └── services/
│   │       ├── stt.py   # Groq Whisper
│   │       ├── video.py # FFmpeg composer
│   │       ├── storage.py # R2 upload
│   │       └── clips.py # Background selector
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/             # Next.js 15
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx # Upload page
│   │   │   └── api/
│   │   └── components/
│   ├── package.json
│   └── .env.local.example
│
├── clips/                # Background video packs
│   └── pack-free/
│
└── docker-compose.yml
```

## 개발 일정

- **Week 1**: 백엔드 핵심 기능 (Groq + FFmpeg + R2)
- **Week 2**: 프론트엔드 + 통합 테스트
- **Week 3-4**: 형님 교회 베타 테스트

## 로컬 개발 환경 설정

```bash
# 1. 백엔드
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. 프론트엔드
cd frontend
npm install

# 3. Docker Compose
docker-compose up -d
```

## 환경 변수

### Backend (.env)

```
GROQ_API_KEY=your_groq_api_key
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET_NAME=qt-videos
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Frontend (.env.local)

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 라이선스

Private - EazyPick Service

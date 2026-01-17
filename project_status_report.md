# 프로젝트 현황 보고서 (2026-01-18)

## 🚨 현재 문제점 (Current Issues & Failures)

### 1. 포트원(PortOne) V2 카카오페이 빌링키 발급 실패
- **현상**: PC 환경에서 `IFRAME` 방식으로 카카오페이 정기결제(빌링키 발급) 시도 시, 카카오페이 인증은 성공(`pg_token` 발급됨)하지만 웹사이트로 돌아왔을 때 **응답(Callback)을 받지 못하거나 `undefined`로 떨어지는 현상** 발생.
- **원인 추정**: 
  - 카카오페이의 PC 결제 프로세스 특성상, 팝업/리다이렉트 처리 과정에서 `IFRAME` 모드의 통신이 끊기거나 정상적으로 부모 창에 메시지를 전달하지 못하는 것으로 보임.
  - V2 SDK의 `requestIssueBillingKey`가 카카오페이와 같은 리다이렉트 기반 PG사에서 `IFRAME` 모드일 때 콜백 처리가 불안정할 수 있음.
- **시도된 해결책 (실패/보류)**:
  - `amount: 0`, `orderName` 파라미터 추가 (API 에러 해결됨)
  - CID `TCSUBSCRIP` 변경 (API 에러 해결됨)
  - `PORTONE_API_KEY` 환경변수 설정 (백엔드 통신 에러 해결됨)
  - `portone_service.py` 구문 오류 수정 (백엔드 실행 에러 해결됨)
  - PC `windowType`을 `REDIRECTION`으로 변경 시도했으나, 현재 코드는 다시 `IFRAME`으로 롤백됨.

### 2. 백엔드-프론트엔드 통신
- 결제 성공 콜백이 프론트엔드에서 트리거되지 않아, 백엔드의 `/api/subscription/activate` API가 호출되지 않고 있음.

---

## 🛠 구현 완료된 기능 (Implemented Features)

### 1. 결제 시스템 (Payment)
#### Frontend
- **PaymentButton.tsx**: 포트원 V2 SDK 연동, 결제 파라미터 구성 (`issueName`, `orderName`, `amount: 0` 등).
- **Callback Page**: `/subscription/callback` 페이지에서 리다이렉트 응답 처리 로직 구현 (현재 IFRAME 모드라 사용되지 않을 수 있음).
- **Subscription Page**: 구독 상태에 따른 UI 분기 처리.

#### Backend
- **PortOneService (`portone_service.py`)**:
  - `_get_access_token`: V2 API Secret을 이용한 포트원 액세스 토큰 발급 (캐싱 포함, 로깅 추가됨).
  - `charge_billing_key`: 발급된 빌링키를 이용한 정기 결제 승인 요청.
  - `cancel_payment`, `get_payment_history`: 결제 취소 및 내역 조회.
- **API Endpoints (`_subscription_apis.py`)**:
  - `POST /api/subscription/activate`: 빌링키 등록 및 첫 결제 수행.
  - `GET /api/subscription/status`: 구독 상태 조회.

### 2. 비디오 생성 엔진 (Video Engine)
#### Backend (`video.py`)
- **기본 합성**: 클립 연결, 오디오/자막 병합.
- **인트로 썸네일**: 영상 앞부분에 썸네일 이미지 및 페이드 인 효과 추가.
- **[NEW] 아웃트로 기능**: 
  - `_add_outro` 메서드 구현 완료.
  - 영상 끝에 아웃트로 이미지 추가 및 페이드 아웃/크로스페이드 효과 적용.
  - `compose_video_with_thumbnail` 메서드에서 아웃트로 처리 로직 연동 완료.

---

## 📅 향후 권장 작업 (Recommendations)
1. **PC 결제 방식 변경**: `PaymentButton.tsx`에서 `windowType.pc`를 `"REDIRECTION"`으로 변경하여 페이지 이동 방식으로 결제 흐름을 바꾸는 것을 강력 권장 (카카오페이 호환성 확보).
2. **백엔드 로그 모니터링**: 결제 성공 시 포트원 웹훅(Webhook)이 들어오는지 확인하여, 프론트엔드 콜백 실패 시 웹훅으로 구독 처리를 보완하는 로직 고려.

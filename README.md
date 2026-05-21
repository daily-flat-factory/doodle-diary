# 🎨 Doodle-Diary (Voice of the Heart)

AI가 일기를 읽고 어린이 그림일기 스타일의 그림을 그려주는 감성 일기 앱

---

## 프로젝트 구조

```
doodle-diary/
├── app.py                  # Flask 앱 진입점
├── config.py               # 환경변수 설정
├── requirements.txt
├── .env                    # 환경변수
├── database/
│   └── models.py           # SQLite 스키마 + DB 헬퍼
├── routes/
│   ├── diary.py            # 일기 CRUD API
│   └── user.py             # 사용자 초기화 / 데이터 삭제
├── services/
│   └── ai_service.py       # Claude API + HuggingFace 파이프라인
├── templates/
│   ├── base.html
│   ├── index.html          # 메인 (일기 작성)
│   └── diary.html          # 일기 상세
└── static/
    ├── css/style.css
    └── js/app.js
```

---

## 빠른 시작

```bash
# 1. 환경변수 설정
cp .env .env

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 실행
python app.py
# → http://localhost:5000
```

---

## 핵심 설계 원칙 (Privacy by Design)

| 원칙 | 구현 |
|------|------|
| 일기 원문 서버 미저장 | `ai_service.py`의 `process_diary()` 내에서만 사용 후 소멸 |
| 익명 UUID 기반 인증 | 이메일/전화번호 수집 없음 |
| 일일 생성 3회 제한 | `daily_limits` 테이블, 자정 리셋 |
| 완전 삭제 (hard delete) | `DELETE /api/user` → 모든 데이터 즉시 삭제 |
| 에러 로그 원문 미포함 | 에러 시 `diary_content` 절대 로깅 안 함 |

---

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/user/init` | 익명 UUID 발급 |
| GET | `/api/user/status` | 오늘 남은 횟수 확인 |
| GET | `/api/user/export` | 데이터 내보내기 (JSON) |
| DELETE | `/api/user` | 계정 + 전체 데이터 삭제 |
| POST | `/api/diary` | 일기 저장 + 이미지 생성 |
| GET | `/api/diary/list` | 일기 목록 |
| GET | `/api/diary/<id>` | 일기 상세 |
| DELETE | `/api/diary/<id>` | 일기 삭제 |

---

## 로드맵

- **Phase 1 (현재)**: Flask 웹앱, Claude API + HuggingFace, 일일 3회 제한
- **Phase 2**: 모바일 앱, AES-256 암호화, 광고 기반 추가 크레딧
- **Phase 3**: 그림체 변경 (LoRA 교체), 프리미엄 구독

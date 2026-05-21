import sqlite3
import uuid
from datetime import date, datetime
from config import Config


def get_db():
    """매 요청마다 DB 연결 반환 (thread-safe)"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row   # dict처럼 컬럼명으로 접근 가능
    conn.execute("PRAGMA journal_mode=WAL")   # 동시 읽기 성능 향상
    return conn


def init_db():
    """
    앱 최초 실행 시 테이블 생성.
    
    ⚠️  프라이버시 설계 원칙:
        - diary 테이블에 content(일기 원문) 컬럼 없음 — 원문은 서버에 저장하지 않음
        - image_prompt 만 저장 (원문에서 추출된 키워드 수준)
        - 사용자 식별은 anonymous_uuid 로만 수행
    """
    conn = get_db()
    cursor = conn.cursor()

    # ── 사용자 (익명 UUID 기반) ─────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,          -- UUID v4
            created_at    TEXT NOT NULL,
            last_seen_at  TEXT NOT NULL
        )
    """)

    # ── 일기 (원문 미저장) ─────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diaries (
            id            TEXT PRIMARY KEY,          -- UUID v4
            user_id       TEXT NOT NULL,
            image_prompt  TEXT,                      -- 원문 아님! 변환된 프롬프트만
            image_path    TEXT,                      -- 로컬 이미지 경로
            mood          TEXT,                      -- happy / sad / calm / angry / excited
            diary_date    TEXT NOT NULL,             -- YYYY-MM-DD (사용자 입력 날짜)
            created_at    TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ── 일일 생성 횟수 추적 ────────────────────────────
    # Phase 2에서 Redis로 교체 예정. 지금은 SQLite로 충분.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_limits (
            user_id       TEXT NOT NULL,
            limit_date    TEXT NOT NULL,             -- YYYY-MM-DD
            count         INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, limit_date),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ DB initialized")


# ── 사용자 헬퍼 ───────────────────────────────────────────

def get_or_create_user(user_uuid: str) -> dict:
    """UUID로 사용자 조회, 없으면 생성"""
    conn = get_db()
    now = datetime.utcnow().isoformat()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_uuid,)
    ).fetchone()

    if not user:
        conn.execute(
            "INSERT INTO users (id, created_at, last_seen_at) VALUES (?, ?, ?)",
            (user_uuid, now, now)
        )
        conn.commit()
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_uuid,)
        ).fetchone()
    else:
        conn.execute(
            "UPDATE users SET last_seen_at = ? WHERE id = ?", (now, user_uuid)
        )
        conn.commit()

    conn.close()
    return dict(user)


# ── 일일 제한 헬퍼 ────────────────────────────────────────

def get_today_count(user_id: str) -> int:
    """오늘 사용자의 이미지 생성 횟수 반환"""
    today = date.today().isoformat()
    conn = get_db()
    row = conn.execute(
        "SELECT count FROM daily_limits WHERE user_id = ? AND limit_date = ?",
        (user_id, today)
    ).fetchone()
    conn.close()
    return row["count"] if row else 0


def increment_today_count(user_id: str) -> int:
    """오늘 생성 횟수 +1, 증가 후 현재 카운트 반환"""
    today = date.today().isoformat()
    conn = get_db()
    conn.execute("""
        INSERT INTO daily_limits (user_id, limit_date, count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, limit_date)
        DO UPDATE SET count = count + 1
    """, (user_id, today))
    conn.commit()
    count = conn.execute(
        "SELECT count FROM daily_limits WHERE user_id = ? AND limit_date = ?",
        (user_id, today)
    ).fetchone()["count"]
    conn.close()
    return count


def is_limit_exceeded(user_id: str) -> bool:
    """오늘 제한 초과 여부"""
    return get_today_count(user_id) >= Config.DAILY_LIMIT


# ── 일기 헬퍼 ─────────────────────────────────────────────

def save_diary(user_id: str, image_prompt: str, image_path: str,
               mood: str, diary_date: str) -> str:
    """일기 저장 (원문 미포함). diary_id 반환"""
    diary_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_db()
    conn.execute("""
        INSERT INTO diaries (id, user_id, image_prompt, image_path, mood, diary_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (diary_id, user_id, image_prompt, image_path, mood, diary_date, now))
    conn.commit()
    conn.close()
    return diary_id


def get_diary(diary_id: str, user_id: str) -> dict | None:
    """특정 일기 조회 (본인 것만)"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM diaries WHERE id = ? AND user_id = ?",
        (diary_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_diary_list(user_id: str, limit: int = 20, offset: int = 0) -> list:
    """사용자 일기 목록 (최신순)"""
    conn = get_db()
    rows = conn.execute("""
        SELECT id, mood, diary_date, image_path, created_at
        FROM diaries
        WHERE user_id = ?
        ORDER BY diary_date DESC
        LIMIT ? OFFSET ?
    """, (user_id, limit, offset)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_diary(diary_id: str, user_id: str) -> bool:
    """일기 완전 삭제 (soft delete 없음). 성공 여부 반환"""
    conn = get_db()
    result = conn.execute(
        "DELETE FROM diaries WHERE id = ? AND user_id = ?",
        (diary_id, user_id)
    )
    conn.commit()
    conn.close()
    return result.rowcount > 0


def delete_all_user_data(user_id: str):
    """
    계정 탈퇴: 사용자 관련 모든 데이터 완전 삭제 (hard delete)
    GDPR / PIPA 잊혀질 권리 대응
    """
    conn = get_db()
    conn.execute("DELETE FROM diaries      WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM daily_limits WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users        WHERE id = ?",      (user_id,))
    conn.commit()
    conn.close()

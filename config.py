import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Flask ──────────────────────────────────────────
    SECRET_KEY         = os.getenv("SECRET_KEY", "dev-secret-change-me")
    FLASK_ENV          = os.getenv("FLASK_ENV", "production")

    # ── API Keys ───────────────────────────────────────
    ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY")
    HF_API_KEY         = os.getenv("HF_API_KEY")
    HF_MODEL_ID        = os.getenv("HF_MODEL_ID", "alvdansen/littletinies")

    # ── 이미지 생성 제한 ────────────────────────────────
    DAILY_LIMIT        = int(os.getenv("DAILY_LIMIT", 3))

    # ── 저장 경로 ──────────────────────────────────────
    DATABASE_PATH      = os.getenv("DATABASE_PATH", "./doodle_diary.db")
    IMAGE_SAVE_PATH    = os.getenv("IMAGE_SAVE_PATH", "./static/images/generated")

    # ── 쿠키 설정 ──────────────────────────────────────
    SESSION_COOKIE_HTTPONLY  = True   # JS에서 쿠키 접근 차단
    SESSION_COOKIE_SAMESITE  = "Lax"
    SESSION_COOKIE_SECURE    = FLASK_ENV == "production"  # HTTPS 환경에서만 Secure

    # ── HuggingFace API URL ────────────────────────────
    @staticmethod
    def hf_api_url():
        model_id = os.getenv("HF_MODEL_ID", "alvdansen/littletinies")
        return f"https://api-inference.huggingface.co/models/{model_id}"

import os
from flask import Blueprint, request, jsonify, session, g
from database.models import (
    is_limit_exceeded, increment_today_count, get_today_count,
    save_diary, get_diary, get_diary_list, delete_diary
)
from services.ai_service import process_diary
from config import Config

diary_bp = Blueprint("diary", __name__, url_prefix="/api/diary")


# ── POST /api/diary ───────────────────────────────────────
# 일기 저장 + AI 이미지 생성
@diary_bp.route("", methods=["POST"])
def create_diary():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized"}), 401

    # ── 일일 제한 체크 ────────────────────────────────────
    if is_limit_exceeded(user_id):
        today_count = get_today_count(user_id)
        return jsonify({
            "error":       "daily_limit_exceeded",
            "message":     "오늘의 그림일기를 다 썼어요 🎨 내일 다시 만나요!",
            "today_count": today_count,
            "daily_limit": Config.DAILY_LIMIT,
        }), 429

    # ── 입력 검증 ──────────────────────────────────────────
    data = request.get_json(silent=True) or {}

    diary_content = data.get("content", "").strip()
    mood          = data.get("mood", "neutral")
    diary_date    = data.get("date", "")

    if not diary_content:
        return jsonify({"error": "일기 내용을 입력해주세요."}), 400
    if len(diary_content) > 2000:
        return jsonify({"error": "일기는 2000자 이내로 작성해주세요."}), 400
    if mood not in ("happy", "sad", "calm", "angry", "excited", "neutral"):
        mood = "neutral"

    # ── AI 파이프라인 (일기 원문 → 프롬프트 → 이미지) ───────
    # ⚠️  diary_content 는 process_diary() 내부에서만 사용,
    #     반환값에 포함되지 않으므로 이 시점 이후 원문 소멸
    try:
        result = process_diary(diary_content)
    except Exception as e:
        # 에러 로그에 diary_content 절대 포함 금지
        # print(f"[ERROR] AI pipeline failed for user {user_id[:8]}... : {type(e).__name__}")
        import traceback
        traceback.print_exc()   # 풀 스택트레이스 출력!
        print(f"[ERROR] {type(e).__name__}: {str(e)}")
        return jsonify({"error": "이미지 생성 중 오류가 발생했어요. 잠시 후 다시 시도해주세요."}), 500

    # ── DB 저장 (원문 미포함) ──────────────────────────────
    diary_id = save_diary(
        user_id      = user_id,
        image_prompt = result["image_prompt"],
        image_path   = result["image_path"],
        mood         = mood,
        diary_date   = diary_date,
    )

    # ── 제한 카운트 증가 ──────────────────────────────────
    today_count = increment_today_count(user_id)
    remaining   = max(0, Config.DAILY_LIMIT - today_count)

    return jsonify({
        "diary_id":    diary_id,
        "image_path":  result["image_path"],
        "mood":        mood,
        "today_count": today_count,
        "remaining":   remaining,
        "daily_limit": Config.DAILY_LIMIT,
    }), 201


# ── GET /api/diary/list ───────────────────────────────────
@diary_bp.route("/list", methods=["GET"])
def list_diaries():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized"}), 401

    limit  = min(int(request.args.get("limit",  20)), 50)
    offset = max(int(request.args.get("offset",  0)),  0)

    diaries = get_diary_list(user_id, limit=limit, offset=offset)
    return jsonify({
        "diaries":     diaries,
        "today_count": get_today_count(user_id),
        "remaining":   max(0, Config.DAILY_LIMIT - get_today_count(user_id)),
        "daily_limit": Config.DAILY_LIMIT,
    })


# ── GET /api/diary/<diary_id> ─────────────────────────────
@diary_bp.route("/<diary_id>", methods=["GET"])
def get_single_diary(diary_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized"}), 401

    diary = get_diary(diary_id, user_id)
    if not diary:
        return jsonify({"error": "not_found"}), 404

    return jsonify(diary)


# ── DELETE /api/diary/<diary_id> ──────────────────────────
@diary_bp.route("/<diary_id>", methods=["DELETE"])
def delete_single_diary(diary_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized"}), 401

    diary = get_diary(diary_id, user_id)
    if not diary:
        return jsonify({"error": "not_found"}), 404

    # 이미지 파일 삭제
    image_path = diary.get("image_path", "")
    if image_path:
        local_path = "." + image_path   # /static/... → ./static/...
        if os.path.exists(local_path):
            os.remove(local_path)

    delete_diary(diary_id, user_id)
    return jsonify({"message": "삭제되었습니다."}), 200

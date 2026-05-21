import json
import uuid
from flask import Blueprint, session, jsonify, request
from database.models import (
    get_or_create_user, get_diary_list,
    delete_all_user_data, get_today_count
)
from config import Config

user_bp = Blueprint("user", __name__, url_prefix="/api/user")


# ── GET /api/user/init ────────────────────────────────────
# 앱 최초 진입 시 익명 UUID 발급 또는 기존 세션 확인
@user_bp.route("/init", methods=["POST"])
def init_user():
    """
    익명 사용자 초기화.
    세션에 UUID가 없으면 새로 발급합니다.
    이메일, 전화번호 등 개인정보 수집 없음.
    """
    user_id = session.get("user_id")

    if not user_id:
        user_id = str(uuid.uuid4())
        session["user_id"] = user_id
        session.permanent = True

    user = get_or_create_user(user_id)

    return jsonify({
        "user_id":     user_id[:8] + "...",   # 클라이언트에 전체 UUID 노출 최소화
        "today_count": get_today_count(user_id),
        "remaining":   max(0, Config.DAILY_LIMIT - get_today_count(user_id)),
        "daily_limit": Config.DAILY_LIMIT,
    })


# ── GET /api/user/status ──────────────────────────────────
@user_bp.route("/status", methods=["GET"])
def user_status():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False}), 200

    today_count = get_today_count(user_id)
    return jsonify({
        "authenticated": True,
        "today_count":   today_count,
        "remaining":     max(0, Config.DAILY_LIMIT - today_count),
        "daily_limit":   Config.DAILY_LIMIT,
    })


# ── GET /api/user/export ──────────────────────────────────
# PIPA / GDPR 데이터 이동권 대응
@user_bp.route("/export", methods=["GET"])
def export_data():
    """
    사용자 데이터 전체 내보내기.
    일기 원문은 서버에 없으므로 메타데이터 + 이미지 경로만 포함됩니다.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized"}), 401

    diaries = get_diary_list(user_id, limit=1000, offset=0)

    export_data = {
        "export_note": (
            "Doodle-Diary는 일기 원문을 서버에 저장하지 않습니다. "
            "이 파일에는 생성된 이미지 메타데이터만 포함됩니다."
        ),
        "diaries": diaries,
    }

    response = jsonify(export_data)
    response.headers["Content-Disposition"] = "attachment; filename=doodle-diary-export.json"
    return response


# ── DELETE /api/user ──────────────────────────────────────
# PIPA / GDPR 잊혀질 권리 (Right to Erasure) 대응
@user_bp.route("", methods=["DELETE"])
def delete_account():
    """
    계정 + 모든 데이터 완전 삭제 (hard delete).
    Soft delete 없음 — 즉시 영구 삭제.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized"}), 401

    delete_all_user_data(user_id)
    session.clear()

    return jsonify({
        "message": "모든 데이터가 완전히 삭제되었습니다. 이용해주셔서 감사합니다."
    }), 200

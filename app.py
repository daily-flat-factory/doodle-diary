import os
from datetime import timedelta
from flask import Flask, render_template, session
from flask_cors import CORS
from config import Config

from database.models import init_db
from routes.diary import diary_bp
from routes.user import user_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.permanent_session_lifetime = timedelta(days=365)

    # CORS 개발 환경에서만 허용(배포 X)
    # TODO : CORS - 다른 사이트(예: 클라이언트 애플리케이션)가 서버에 접근하는 것을 검사하는 보안 규칙
    # supports_credentials=True : CORS 요청에 자격 증명(쿠키, 인증 헤더 등)을 포함할 수 있도록 허용
    if Config.FLASK_ENV == "development":
        CORS(app, supports_credentials=True)

    # Blueprint 등록
    # TODO : Blueprint - Flask에서 애플리케이션을 모듈화하는 방법, 라우트와 관련된 코드를 별도의 파일로 분리하여 관리
    app.register_blueprint(diary_bp)
    app.register_blueprint(user_bp)

    # DB 초기화
    with app.app_context():
        os.makedirs(Config.IMAGE_SAVE_PATH, exist_ok=True)
        init_db()
    
    # 페이지 라우트
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/diary/<diary_id>')
    def diary_detail(diary_id):
        return render_template('diary.html', diary_id=diary_id)
    
    # 에러 핸들러
    @app.errorhandler(404)
    def not_found(e):
        return render_template('index.html'), 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return {"error": "too_many_requests", "message": str(e)}, 429
    
    @app.errorhandler(500)
    def server_error(e):
        # 에러 메시지에 민감 정보 노출 금지
        print(f"[500 ERROR] {type(e).__name__}: {str(e)[:100]}")
        return {"error": "server_error", "message": "서버 오류가 발생했어요."}, 500
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=Config.FLASK_ENV == "development", port=5000)
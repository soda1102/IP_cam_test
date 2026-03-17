from dotenv import load_dotenv
load_dotenv()

# 기본 모듈
import os

# 라이브러리
from flask_caching import Cache
from flask import Flask, render_template

# 공통 모듈
from src.common import init_app

# 서비스 모듈
# FIXME : 반드시 이 부분만 수정해주세요.
#  여기에 코드를 넣기 전에 항상 src/service/__init__.py에 해당 Blueprint를 추가했는지 검토해주세요.
from src.service import (
    auth_bp,
    mypage_bp,
    introduce_bp,
    board_bp,
    admin_bp,
    # 여기 아래에 계속 추가하기
)
# FIXME end

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')

# Cache 설정
cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app)
init_app(app)

# 메인 페이지 라우트
@app.route('/')
def index():
    return render_template('main.html')

# Blueprint 등록
# FIXME : app.py에 등록할 때 항상 url_prefix를 붙여서 넣기, 반드시 이 부분만 수정해주세요
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(mypage_bp, url_prefix='/mypage')
app.register_blueprint(introduce_bp, url_prefix='/introduce')
app.register_blueprint(board_bp, url_prefix='/board')
app.register_blueprint(admin_bp, url_prefix='/admin')
# FIXME end


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_APP_PORT', 5000)),
        debug=bool(os.getenv('FLASK_DEBUG', 1)),
    )
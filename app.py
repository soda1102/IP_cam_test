from dotenv import load_dotenv

from LMS.service.BoardService import board_bp
load_dotenv()

# 기본 모듈
import os

# 라이브러리
from flask_caching import Cache
from flask import Flask, render_template, Blueprint, g

# 공통 모듈
from LMS.common import init_app

# 서비스 모듈
from LMS.service.MemberService import member_bp
from LMS.service.AdminService import AdminService
from LMS.service.introduce import introduce_bp



app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.register_blueprint(board_bp, url_prefix='/board')

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
# TODO : app.py에 등록할 때 항상 url_prefix를 붙여서 넣기
app.register_blueprint(member_bp, url_prefix='/member')
app.register_blueprint(introduce_bp, url_prefix='/introduce')
# app.register_blueprint(admin_bp, url_prefix='/admin')


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# 서버 실행부
# 블루프린트 app.py 안에서 바로 정의
# admin_bp = Blueprint('admin', __name__)
#
# @admin_bp.route('/')
# def dashboard():
#     members = AdminService.get_members()
#     new_today = AdminService.get_today_new_members(members)
#     boards = AdminService.get_boards()
#     return render_template('admin.html',members=members, new_today=new_today, boards=boards)




if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_APP_PORT', 5000)),
        debug=bool(os.getenv('FLASK_DEBUG', 1)),
    )
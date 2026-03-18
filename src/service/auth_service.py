from flask import (
    Blueprint,
    request, session, flash,
    render_template, redirect, url_for
)
from datetime import date

from src.common import (
    fetch_query, execute_query,
    log_system
)

# auth 서비스에는 로그인, 회원가입, 로그아웃 기능을 넣는다.

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')

    uid = request.form.get('uid')
    upw = request.form.get('upw')

    # [개선] SELECT 로직이 한 줄로 줄어듦
    user = fetch_query("SELECT * FROM members WHERE uid = %s", (uid,), one=True)

    if not bool(user['active']):
        return "<script>alert('계정이 삭제되었습니다.');history.back();</script>"

    if user and user['password'] == upw:
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_role'] = user['role']
        session['user_profile'] = user['profile_img']
        log_system('ACCESS', 'INFO', 'LOGIN_SUCCESS', f'로그인 UID : {uid}')
        return redirect(url_for('index'))
    else:
        log_system('SECURITY', 'WARNING', 'LOGIN_FAIL', f'로그인 시도한 UID: {uid}')
        return "<script>alert('로그인 실패');history.back();</script>"

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash('로그아웃 되었습니다.')
    return redirect(url_for('auth.login'))

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        today_year = date.today().year
        return render_template('auth/signup.html', year_now=today_year, name = session['name'], role = session['role'])

    uid = request.form.get('uid')
    password = request.form.get('password')
    name = request.form.get('name')
    # 회원가입 시 생년월일 추가(만 14세 이상만 가입 가능)
    # [추가] 따로 입력받은 년, 월, 일을 가져옴
    b_year = request.form.get('birth_year')
    b_month = request.form.get('birth_month')
    b_day = request.form.get('birth_day')

    try:
        # [추가] 만 나이 계산 및 14세 체크
        if b_year and b_month and b_day:
            birth_date = date(int(b_year), int(b_month), int(b_day))
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

            if age < 14:
                return '<script>alert("만 14세 이상만 가입 가능합니다.");history.back();</script>'

            # DB에 저장할 날짜 형식 (YYYY-MM-DD)
            birthdate_str = birth_date.strftime('%Y-%m-%d')
        else:
            return '<script>alert("생년월일을 모두 입력해주세요.");history.back();</script>'

        # 1. 중복 체크 (SELECT)
        exist = fetch_query("SELECT id FROM members WHERE uid = %s", (uid,), one=True)

        if exist:
            return '<script>alert("이미 존재하는 아이디입니다.");history.back();</script>'

        # 2. 회원 가입 (INSERT - DML)
        # [개선] 복잡한 conn, cursor, commit 코드가 사라지고 함수 호출만 남음
        hashed_pw = password
        execute_query("INSERT INTO members (uid, password, name, birthdate) VALUES (%s, %s, %s, %s)", (uid, hashed_pw, name, birthdate_str))

        return '<script>alert("가입 완료!"); location.href="/auth/login";</script>'

    except Exception as e:
        print(f"가입 에러: {e}")
        return '가입 중 오류 발생'
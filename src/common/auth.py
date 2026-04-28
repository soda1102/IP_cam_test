from functools import wraps
from flask import session, request, redirect, url_for, flash, abort

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # [수정] 로그인 후 돌아올 주소(next)를 쿼리 스트링으로 전달
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_role') not in ('admin','manager'):
            flash('관리자, 매니저만 이용 가능한 서비스입니다.')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

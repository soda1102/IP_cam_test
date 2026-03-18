from functools import wraps
from flask import session, redirect, url_for, flash, abort

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('로그인이 필요한 서비스입니다.')
            return redirect(url_for('auth.login')) # bp이름.함수명
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_role') != 'admin':
            flash('관리자만 이용 가능한 서비스입니다.')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

from flask import request, session
from src.common.db import execute_query
import traceback

def log_system(category, level, action, content=None):
    """
    모든 종류의 로그를 통합 저장하는 함수
    사용법: log_system('SECURITY', 'WARNING', 'LOGIN_FAIL', '비밀번호 5회 오류')
    """
    # 1. 사용자 정보 (로그인 안 했으면 None)
    member_id = session.get('user_id')

    # 2. IP 주소 (Vercel 환경 고려)
    if request.headers.getlist("X-Forwarded-For"):
        ip_address = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip_address = request.remote_addr

    # 3. DB 저장
    sql = """
        INSERT INTO system_logs (category, level, member_id, action, content, ip_address)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        execute_query(sql, (category, level, member_id, action, content, ip_address))
    except Exception as e:
        # 로그 저장이 실패하면 콘솔에라도 남겨야 함 (Vercel Runtime Log)
        print(f"💥 로그 저장 실패: {e}")
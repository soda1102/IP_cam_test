from flask import (
    Blueprint,
    request, session, flash,
    render_template, redirect, url_for
)

from src.common import (
    fetch_query, execute_query,
    log_system,
    login_required
)

mypage_bp = Blueprint('mypage', __name__)

@mypage_bp.route('/')
@login_required
def mypage():
    # 1. 유저 정보 가져오기 (이때 profile_img 컬럼 데이터가 포함되어야 합니다)
    user = fetch_query("SELECT * FROM members WHERE id = %s", (session['user_id'],), one=True)
    # 2. 활동 요약 정보
    sql_count = """
        SELECT 
            COUNT(*) as total_cnt,
            COUNT(CASE WHEN (SELECT COUNT(*) FROM reports WHERE board_id = b.id) >= 1 THEN 1 END) as reported_cnt
        FROM boards b
        WHERE b.member_id = %s AND b.active = 1
    """
    count_data = fetch_query(sql_count, (session['user_id'],), one=True)

    board_count = count_data['total_cnt'] if count_data else 0
    reported_count = count_data['reported_cnt'] if count_data else 0

    # 3. render_template 시 user 객체를 통째로 넘기면 user.profile_img를 HTML에서 쓸 수 있습니다.
    return render_template('mypage/mypage.html',
                           user=user,
                           board_count=board_count,
                           reported_count=reported_count)

@mypage_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def member_edit():
    if request.method == 'GET':
        user = fetch_query("SELECT * FROM members WHERE id = %s", (session['user_id'],), one=True)
        return render_template('mypage/edit.html', user=user)

    # POST 요청 (정보 수정)
    new_name = request.form.get('name')
    new_pw = request.form.get('password')

    try:
        if new_pw:
            hashed_pw = new_pw
            # [개선] UPDATE 실행
            execute_query(
                "UPDATE members SET name = %s, password = %s WHERE id = %s",
                (new_name, hashed_pw, session['user_id'])
            )

        else:
            execute_query(
                "UPDATE members SET name = %s WHERE id = %s",
                (new_name, session['user_id'])
            )

        session['user_name'] = new_name
        return "<script>alert('수정 완료');location.href='/mypage';</script>"

    except Exception as e:
        print(f"수정 에러: {e}")
        return "수정 중 오류 발생"

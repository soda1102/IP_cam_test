from flask import (
    Blueprint,
    request, session, flash,
    render_template, redirect, url_for,
)

from src.common import (
    fetch_query, execute_query,
    log_system,
    login_required, upload_file, Session
)

from src.common import fetch_query, execute_query, log_system, login_required
# storage.py가 src 폴더 안에 있다면 아래와 같이 import
from src.common.storage import upload_file
from src.domain import Member
import math

mypage_bp = Blueprint('mypage', __name__)

@mypage_bp.route('/')
@login_required
def mypage_info():
    # 1. 세션에서 로그인한 사용자의 PK(id)를 가져옴
    user_pk = session.get('user_id')

    if not user_pk:
        return redirect(url_for('auth.login'))

    # 2. DB에서 해당 사용자의 최신 정보 조회 (created_at 포함)
    row = fetch_query("SELECT * FROM members WHERE id = %s", (user_pk,), one=True)

    # 3. Member 객체로 변환 (가입일자가 포함된 버전)
    user_obj = Member.from_db(row)

    # 4. 템플릿 렌더링 (user 객체 하나만 넘겨도 객체 안에 가입일이 들어있음)
    return render_template('mypage/info.html', user=user_obj)

# 마이페이지
@mypage_bp.route('/main')
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
    return render_template('mypage/info.html',
                           user=user,
                           board_count=board_count,
                           reported_count=reported_count)


# 회원 정보 수정
@mypage_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def member_edit():
    if request.method == 'GET':
        user = fetch_query("SELECT * FROM members WHERE id = %s", (session['user_id'],), one=True)
        return render_template('mypage/edit.html', user=user)

    # 1. 폼 데이터 가져오기
    new_name = request.form.get('name')
    new_nickname = request.form.get('nickname')
    new_pw = request.form.get('password')
    b_year = request.form.get('birth_year')
    b_month = request.form.get('birth_month')
    b_day = request.form.get('birth_day')

    try:
        set_clauses = []
        params = []

        if new_name:
            set_clauses.append("name = %s")
            params.append(new_name)

        if new_nickname:
            set_clauses.append("nickname = %s")
            params.append(new_nickname)

        if new_pw:
            set_clauses.append("password = %s")
            params.append(new_pw)

        # 2. 생년월일 처리 로직
        if b_year and b_month and b_day:

            full_birthday = f"{b_year}-{b_month.zfill(2)}-{b_day.zfill(2)}"
            set_clauses.append("birthdate = %s")
            params.append(full_birthday)

        if set_clauses:

            params.append(session['user_id'])
            sql = f"UPDATE members SET {', '.join(set_clauses)} WHERE id = %s"
            execute_query(sql, tuple(params))

        # 3. 세션 갱신 (선택사항)
        session['user_name'] = new_name
        session['user_nickname'] = new_nickname

        return "<script>alert('수정 완료');location.href='/mypage';</script>"

    except Exception as e:
        print(f"수정 에러: {e}")
        return "<script>alert('수정 중 오류 발생');history.back();</script>"

# 프로필
@mypage_bp.route('/profile/upload', methods=['POST'])
@login_required
def profile_upload():
    user_id = session.get('user_id')

    # HTML의 <input name="profile_img">와 일치해야 함
    if 'profile_img' not in request.files:
        return "<script>alert('파일이 전송되지 않았습니다.');history.back();</script>"

    file = request.files['profile_img']
    if file.filename == '':
        return "<script>alert('선택된 사진이 없습니다.');history.back();</script>"

    try:
        # storage.py의 함수를 이용해 Cloudinary 업로드
        file_url = upload_file(file, folder=f"user_profiles/{user_id}")

        if file_url:
            # 1. DB 업데이트
            sql = "UPDATE members SET profile_img = %s WHERE id = %s"
            execute_query(sql, (file_url, user_id))

            # 2. [핵심] 세션 정보 즉시 갱신
            # 템플릿이나 헤더에서 session['user_profile'] 등을 사용한다면 여기서 바꿔줘야 합니다.
            session['user_profile'] = file_url

            # 3. [핵심] 알림 후 마이페이지로 이동 (경로 끝에 / 확인)
            return "<script>alert('프로필 사진이 변경되었습니다.'); location.href='/mypage/';</script>"

    except Exception as e:
        return f"<script>alert('오류 발생: {str(e)}');history.back();</script>"

# 프로필 삭제
@mypage_bp.route('/profile/delete', methods=['POST'])
@login_required
def profile_delete():
    user_id = session.get('user_id')

    try:
        # DB의 profile_img를 NULL(또는 빈 문자열)로 업데이트
        sql = "UPDATE members SET profile_img = NULL WHERE id = %s"
        execute_query(sql, (user_id,))

        # 세션 정보도 초기화
        session['user_profile'] = None

        return "<script>alert('프로필 사진이 삭제되었습니다.'); location.href='/mypage/';</script>"
    except Exception as e:
        return f"<script>alert('삭제 중 오류 발생: {str(e)}'); history.back();</script>"

# 나의 활동 메뉴
@mypage_bp.route('/my_activity/')
@login_required
def my_activity():

    # 1. 로그인 확인 및 사용자 ID 가져오기
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    # 2. 페이지네이션 설정 (현재 페이지 번호 받기)
    page = request.args.get('page', 1, type=int)
    per_page = 10  # 한 페이지에 보여줄 글 개수
    offset = (page - 1) * per_page

    # 3. 데이터베이스 조회 (작성 게시물 개수 파악)
    total_row = fetch_query("SELECT COUNT(*) as cnt FROM boards WHERE member_id = %s AND active = 1", (user_id,), one=True)
    total_count = total_row['cnt']
    total_pages = math.ceil(total_count / per_page)

    # 4. 실제 데이터 가져오기 (LIMIT와 OFFSET으로 페이지 자르기)
    my_posts = fetch_query("""
        SELECT * FROM boards 
        WHERE member_id = %s AND active = 1 
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, (user_id, per_page, offset))

    # 좋아요와 스크랩 데이터
    my_likes = fetch_query("""
        SELECT b.*, m.name as writer_name 
        FROM board_likes bl
        JOIN boards b ON bl.board_id = b.id
        JOIN members m ON b.member_id = m.id
        WHERE bl.member_id = %s
    """, (user_id,))

    my_scraps = fetch_query("""
        SELECT b.*, bs.created_at as scrap_date 
        FROM board_scrap bs
        JOIN boards b ON bs.board_id = b.id
        WHERE bs.member_id = %s
    """, (user_id,))

    # 내가 작성한 댓글 가져오기
    my_comments = fetch_query("""
            SELECT c.*, b.title as board_title 
            FROM board_comments c
            JOIN boards b ON c.board_id = b.id
            WHERE c.member_id = %s
            ORDER BY c.created_at DESC
        """, (user_id,))

    # 휴지통 데이터 조회 (삭제 후 30일 계산 로직 포함)
    my_trash = fetch_query("""
        SELECT *, DATEDIFF(DATE_ADD(deleted_at, INTERVAL 30 DAY), NOW()) as remaining_days
        FROM boards 
        WHERE member_id = %s AND active = 0 AND deleted_at IS NOT NULL
        ORDER BY deleted_at DESC
    """, (user_id,))

    # 5. HTML이 기다리고 있는 pagination 객체 만들기
    pagination_obj = {
        'page': page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1,
        'next_num': page + 1
    }

    # 6. 템플릿으로 데이터 넘기기 (my_trash 추가됨)
    return render_template('mypage/my_activity.html',
                           my_posts=my_posts,
                           my_likes=my_likes,
                           my_scraps=my_scraps,
                           my_comments=my_comments,
                           my_trash=my_trash,  # 휴지통 변수 전달
                           pagination=pagination_obj)

# 회원 탈퇴
@mypage_bp.route('/delete_account', methods=['GET', 'POST'])
@login_required
def delete_account():
    user_id = session.get('user_id')

    if not user_id:
        return "<script>alert('로그인이 만료되었습니다.'); location.href='/login';</script>"

    try:
        # 1. DB에서 삭제 대신 active 상태를 0(False)으로 업데이트
        sql = "UPDATE members SET active = 0 WHERE id = %s"
        execute_query(sql, (user_id,))

        # 2. 세션 정보 비우기 (자동 로그아웃)
        session.clear()

        # 3. 알림 후 메인 페이지로 이동
        return """
            <script>
                alert('회원 탈퇴가 완료되었습니다.\\n그동안 이용해 주셔서 감사합니다.'); 
                location.href='/';
            </script>
        """

    except Exception as e:
        return f"<script>alert('탈퇴 처리 중 오류가 발생했습니다: {str(e)}'); history.back();</script>"
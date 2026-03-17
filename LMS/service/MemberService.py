from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, Flask

from datetime import date
from LMS.common import log_system, upload_file, login_required
from LMS.common.db import fetch_query, execute_query
from LMS.common.session import Session
from LMS.domain import Board

# Blueprint 설정
member_bp = Blueprint('member', __name__)

# 로그인
@member_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

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

# 로그아웃
@member_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash('로그아웃 되었습니다.')
    return redirect(url_for('member.login'))

# 회원가입
@member_bp.route('/signup', methods=['GET', 'POST'])
def join():
    if request.method == 'GET':
        today_year = date.today().year
        return render_template('join.html', year_now=today_year)

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

        return '<script>alert("가입 완료!"); location.href="/login";</script>'

    except Exception as e:
        print(f"가입 에러: {e}")
        return '가입 중 오류 발생'

# 회원 정보 수정
@member_bp.route('/member/modify', methods=['GET', 'POST'])
@login_required
def member_edit():
    if request.method == 'GET':
        user = fetch_query("SELECT * FROM members WHERE id = %s", (session['user_id'],), one=True)
        return render_template('member_edit.html', user=user)

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

# 마이페이지
@member_bp.route('/mypage')
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
    return render_template('mypage.html',
                           user=user,
                           board_count=board_count,
                           reported_count=reported_count)


# 마이페이지 - 프로필 사진
@member_bp.route('/profile/upload', methods=['POST'])
@login_required
def profile_upload():
    if 'profile_img' not in request.files:
        return "<script>alert('파일이 없습니다.');history.back();</script>"

    file = request.files['profile_img']

    if file.filename == '':
        return "<script>alert('선택된 파일이 없습니다.');history.back();</script>"

    if file:
        try:
            file_url = upload_file(file, folder="profiles")
            if file_url:
                origin_name = file.filename
                save_name = file_url
                file_path = file_url
                print('file_path :', file_path)
                # [4] DB 업데이트
                sql = "UPDATE members SET profile_img = %s WHERE id = %s"
                execute_query(sql, (file_path, session['user_id']))

                return "<script>alert('프로필 사진이 변경되었습니다.');location.href='/mypage';</script>"
        except Exception as e:
            # 어떤 에러인지 정확히 알기 위해 f-string 사용
            return f"<script>alert('오류 발생: {str(e)}');history.back();</script>"

    return "<script>alert('업로드 실패');history.back();</script>"

# 마이페이지 - 작성한 게시물 조회
@member_bp.route('/board/my', methods=['GET', 'POST'])
@login_required
def my_board_list() :

    if 'user_id' not in session :
        return redirect(url_for('login'))

    conn = Session.get_connection()

    try :
        with conn.cursor() as cursor :

            # board_likes 테이블의 데이터를 참조하여 JOIN 쿼리 작성
            # COUNT(bl.id)를 통해 게시물별 좋아요 개수를 가져옵니다.
            sql = """
                  SELECT 
                      b.*, 
                      m.name as writer_name,
                      COUNT(bl.id) as like_count
                  FROM boards b
                  JOIN members m ON b.member_id = m.id
                  LEFT JOIN board_likes bl ON b.id = bl.board_id
                  WHERE b.member_id = %s
                  GROUP BY b.id, m.name
                  ORDER BY b.id DESC
                  """
            cursor.execute(sql, (session['user_id'],))
            rows = cursor.fetchall()

            boards = []

            for row in rows :
                board = Board.from_db(row)

                # 1. 쿼리 결과에서 가져온 like_count를 객체에 주입 (UndefinedError 방지)
                board.like_count = row.get('like_count', 0)

                # 2. 아직 존재 여부가 불확실한 속성들은 기본값 0으로 설정
                # (이렇게 하면 board_list.html에서 오류가 발생하지 않습니다)
                if not hasattr(board, 'dislike_count') :
                    board.dislike_count = 0

                if not hasattr(board, 'comment_count') :
                    board.comment_count = 0

                boards.append(board)

            # pagination=None을 넘겨주어 템플릿의 페이지네이션 에러를 방지합니다.
            return render_template('board_list.html',
                                   boards=boards,
                                   list_title="내가 작성한 게시물",
                                   pagination=None)

    finally :
        conn.close()

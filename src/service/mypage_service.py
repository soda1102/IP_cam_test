from flask import (
    Blueprint,
    request, session, flash,
    render_template, redirect, url_for
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

# 작성한 게시물 조회
@mypage_bp.route('/board/my')
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

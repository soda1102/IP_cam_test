from math import ceil

from flask import Blueprint, session, request, render_template, url_for, redirect, jsonify
from LMS.common import Session
from LMS.common.db import fetch_query, execute_query
from LMS.domain import Board
from LMS.common.storage import upload_file

board_bp = Blueprint('board_bp', __name__)

# 게시물 작성
@board_bp.route('/write', methods=['GET', 'POST'])
def board_write():
    # 1. 사용자가 '글쓰기' 버튼을 눌러서 들어왔을 때 (화면 보여주기)
    if request.method == 'GET':
        # 로그인 체크
        if 'user_id' not in session:
            # alert 후 이동은 기존 방식 유지 혹은 redirect 사용
            return '<script>alert("로그인 후 이용 가능합니다."); location.href="/login";</script>'

        # 관리자 여부를 템플릿에 전달
        is_admin = (session.get('user_role') == "admin")
        return render_template('board_write.html', is_admin=is_admin)

    # 2. 사용자가 '등록하기' 버튼을 눌러서 데이터를 보냈을 때(DB 저장)
    elif request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        # 세션에 저장된 로그인 유지의 id (member_id)
        member_id = session.get('user_id')

        # 1. 공지사항 고정 여부 확인 (관리자만 가능)
        is_pinned = 0
        if session.get('user_role') == "admin":
            if request.form.get('is_pinned') == 'on':
                is_pinned = 1

        conn = Session.get_connection()

        try:
            with conn.cursor() as cursor:
                # 2. 공지사항(is_pinned=1)인 경우에만 개수 체크
                if is_pinned == 1:
                    count_sql = "SELECT COUNT(*) AS c FROM boards WHERE is_pinned = 1"
                    cursor.execute(count_sql)
                    pinned_count = cursor.fetchone()['c']  # 튜플이나 딕셔너리 형태에 따라 적절히 추출
                    print(pinned_count)

                    if pinned_count >= 10:
                        return "<script>alert('공지사항은 최대 10개까지만 등록 가능합니다.');history.back();</script>"

                # 3. DB 저장 (is_pinned 컬럼 포함)
                sql = "INSERT INTO boards (member_id, title, content, is_pinned) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (member_id, title, content, is_pinned))
                conn.commit()

            return redirect(url_for('board_list'))  # 저장 후 목록으로 이동

        except Exception as e:
            print(f"글쓰기 에러: {e}")
            return "저장 중 에러가 발생했습니다."

        finally:
            conn.close()

# 게시물 목록
@board_bp.route('/list', methods=['GET', 'POST'])
def board_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    # 1. 권한에 따른 WHERE 절 생성
    # 관리자는 삭제된 글(active=0)도 보고, 유저는 정상 글(active=1)만 봄
    if session.get('user_role') == 'admin':
        where_clause = "WHERE 1=1"  # 모든 글 보기
    else:
        where_clause = "WHERE b.active = 1"  # 정상 글만 보기

    # 2. 전체 개수 구하기 (권한 필터 적용)
    count_sql = f"SELECT COUNT(*) as cnt FROM boards b {where_clause}"
    count_res = fetch_query(count_sql, one=True)
    total_count = count_res['cnt'] if count_res else 0
    total_pages = ceil(total_count / per_page)

    # 3. 메인 쿼리 (좋아요, 싫어요, 댓글수 + [추가] 신고수)
    sql = f"""
            SELECT 
                b.*, 
                m.name as writer_name,
                (SELECT COUNT(*) FROM board_likes WHERE board_id = b.id) as like_count,
                (SELECT COUNT(*) FROM board_dislikes WHERE board_id = b.id) as dislike_count,
                (SELECT COUNT(*) FROM board_comments WHERE board_id = b.id) as comment_count,
                (SELECT COUNT(*) FROM reports WHERE board_id = b.id) as report_count
            FROM boards b
            JOIN members m ON b.member_id = m.id
            {where_clause}
            ORDER BY b.is_pinned DESC, b.created_at DESC
            LIMIT {per_page} OFFSET {offset}
        """
    rows = fetch_query(sql)

    boards = []
    for row in rows:
        board = Board.from_db(row)
        board.like_count = row['like_count']
        board.dislike_count = row['dislike_count']
        board.comment_count = row['comment_count']
        board.report_count = row['report_count']  # [추가] 신고 수 주입
        board.is_pinned = row.get('is_pinned', 0)
        boards.append(board)

    pagination = {
        'page': page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1,
        'next_num': page + 1
    }

    return render_template('board_list.html', boards=boards, pagination=pagination)

# 게시물 상세보기
@board_bp.route('/view/<int:board_id>')
def board_view(board_id):
    # 1. 조회수 증가
    try:
        execute_query("UPDATE boards SET visits = visits + 1 WHERE id = %s", (board_id,))
    except Exception as e:
        print(f"조회수 증가 오류: {e}")

        # 2. 게시글 상세 정보 가져오기 (신고 수 서브쿼리 추가)
    sql = """
            SELECT b.*, m.name as writer_name, m.uid as writer_uid, m.profile_img as writer_profile,
                   (SELECT COUNT(*) FROM reports WHERE board_id = b.id) as report_count
            FROM boards b
            JOIN members m ON b.member_id = m.id
            WHERE b.id = %s
        """
    row = fetch_query(sql, (board_id,), one=True)
    if not row:
        return '<script>alert("존재하지 않는 게시글입니다."); history.back();</script>'

    # 🚩 [신규 추가] 신고 5개 이상 차단 로직 (관리자는 통과)
    if row['report_count'] >= 5:
        if session.get('user_role') != 'admin':
            return "<script>alert('신고 접수된 게시글임으로 조회가 불가능합니다.'); history.back();</script>"

    # 3. 좋아요 & 싫어요 정보 조회
    like_count = fetch_query("SELECT COUNT(*) as cnt FROM board_likes WHERE board_id = %s", (board_id,), one=True)['cnt']
    dislike_count = \
        fetch_query("SELECT COUNT(*) as cnt FROM board_dislikes WHERE board_id = %s", (board_id,), one=True)['cnt']

    user_liked = False
    user_disliked = False

    if 'user_id' in session:
        # 이미 세션에 member_id(PK)가 저장되어 있다고 가정 (로그인 시 id를 저장했다면)
        member_pk = session['user_id']

        if fetch_query("SELECT 1 FROM board_likes WHERE board_id = %s AND member_id = %s", (board_id, member_pk),
                       one=True):
            user_liked = True
        if fetch_query("SELECT 1 FROM board_dislikes WHERE board_id = %s AND member_id = %s", (board_id, member_pk),
                       one=True):
            user_disliked = True

    # 4. 댓글 및 대댓글 목록 가져오기 (기존 팀원 코드 유지)
    comment_sql = """
                SELECT c.*, m.name as writer_name, m.uid as writer_uid
                FROM board_comments c
                JOIN members m ON c.member_id = m.id
                WHERE c.board_id = %s
                ORDER BY c.created_at ASC
            """
    all_comments = fetch_query(comment_sql, (board_id,))

    comment_dict = {c['id']: {**c, 'children': []} for c in all_comments}
    root_comments = []

    for c_id, c_data in comment_dict.items():
        parent_id = c_data['parent_id']
        if parent_id and parent_id in comment_dict:
            comment_dict[parent_id]['children'].append(c_data)
        else:
            root_comments.append(c_data)

    # 5. Board 객체 생성 및 데이터 주입
    board = Board.from_db(row)
    board.likes = like_count
    board.dislikes = dislike_count
    board.report_count = row['report_count']  # 혹시 화면에 신고수 띄울까봐 추가
    board.writer_profile = row['writer_profile']

    return render_template('board_view.html',
                           board=board,
                           user_liked=user_liked,
                           user_disliked=user_disliked,
                           comments=root_comments)

# 게시물 수정
@board_bp.route('/edit/<int:board_id>', methods = ['GET', 'POST'])
def board_edit(board_id):
    if request.method == 'GET':
        sql = "SELECT * FROM boards WHERE id = %s"
        row = fetch_query(sql, (board_id,), one=True)
        if not row:
            return '<script>alert("존재하지 않는 게시글입니다."); history.back();</script>'

        if row['member_id'] != session.get('user_id'):
            return "<script>alert('수정 권한이 없습니다.'); history.back();</script>"
        board = Board.from_db(row)
        return render_template('board_edit.html', board=board)
    elif request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        sql = "UPDATE boards SET title = %s, content = %s WHERE id = %s"
        try:
            execute_query(sql, (title, content, board_id))
            return redirect(url_for('board_view', board_id=board_id))
        except Exception as e:
            print(e)
    return None

# 게시물 삭제
@board_bp.route('/delete/<int:board_id>')
def board_delete(board_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # 1. 게시글 존재 여부 및 정보 확인
    board_sql = 'SELECT * FROM boards WHERE id = %s'
    row = fetch_query(board_sql, (board_id,), one=True)

    if not row:
        return '<script>alert("존재하지 않는 게시글입니다."); history.back();</script>'

    try:
        # 2. 관리자(admin)인 경우: DB에서 아예 행을 삭제 (Hard Delete)
        if session.get('user_role') == 'admin':
            sql = "DELETE FROM boards WHERE id = %s"
            execute_query(sql, (board_id,))
            msg = "관리자 권한으로 게시글을 영구 삭제했습니다."

        # 3. 일반 유저인 경우: 본인 글일 때만 active를 0으로 수정 (Soft Delete)
        else:
            # 본인 글인지 먼저 체크
            if row['member_id'] != session.get('user_id'):
                return '<script>alert("삭제할 권한이 없습니다."); history.back();</script>'

            # active 상태만 0으로 바꿔서 목록에서 숨김
            sql = "UPDATE boards SET active = 0 WHERE id = %s AND member_id = %s"
            execute_query(sql, (board_id, session['user_id']))
            msg = "게시글이 삭제되었습니다."

        return f"<script>alert('{msg}'); location.href='/board';</script>"

    except Exception as e:
        print(f'삭제 에러: {e}')
        return "<script>alert('처리 중 오류가 발생했습니다.'); history.back();</script>"

# 좋아요 기능
@board_bp.route('/like/<int:board_id>', methods = ['POST'])
def board_like_toggle(board_id):
    # 1. 로그인 체크
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        # 2. 게시글 존재 확인
        board = fetch_query("SELECT id FROM boards WHERE id = %s", (board_id,), one=True)
        if not board:
            return jsonify({'success': False, 'message': '존재하지 않는 게시글입니다.'}), 404

        # 3. 좋아요 상태 확인
        check_sql = "SELECT id FROM board_likes WHERE board_id = %s AND member_id = %s"
        # session['user_id']가 DB의 members.id(PK, 숫자)와 일치하는지 꼭 확인하세요!
        already_liked = fetch_query(check_sql, (board_id, session['user_id']), one=True)

        if already_liked:
            execute_query("DELETE FROM board_likes WHERE board_id = %s AND member_id = %s",
                          (board_id, session['user_id']))
            is_liked = False
        else:
            execute_query("INSERT INTO board_likes (board_id, member_id) VALUES (%s, %s)",
                          (board_id, session['user_id']))
            is_liked = True

        # 4. 개수 집계
        count_res = fetch_query("SELECT COUNT(*) as cnt FROM board_likes WHERE board_id = %s", (board_id,), one=True)
        like_count = count_res['cnt'] if count_res else 0

        return jsonify({
            'success': True,
            'is_liked': is_liked,
            'like_count': like_count
        })

    except Exception as e:
        # 이 부분이 중요합니다! 에러가 나더라도 클라이언트에게 JSON을 돌려줘야 합니다.
        print(f"Database Error: {e}")
        return jsonify({
            'success': False,
            'message': f"데이터베이스 오류가 발생했습니다: {str(e)}"
        }), 500

# 싫어요 기능
@board_bp.route('/dislike/<int:board_id>', methods = ['POST'])
def board_dislike_toggle(board_id):
    # 1. 로그인 체크
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        # 2. 게시글 존재 확인
        board = fetch_query("SELECT id FROM boards WHERE id = %s", (board_id,), one=True)
        if not board:
            return jsonify({'success': False, 'message': '존재하지 않는 게시글입니다.'}), 404

        # 3. 싫어요 상태 확인
        check_sql = "SELECT id FROM board_dislikes WHERE board_id = %s AND member_id = %s"

        # session['user_id']가 DB의 members.id(PK)와 일치한다고 가정합니다.
        # (만약 session에 문자열 ID가 들어있다면, 여기서 member_id를 조회하는 로직이 추가로 필요할 수 있습니다)
        already_disliked = fetch_query(check_sql, (board_id, session['user_id']), one=True)

        if already_disliked:
            # 이미 싫어요를 눌렀다면 -> 삭제 (취소)
            execute_query("DELETE FROM board_dislikes WHERE board_id = %s AND member_id = %s",
                          (board_id, session['user_id']))
            is_disliked = False
        else:
            # 안 눌렀다면 -> 추가 (싫어요)
            execute_query("INSERT INTO board_dislikes (board_id, member_id) VALUES (%s, %s)",
                          (board_id, session['user_id']))
            is_disliked = True

        # 4. 개수 집계 (board_dislikes 테이블 카운트)
        count_res = fetch_query("SELECT COUNT(*) as cnt FROM board_dislikes WHERE board_id = %s", (board_id,), one=True)
        dislike_count = count_res['cnt'] if count_res else 0

        return jsonify({
            'success': True,
            'is_disliked': is_disliked,
            'dislike_count': dislike_count
        })

    except Exception as e:
        # 에러 발생 시 JSON 응답 반환
        print(f"Database Error: {e}")
        return jsonify({
            'success': False,
            'message': f"데이터베이스 오류가 발생했습니다: {str(e)}"
        }), 500

# 댓글 기능
@board_bp.route('/comment/<int:board_id>', methods = ['POST'])
def add_comment(board_id):
    if 'user_id' not in session:
        return jsonify({'success' : False, 'massage' : '로그인이 필요합니다.'}), 401

    data = request.get_json()
    content = data.get('content')
    parent_id = data.get('parent_id')  # 대댓글일 경우 부모 ID가 넘어옴

    sql = "INSERT INTO board_comments (board_id, member_id, parent_id, content) VALUES (%s, %s, %s, %s)"
    execute_query(sql, (board_id, session['user_id'], parent_id, content))

    return jsonify({'success': True})

# 사진 업로드
@board_bp.route('/upload/image', methods = ['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:

        # 1. Cloudinary 업로드 함수 호출
        # folder='board_editor'로 설정하면 Cloudinary 내 해당 폴더에 정리됨
        image_url = upload_file(file, folder="board_editor")

        if image_url:
            # 2. 성공 시 Cloudinary URL 반환
            return jsonify({'url': image_url})
        else:
            # 3. 실패 시 에러 반환
            return jsonify({'error': 'Cloudinary upload failed'}), 500

    return jsonify({'error': 'Upload failed'}), 500

# 게시물 신고 기능
@board_bp.route('/report/<int:board_id>', methods=['POST'])
def board_report(board_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    data = request.get_json()
    reason = data.get('reason')
    reporter_id = session['user_id']

    try:
        board = fetch_query("SELECT member_id FROM boards WHERE id = %s", (board_id,), one=True)
        if board and board['member_id'] == reporter_id:
            return jsonify({'success': False, 'message': '본인 글은 신고할 수 없습니다.'})
        check_sql = "SELECT id FROM reports WHERE board_id = %s AND reporter_id = %s"
        if fetch_query(check_sql, (board_id, reporter_id), one=True):
            return jsonify({'success': False, 'message': '이미 신고한 글입니다.'})

        insert_sql = "INSERT INTO reports (board_id, reporter_id, reason) VALUES (%s, %s, %s)"
        execute_query(insert_sql, (board_id, reporter_id, reason))
        return jsonify({'success': True, 'message': '신고가 접수되었습니다.'})

    except Exception as e:
        print(f"Database Error: {e}")
        return jsonify({'success': False, 'message': '서버 오류 발생'}), 500
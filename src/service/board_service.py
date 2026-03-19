import os
import bleach
import cloudinary
import cloudinary.uploader

from math import ceil
from flask import Blueprint, session, request, render_template, url_for, redirect, jsonify
from src.common import Session, login_required
from src.common.db import fetch_query, execute_query
from src.domain import Board
from src.common.storage import upload_file
from bleach.css_sanitizer import CSSSanitizer


board_bp = Blueprint('board', __name__)

# 1. Cloudinary 연결 설정 (이미 load_dotenv()가 실행된 상태라면 아래처럼만 적으세요)
cloudinary.config(
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key = os.getenv('CLOUDINARY_API_KEY'),
    api_secret = os.getenv('CLOUDINARY_API_SECRET'),
    secure = True
)

# 게시물 작성
@board_bp.route('/write', methods=['GET', 'POST'])
@login_required
def board_write():
    if request.method == 'GET':
        is_admin = (session.get('user_role') == "admin")
        return render_template('board/write.html', is_admin=is_admin)

    elif request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        member_id = session.get('user_id')

        # 1. Cloudinary 파일 업로드 로직
        file = request.files.get('file')
        file_info = None

        if file and file.filename != '':
            try:
                # 파일 사이즈 추출
                file.seek(0, os.SEEK_END)
                f_size = file.tell()
                file.seek(0)

                upload_result = cloudinary.uploader.upload(file, resource_type="auto")
                file_info = {
                    'origin_name': file.filename,
                    'save_name': upload_result.get('secure_url'),
                    'file_path': upload_result.get('secure_url'),
                    'file_size': f_size
                }
            except Exception as e:
                print(f"Cloudinary Error: {e}")
                return "<script>alert('파일 업로드 중 오류가 발생했습니다.');history.back();</script>"

        # 2. 보안 세정 (Bleach)
        allowed_tags = ['p', 'br', 'b', 'i', 'u', 'em', 'strong', 'span', 'img', 'a', 'ul', 'ol', 'li', 'h1', 'h2',
                        'h3', 'table', 'thead', 'tbody', 'tr', 'th', 'td']
        allowed_attrs = {'a': ['href', 'title', 'target'], 'img': ['src', 'alt', 'style'], '*': ['style', 'class']}
        try:
            my_sanitizer = CSSSanitizer(allowed_css_properties=['color', 'background-color', 'font-size', 'text-align'])
        except:
            my_sanitizer = None
        clean_content = bleach.clean(content, tags=allowed_tags, attributes=allowed_attrs, css_sanitizer=my_sanitizer)

        # 3. DB 저장 (ERD 구조 준수)
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                # [A] posts 테이블에 저장 (attachments가 posts를 참조하므로)
                # ERD 기준 컬럼명: member_id, title, content
                sql_post = "INSERT INTO posts (member_id, title, content) VALUES (%s, %s, %s)"
                cursor.execute(sql_post, (member_id, title, clean_content))

                # 방금 생성된 posts 테이블의 id 가져오기
                new_post_id = cursor.lastrowid

                # [B] attachments 테이블에 저장
                if file_info:
                    # ERD 컬럼명: post_id, origin_name, save_name, file_path, file_size
                    sql_file = """
                        INSERT INTO attachments (post_id, origin_name, save_name, file_path, file_size) 
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql_file, (
                        new_post_id,
                        file_info['origin_name'],
                        file_info['save_name'],
                        file_info['file_path'],
                        file_info['file_size']
                    ))

                conn.commit()
            return redirect(url_for('board.board_list'))

        except Exception as e:
            conn.rollback()
            print(f"DB 저장 에러: {e}")
            return f"저장 중 에러가 발생했습니다: {e}"
        finally:
            conn.close()

# 게시물 목록
@board_bp.route('/list', methods=['GET', 'POST'])
def board_list():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '').strip()
    search_type = request.args.get('search_type', 'title')
    sort = request.args.get('sort', 'latest')
    offset = (page - 1) * per_page

    # ── 검색 조건 ──
    search_query = ""
    query_args = []
    if search:
        if search_type == 'title':
            search_query = "AND title LIKE %s"
            query_args = [f"%{search}%"]
        elif search_type == 'content':
            search_query = "AND content LIKE %s"
            query_args = [f"%{search}%"]
        elif search_type == 'all':
            search_query = "AND (title LIKE %s OR content LIKE %s)"
            query_args = [f"%{search}%", f"%{search}%"]

    # ── 1. 전체 개수 (공지 포함, 페이지네이션용) ──
    count_sql = f"""
        SELECT SUM(cnt) as total FROM (
            SELECT COUNT(*) as cnt FROM boards WHERE 1=1 {search_query}
            UNION ALL
            SELECT COUNT(*) as cnt FROM posts  WHERE 1=1 {search_query}
        ) as combined_count
    """
    count_res = fetch_query(count_sql, tuple(query_args * 2), one=True)
    total_count = int(count_res['total']) if count_res and count_res['total'] else 0
    total_pages = ceil(total_count / per_page) if total_count else 1

    # ── 정렬 기준 ──
    order_map = {
        'latest':  'combined.created_at DESC',
        'oldest':  'combined.created_at ASC',
        'views':   'combined.visits DESC',
    }
    order_clause = order_map.get(sort, 'combined.created_at DESC')

    # ── 2. 목록 조회 ──
    # boards: likes(board_likes), comments(board_comments), attachments 없음
    # posts : likes 없음, attachments(attachments 테이블), comments 없음(posts 전용 댓글 없으므로 0)
    # 공지(is_pinned=1)는 sort 무관하게 항상 상단 고정
    sql = f"""
        SELECT * FROM (
            SELECT
                b.id,
                b.member_id,
                b.title,
                b.content,
                b.created_at,
                b.visits,
                b.is_pinned,
                'board' AS origin_table,
                m.name  AS writer_name,
                m.profile_img AS writer_profile,
                (SELECT COUNT(*) FROM board_likes    WHERE board_id = b.id) AS like_count,
                (SELECT COUNT(*) FROM board_comments WHERE board_id = b.id) AS comment_count,
                0 AS file_count
            FROM boards b
            JOIN members m ON b.member_id = m.id
            WHERE 1=1 {search_query}

            UNION ALL

            SELECT
                p.id,
                p.member_id,
                p.title,
                p.content,
                p.created_at,
                p.view_count AS visits,
                0            AS is_pinned,
                'post'       AS origin_table,
                m.name       AS writer_name,
                m.profile_img AS writer_profile,
                0 AS like_count,
                0 AS comment_count,
                (SELECT COUNT(*) FROM attachments WHERE post_id = p.id) AS file_count
            FROM posts p
            JOIN members m ON p.member_id = m.id
            WHERE 1=1 {search_query}
        ) AS combined
        ORDER BY combined.is_pinned DESC, {order_clause}
        LIMIT %s OFFSET %s
    """
    final_args = tuple(query_args * 2 + [per_page, offset])
    rows = fetch_query(sql, final_args)

    # ── 3. 객체 변환 ──
    boards = []
    for row in rows:
        board = Board.from_db(row)
        board.like_count    = row.get('like_count', 0)
        board.comment_count = row.get('comment_count', 0)
        board.file_count    = row.get('file_count', 0)
        board.writer_name   = row.get('writer_name', '')
        board.writer_profile = row.get('writer_profile')
        board.origin_table  = row.get('origin_table')
        board.visits        = row.get('visits', 0)
        boards.append(board)

    pagination = {
        'page':        page,
        'total_pages': total_pages,
        'has_prev':    page > 1,
        'has_next':    page < total_pages,
    }

    return render_template(
        'board/list.html',
        boards=boards,
        pagination=pagination,
        search=search,
        search_type=search_type,
        sort=sort,
        per_page=per_page,
        total_count=total_count,
    )

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

    return render_template('board/view.html',
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

        return f"<script>alert('{msg}'); location.href='/board/list';</script>"

    except Exception as e:
        print(f'삭제 에러: {e}')
        return "<script>alert('처리 중 오류가 발생했습니다.'); history.back();</script>"

# 좋아요 기능
@board_bp.route('/like/<int:board_id>', methods = ['POST'])
def board_like_toggle(board_id):
    # 1. 로그인 체크
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    user_id = session['user_id']
    try:
        # 게시글 존재 확인
        board = fetch_query("SELECT id FROM boards WHERE id = %s", (board_id,), one=True)
        if not board:
            return jsonify({'success': False, 'message': '존재하지 않는 게시글입니다.'}), 404

        # 좋아요 상태 확인
        already_liked = fetch_query("SELECT id FROM board_likes WHERE board_id = %s AND member_id = %s",
                                    (board_id, user_id), one=True)

        if already_liked:
            execute_query("DELETE FROM board_likes WHERE board_id = %s AND member_id = %s", (board_id, user_id))
            is_liked = False
        else:
            # 🔥 [핵심] 좋아요를 추가하기 전에, 싫어요가 되어 있다면 삭제
            execute_query("DELETE FROM board_dislikes WHERE board_id = %s AND member_id = %s", (board_id, user_id))
            execute_query("INSERT INTO board_likes (board_id, member_id) VALUES (%s, %s)", (board_id, user_id))
            is_liked = True

        # 양쪽 개수 모두 집계 (JS에서 둘 다 업데이트하기 위함)
        l_res = fetch_query("SELECT COUNT(*) as cnt FROM board_likes WHERE board_id = %s", (board_id,), one=True)
        d_res = fetch_query("SELECT COUNT(*) as cnt FROM board_dislikes WHERE board_id = %s", (board_id,), one=True)

        return jsonify({
            'success': True,
            'is_liked': is_liked,
            'like_count': l_res['cnt'] if l_res else 0,
            'dislike_count': d_res['cnt'] if d_res else 0  # 싫어요 개수도 함께 전달
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# 싫어요 기능
@board_bp.route('/dislike/<int:board_id>', methods = ['POST'])
def board_dislike_toggle(board_id):
    # 1. 로그인 체크
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    user_id = session['user_id']
    try:
        board = fetch_query("SELECT id FROM boards WHERE id = %s", (board_id,), one=True)
        if not board:
            return jsonify({'success': False, 'message': '존재하지 않는 게시글입니다.'}), 404

        # 싫어요 상태 확인
        already_disliked = fetch_query("SELECT id FROM board_dislikes WHERE board_id = %s AND member_id = %s",
                                       (board_id, user_id), one=True)

        if already_disliked:
            execute_query("DELETE FROM board_dislikes WHERE board_id = %s AND member_id = %s", (board_id, user_id))
            is_disliked = False
        else:
            # 🔥 [핵심] 싫어요를 추가하기 전에, 좋아요가 되어 있다면 삭제
            execute_query("DELETE FROM board_likes WHERE board_id = %s AND member_id = %s", (board_id, user_id))
            execute_query("INSERT INTO board_dislikes (board_id, member_id) VALUES (%s, %s)", (board_id, user_id))
            is_disliked = True

        # 양쪽 개수 모두 집계
        l_res = fetch_query("SELECT COUNT(*) as cnt FROM board_likes WHERE board_id = %s", (board_id,), one=True)
        d_res = fetch_query("SELECT COUNT(*) as cnt FROM board_dislikes WHERE board_id = %s", (board_id,), one=True)

        return jsonify({
            'success': True,
            'is_disliked': is_disliked,
            'like_count': l_res['cnt'] if l_res else 0,
            'dislike_count': d_res['cnt'] if d_res else 0  # 좋아요 개수도 함께 전달
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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

# 게시물 스크랩 기능 추가
@board_bp.route('/view/scrap/<int:board_id>', methods=['POST'])
def board_scrap_toggle(board_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    user_id = session['user_id']
    try:
        # 이미 스크랩했는지 확인
        check_sql = "SELECT id FROM board_scrap WHERE board_id = %s AND member_id = %s"
        already_scrapped = fetch_query(check_sql, (board_id, user_id), one=True)

        if already_scrapped:
            # 스크랩 취소
            execute_query("DELETE FROM board_scrap WHERE board_id = %s AND member_id = %s", (board_id, user_id))
            is_scrapped = False
            msg = "스크랩이 취소되었습니다."
        else:
            # 스크랩 추가
            execute_query("INSERT INTO board_scrap (board_id, member_id) VALUES (%s, %s)", (board_id, user_id))
            is_scrapped = True
            msg = "게시글을 스크랩하였습니다."

        return jsonify({
            'success': True,
            'is_scrapped': is_scrapped,
            'message': msg
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


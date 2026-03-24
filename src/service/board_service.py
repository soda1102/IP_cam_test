import os
import bleach
import cloudinary
import cloudinary.uploader
import requests
import urllib.parse

from math import ceil
from flask import Blueprint, session, request, render_template, url_for, redirect, jsonify, Response, flash
from src.common import Session, login_required
from src.common.db import fetch_query, execute_query
from src.domain import Board
from src.common.storage import upload_file, get_file_info
from bleach.css_sanitizer import CSSSanitizer


board_bp = Blueprint('board', __name__)

# 1. Cloudinary 연결 설정 (이미 load_dotenv()가 실행된 상태라면 아래처럼만 적으세요)
cloudinary.config(
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key = os.getenv('CLOUDINARY_API_KEY'),
    api_secret = os.getenv('CLOUDINARY_API_SECRET'),
    secure = True
)

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
                sql_post = "INSERT INTO boards (member_id, title, content) VALUES (%s, %s, %s)"
                cursor.execute(sql_post, (member_id, title, clean_content))

                # 방금 생성된 posts 테이블의 id 가져오기
                new_board_id = cursor.lastrowid

                # [B] attachments 테이블에 저장
                if file_info:
                    # ERD 컬럼명: post_id, origin_name, save_name, file_path, file_size
                    sql_file = """
                        INSERT INTO files (board_id, origin_name, save_name, file_path, file_size) 
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql_file, (
                        new_board_id,
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
    # 1. 파라미터 수신
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    show_pinned = request.args.get('show_pinned', 'on')
    search = request.args.get('search', '').strip()
    search_type = request.args.get('search_type', 'title')
    sort = request.args.get('sort', 'latest')
    offset = (page - 1) * per_page

    # 2. WHERE 절 구성
    where_clauses = ["b.active = 1"] if session.get('user_role') != 'admin' else ["1=1"]
    if show_pinned != 'on':
        where_clauses.append("b.is_pinned = 0")

    query_args = []
    if search:
        if search_type == 'title':
            where_clauses.append("b.title LIKE %s")
            query_args.append(f"%{search}%")
        elif search_type == 'content':
            where_clauses.append("b.content LIKE %s")
            query_args.append(f"%{search}%")
        elif search_type == 'all':
            where_clauses.append("(b.title LIKE %s OR b.content LIKE %s)")
            query_args.extend([f"%{search}%", f"%{search}%"])

    where_sentence = " WHERE " + " AND ".join(where_clauses)

    # 3. 정렬 조건
    if sort == 'popular':
        order_sentence = "ORDER BY b.is_pinned DESC, like_count DESC, b.created_at DESC"
    else:
        order_sentence = "ORDER BY b.is_pinned DESC, b.created_at DESC"

    # 4. 페이징 및 데이터 조회
    count_sql = f"SELECT COUNT(*) as cnt FROM boards b {where_sentence}"
    count_res = fetch_query(count_sql, tuple(query_args), True)
    total_count = count_res['cnt'] if count_res else 0
    total_pages = ceil(total_count / per_page)

    sql = f"""
        SELECT b.*, m.name as writer_name, m.nickname as writer_nickname,
               (SELECT COUNT(*) FROM board_likes WHERE board_id = b.id) as like_count,
               (SELECT COUNT(*) FROM board_comments WHERE board_id = b.id) as comment_count,
               (SELECT COUNT(*) FROM files WHERE board_id = b.id) as file_count
        FROM boards b
        JOIN members m ON b.member_id = m.id
        {where_sentence}
        {order_sentence}
        LIMIT %s OFFSET %s
    """
    rows = fetch_query(sql, tuple(query_args + [per_page, offset]))

    boards = []
    for row in rows:
        board = Board.from_db(row)
        board.like_count = row['like_count']
        board.comment_count = row['comment_count']
        board.is_pinned = row.get('is_pinned', 0)
        board.file_count = row.get('file_count', 0)  # 추가
        board.writer_nickname = row.get('writer_nickname')
        boards.append(board)

    pagination = {'page': page, 'total_pages': total_pages, 'has_prev': page > 1, 'has_next': page < total_pages, 'prev_num': page - 1, 'next_num': page + 1}
    return render_template('board/list.html', boards=boards, pagination=pagination, search=search, search_type=search_type, sort=sort, per_page=per_page, show_pinned=show_pinned)

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
            SELECT b.*, m.nickname as writer_nickname, m.name as writer_name, m.uid as writer_uid, m.profile_img as writer_profile,
                   (SELECT COUNT(*) FROM reports WHERE board_id = b.id) as report_count
            FROM boards b
            JOIN members m ON b.member_id = m.id
            WHERE b.id = %s
        """
    row = fetch_query(sql, (board_id,), one=True)
    if not row:
        return '<script>alert("존재하지 않는 게시글입니다."); history.back();</script>'

    print(row)
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
                SELECT c.*, m.name as writer_name, m.nickname as writer_nickname, m.uid as writer_uid
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
    board.writer_nickname = row.get('writer_nickname')
    board.writer_name = row.get('writer_name')
    raw_files = fetch_query("SELECT * FROM files WHERE board_id = %s", (board_id,))
    files = []
    for f in raw_files:
        info = get_file_info(f['file_path'])
        if info:
            info['origin_name'] = f['origin_name']
            info['file_size'] = f['file_size']
            info['file_id'] = f['id']  # ✅ 프록시 라우트용 id 추가
            files.append(info)

    return render_template('board/view.html',
                           board=board,
                           files=files,
                           user_liked=user_liked,
                           user_disliked=user_disliked,
                           comments=root_comments)

# 파일 다운로드
@board_bp.route('/download/<int:file_id>')
def download_file(file_id):
    f = fetch_query("SELECT * FROM files WHERE id = %s", (file_id,), one=True)
    if not f:
        return "파일 없음", 404

    # 외부 URL에서 파일 가져오기
    response = requests.get(f['file_path'])

    # [★ 핵심 수정] 한글 파일명을 URL 인코딩 처리
    # '한글파일.pdf' -> '%ED%95%9C%EA%B8%80...'
    encoded_name = urllib.parse.quote(f["origin_name"])

    return Response(
        response.content,
        headers={
            # filename* 형식을 써야 브라우저에서 한글이 안 깨지고 에러도 안 나!
            'Content-Disposition': f"attachment; filename={encoded_name}; filename*=UTF-8''{encoded_name}",
            'Content-Type': response.headers.get('Content-Type', 'application/octet-stream')
        }
    )


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
        return render_template('board/edit.html', board=board)

    elif request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        sql = "UPDATE boards SET title = %s, content = %s WHERE id = %s"
        try:
            execute_query(sql, (title, content, board_id))
            return redirect(f'/board/view/{board_id}')
        except Exception as e:
            print(e)
    return None


# 게시물 삭제
@board_bp.route('/delete/<int:board_id>')
def board_delete(board_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    board_sql = 'SELECT * FROM boards WHERE id = %s'
    row = fetch_query(board_sql, (board_id,), one=True)

    if not row:
        return '<script>alert("존재하지 않는 게시글입니다."); history.back();</script>'

    try:

        # 1. 관리자인 경우: 즉시 영구 삭제 (선택 사항)
        if session.get('user_role') == 'admin':

            execute_query("DELETE FROM boards WHERE id = %s", (board_id,))
            msg = "관리자 권한으로 영구 삭제되었습니다."

        # 2. 일반 유저: 본인 글인 경우 휴지통으로 이동 (Soft Delete)
        else:

            if row['member_id'] != session.get('user_id'):
                return '<script>alert("삭제할 권한이 없습니다."); history.back();</script>'

            # active=0 (비활성), deleted_at=NOW() (삭제 시간 기록)
            sql = "UPDATE boards SET active = 0, deleted_at = NOW() WHERE id = %s"
            execute_query(sql, (board_id,))
            msg = "게시글이 휴지통으로 이동되었습니다. 30일 후 자동 삭제됩니다."

        return f"<script>alert('{msg}'); location.href='/board/list';</script>"

    except Exception as e:
        print(f'삭제 에러: {e}')
        return "<script>alert('처리 중 오류 발생'); history.back();</script>"

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

# [수정 메서드] - fetch_query로 변경
@board_bp.route('/comment/edit/<int:comment_id>', methods=['POST'])
def edit_comment(comment_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    data = request.get_json()
    new_content = data.get('content')

    # 1. 본인 확인 (fetch_query 사용!)
    check_sql = "SELECT member_id FROM board_comments WHERE id = %s"
    comment = fetch_query(check_sql, (comment_id,), one=True) # 한 개만 가져오기

    if not comment or comment['member_id'] != session['user_id']:
        return jsonify({'success': False, 'message': '수정 권한이 없습니다.'})

    # 2. DB 업데이트 (수정은 execute_query 사용)
    update_sql = "UPDATE board_comments SET content = %s WHERE id = %s"
    try:
        execute_query(update_sql, (new_content, comment_id))
        return jsonify({'success': True})
    except Exception as e:
        print(f"수정 에러: {e}")
        return jsonify({'success': False, 'message': 'DB 수정 중 오류 발생'}), 500

# [삭제 메서드] - fetch_query로 변경
@board_bp.route('/comment/delete/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    # 1. 본인 확인 (fetch_query 사용!)
    check_sql = "SELECT member_id FROM board_comments WHERE id = %s"
    comment = fetch_query(check_sql, (comment_id,), one=True)

    if not comment or comment['member_id'] != session['user_id']:
        return jsonify({'success': False, 'message': '삭제 권한이 없습니다.'})

    # 2. DB 삭제
    delete_sql = "DELETE FROM board_comments WHERE id = %s"
    try:
        execute_query(delete_sql, (comment_id,))
        return jsonify({'success': True})
    except Exception as e:
        print(f"삭제 에러: {e}")
        return jsonify({'success': False, 'message': 'DB 삭제 중 오류 발생'}), 500

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

    print('board_id :', board_id)

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

# 휴지통 목록 조회
@board_bp.route('/trash')
@login_required
def board_trash():
    user_id = session['user_id']
    # 삭제된 지 30일 이내인 게시물만 조회
    sql = """
        SELECT *, DATEDIFF(DATE_ADD(deleted_at, INTERVAL 30 DAY), NOW()) as remaining_days
        FROM boards 
        WHERE member_id = %s AND active = 0 AND deleted_at IS NOT NULL
        ORDER BY deleted_at DESC
    """
    trash_posts = fetch_query(sql, (user_id,))
    return render_template('board/trash.html', posts=trash_posts)

# 휴지통에서 복구하기
@board_bp.route('/restore/<int:board_id>')
@login_required
def board_restore(board_id):

    sql = "UPDATE boards SET active = 1, deleted_at = NULL WHERE id = %s"
    execute_query(sql, (board_id,))

    flash("게시물이 성공적으로 복구되었습니다.")
    return redirect(url_for('mypage.my_activity'))

# 휴지통에서 즉시 영구 삭제
@board_bp.route('/permanent_delete/<int:board_id>')
@login_required
def board_permanent_delete(board_id):
    # 1. DB에서 해당 게시물을 완전히 삭제하는 쿼리
    sql = "DELETE FROM boards WHERE id = %s"
    execute_query(sql, (board_id,))

    # 2. flash 기능을 쓰려면 상단에 'from flask import flash'가 있어야 합니다!
    flash("게시물이 영구 삭제되었습니다.")
    return redirect(url_for('mypage.my_activity'))

# 30일 지난 게시물 자동 영구 삭제 함수
def cleanup_old_trash():
    try:
        # active가 0이고 삭제된 지 30일이 넘은 데이터 삭제
        sql = """
            DELETE FROM boards 
            WHERE active = 0 
              AND deleted_at IS NOT NULL 
              AND deleted_at < NOW() - INTERVAL 30 DAY
        """
        execute_query(sql)
        print("휴지통 자동 청소 완료")
    except Exception as e:
        print(f"자동 삭제 중 오류 발생: {e}")


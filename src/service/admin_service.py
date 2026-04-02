from flask import (
    Blueprint,
    request, session, flash,
    render_template, redirect, url_for,
    jsonify
)
from datetime import datetime, timedelta
from src.common import (
    Session,
    fetch_query, execute_query,
    log_system,
    admin_required
)

admin_bp = Blueprint('admin', __name__)

PAGE_SIZE = 10  # 페이지당 행 수

# ──────────────────────────────────────────────
#  공통: 사이드바 배지용 카운트
# ──────────────────────────────────────────────
def _sidebar_context(members, boards):
    """이미 조회한 members/boards를 받아서 컨텍스트 생성 — DB 중복 호출 없음"""
    return {
        'new_members_count': AdminService.get_today_new_members(members),
        'new_boards_count':  AdminService.get_today_new_boards(boards),
        'current_user_role': session.get('user_role'),
        'current_user_name': session.get('user_name'),
        'current_user_img':  session.get('user_profile'),
    }


# ──────────────────────────────────────────────
#  대시보드
# ──────────────────────────────────────────────
@admin_bp.route('/')
@admin_required
def dashboard():
    members = AdminService.get_members()
    boards  = AdminService.get_boards()

    # 주간 게시글 집계
    week_counts = [0] * 7
    today = datetime.now().date()
    for b in boards:
        diff = (today - b['created_at'].date()).days
        if 0 <= diff <= 6:
            week_counts[6 - diff] += 1

    ctx = _sidebar_context(members, boards)
    ai_stats = AdminService.get_ai_analysis_total()
    ctx.update({
        'active_nav':    'dashboard',
        'total_members': len(members),
        'total_boards':  len(boards),
        'new_members':   AdminService.get_today_new_members(members),
        'new_boards':    AdminService.get_today_new_boards(boards),
        'report_count':  sum(b['report_count'] for b in boards),
        'ai_total': ai_stats['total'],
        'ai_today': ai_stats['today'],
        'week_counts':   week_counts,
        'today':         today,
    })
    return render_template('admin/dashboard.html', **ctx)


# ──────────────────────────────────────────────
#  회원 관리  (서버사이드 페이지네이션)
# ──────────────────────────────────────────────
@admin_bp.route('/members')
@admin_required
def members():
    search_q      = request.args.get('q', '').strip()
    filter_role   = request.args.get('role', '')
    filter_active = request.args.get('active', '')
    page          = max(int(request.args.get('page', 1)), 1)

    all_members = AdminService.get_members()

    # 필터링
    filtered = all_members
    if search_q:
        q = search_q.lower()
        filtered = [m for m in filtered
                    if q in (m['name'] or '').lower()
                    or q in (m['uid'] or '').lower()]
    if filter_role:
        filtered = [m for m in filtered if m['role'] == filter_role]
    if filter_active:
        filtered = [m for m in filtered if str(m['active']) == filter_active]

    total_pages = max((len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page        = min(page, total_pages)
    start       = (page - 1) * PAGE_SIZE
    paged       = filtered[start: start + PAGE_SIZE]

    ctx = _sidebar_context(all_members, AdminService.get_boards())
    ctx.update({
        'active_nav':     'members',
        'members':        paged,
        'page':           page,
        'total_pages':    total_pages,
        'search_q':       search_q,
        'filter_role':    filter_role,
        'filter_active':  filter_active,
    })
    return render_template('admin/members.html', **ctx)


# ──────────────────────────────────────────────
#  게시글 관리  (서버사이드 페이지네이션)
# ──────────────────────────────────────────────
@admin_bp.route('/posts')
@admin_required
def posts():
    search_q        = request.args.get('q', '').strip()
    filter_category = request.args.get('category', '')   # free / qna / info
    filter_type     = request.args.get('type', '')        # notice / normal
    filter_status   = request.args.get('status', '')      # normal / reported / hidden
    page            = max(int(request.args.get('page', 1)), 1)

    all_boards = AdminService.get_boards()

    # 필터링
    def _status(b):
        if not b['active']:           return 'hidden'
        if b['report_count'] > 0:     return 'reported'
        return 'normal'

    filtered = all_boards
    if search_q:
        q = search_q.lower()
        filtered = [b for b in filtered
                    if q in (b['title'] or '').lower()
                    or q in (b['author'] or '').lower()
                    or q in (b['nickname'] or '').lower()]
    if filter_category:
        filtered = [b for b in filtered if (b['category'] or '') == filter_category]
    if filter_type == 'notice':
        filtered = [b for b in filtered if b['is_pinned']]
    elif filter_type == 'normal':
        filtered = [b for b in filtered if not b['is_pinned']]
    if filter_status:
        filtered = [b for b in filtered if _status(b) == filter_status]

    total_pages = max((len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page        = min(page, total_pages)
    start       = (page - 1) * PAGE_SIZE
    paged       = filtered[start: start + PAGE_SIZE]

    ctx = _sidebar_context(AdminService.get_members(), all_boards)
    ctx.update({
        'active_nav':       'posts',
        'boards':           paged,
        'page':             page,
        'total_pages':      total_pages,
        'search_q':         search_q,
        'filter_category':  filter_category,
        'filter_type':      filter_type,
        'filter_status':    filter_status,
    })
    return render_template('admin/posts.html', **ctx)


# ──────────────────────────────────────────────
#  AI 자료실
# ──────────────────────────────────────────────
@admin_bp.route('/files')
@admin_required
def files():
    members = AdminService.get_ai_analysis_members()
    all_members = AdminService.get_members()
    all_boards  = AdminService.get_boards()
    ctx = _sidebar_context(all_members, all_boards)
    ctx.update({
        'active_nav': 'files',
        'members':    members,
    })
    return render_template('admin/files.html', **ctx)


# ──────────────────────────────────────────────
#  AI 자료실 — 회원별 파일 목록
# ──────────────────────────────────────────────
@admin_bp.route('/files/<int:user_id>')
@admin_required
def files_detail(user_id):
    page = max(int(request.args.get('page', 1)), 1)
    member = AdminService.get_member_detail(user_id)
    files, total_pages = AdminService.get_ai_analysis_files(user_id, page)

    all_members = AdminService.get_members()
    all_boards = AdminService.get_boards()
    ctx = _sidebar_context(all_members, all_boards)
    ctx.update({
        'active_nav': 'files',
        'member': member,
        'files': files,
        'page': page,
        'total_pages': total_pages,
        'user_id': user_id,
    })
    return render_template('admin/files_detail.html', **ctx)


# ──────────────────────────────────────────────
#  회원 CRUD
# ──────────────────────────────────────────────
@admin_bp.route('/member/add', methods=['POST'])
@admin_required
def add_member():
    success = AdminService.add_member(
        request.form.get('uid'),
        request.form.get('name'),
        request.form.get('nickname'),
        request.form.get('password'),
        request.form.get('birthdate') or None,
    )
    if success:
        flash('✅ 회원이 추가되었습니다.', 'success')
    else:
        flash('❌ 추가 중 오류가 발생했습니다.', 'danger')
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.members'))


@admin_bp.route('/member/update/<int:member_id>', methods=['POST'])
@admin_required
def update_member(member_id):
    current_role = session.get('user_role')
    role = request.form.get('role')

    conn = Session.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT role FROM members WHERE id=%s", (member_id,))
            row = cursor.fetchone()
            target_role = row['role'] if row else None
    except Exception as e:
        print(f"update_member role check 오류: {e}")
        target_role = None

    # 최고 관리자 회원은 수정 불가 (role, active 모두)
    if target_role == 'admin':
        return ('', 403) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
            else redirect(url_for('admin.members'))

    # admin 등급으로 임명 시도 차단 (admin만 가능하더라도 임명 자체 불가)
    if role == 'admin':
        return ('', 403) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
            else redirect(url_for('admin.members'))

    # manager는 등급 변경 불가 — name/nickname/password/active만 허용
    if current_role == 'manager':
        role = target_role  # 기존 role 유지

    success = AdminService.update_member(
        member_id,
        request.form.get('name'),
        request.form.get('nickname'),
        request.form.get('password'),
        role,
        request.form.get('active'),
        request.form.get('birthdate') or None,
    )
    if success:
        flash('✅ 회원 정보가 수정되었습니다.', 'success')
    else:
        flash('❌ 수정 중 오류가 발생했습니다.', 'danger')
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
        else redirect(url_for('admin.members'))


@admin_bp.route('/member/delete/<int:member_id>', methods=['POST'])
@admin_required
def delete_member(member_id):
    success = AdminService.delete_member(member_id)
    if success:
        flash('✅ 변경되었습니다.', 'success')
    else:
        flash('❌ 변경 중 오류가 발생했습니다.', 'danger')
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.members'))


# ──────────────────────────────────────────────
#  회원 상세 페이지
# ──────────────────────────────────────────────
@admin_bp.route('/members/<int:member_id>/detail')
@admin_required
def member_detail(member_id):
    member = AdminService.get_member_detail(member_id)
    if not member:
        flash('존재하지 않는 회원입니다.', 'danger')
        return redirect(url_for('admin.members'))

    tab = request.args.get('tab', 'boards')
    page = max(int(request.args.get('page', 1)), 1)

    data, total_pages = AdminService.get_member_tab_data(member_id, tab, page)

    # 통계
    stats = AdminService.get_member_stats(member_id)

    all_members = AdminService.get_members()
    all_boards = AdminService.get_boards()
    ctx = _sidebar_context(all_members, all_boards)
    ctx.update({
        'active_nav': 'members',
        'member': member,
        'stats': stats,
        'tab': tab,
        'tab_data': data,
        'page': page,
        'total_pages': total_pages,
    })
    return render_template('admin/member_detail.html', **ctx)


# ──────────────────────────────────────────────
#  회원 상세 - 게시글 삭제
# ──────────────────────────────────────────────
@admin_bp.route('/members/<int:member_id>/board/<int:board_id>/delete', methods=['POST'])
@admin_required
def delete_member_board(member_id, board_id):
    AdminService.delete_board_by_admin(board_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
        else redirect(url_for('admin.member_detail', member_id=member_id, tab='boards'))


# ──────────────────────────────────────────────
#  회원 상세 - 댓글 삭제
# ──────────────────────────────────────────────
@admin_bp.route('/members/<int:member_id>/comment/<int:comment_id>/delete', methods=['POST'])
@admin_required
def delete_member_comment(member_id, comment_id):
    AdminService.delete_comment_by_admin(comment_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
        else redirect(url_for('admin.member_detail', member_id=member_id, tab='comments'))

# ──────────────────────────────────────────────
#  게시글 액션
# ──────────────────────────────────────────────
@admin_bp.route('/board/hide/<int:board_id>', methods=['POST'])
@admin_required
def hide_board(board_id):
    AdminService.set_board_active(board_id, 0)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))


@admin_bp.route('/board/restore/<int:board_id>', methods=['POST'])
@admin_required
def restore_board(board_id):
    AdminService.set_board_active(board_id, 1)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))


@admin_bp.route('/board/unreport/<int:board_id>', methods=['POST'])
@admin_required
def unreport_board(board_id):
    AdminService.delete_board_reports(board_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))


@admin_bp.route('/board/pin/<int:board_id>', methods=['POST'])
@admin_required
def pin_board(board_id):
    AdminService.set_board_pinned(board_id, 1)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))

@admin_bp.route('/board/unpin/<int:board_id>', methods=['POST'])
@admin_required
def unpin_board(board_id):
    AdminService.set_board_pinned(board_id, 0)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))


@admin_bp.route('/board/update/<int:board_id>', methods=['POST'])
@admin_required
def update_board(board_id):
    AdminService.update_board(
        board_id,
        request.form.get('title'),
        request.form.get('content'),
    )
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))


@admin_bp.route('/board/detail/<int:board_id>')
@admin_required
def board_detail(board_id):
    board = AdminService.get_board_detail(board_id)
    if not board:
        return jsonify({'error': '게시글 없음'}), 404
    board['created_at'] = board['created_at'].strftime('%Y.%m.%d %H:%M') if board.get('created_at') else ''
    return jsonify(board)


# ──────────────────────────────────────────────
#  방문자 통계 API
# ──────────────────────────────────────────────
@admin_bp.route('/api/visitors')
@admin_required
def visitor_stats():
    return jsonify({
        'today': AdminService.get_visitor_stats('today'),
        'week':  AdminService.get_visitor_stats('week'),
        'month': AdminService.get_visitor_stats('month'),
    })

# ──────────────────────────────────────────────
#  AI 통계 API 라우트 추가
# ──────────────────────────────────────────────
@admin_bp.route('/api/ai_stats')
@admin_required
def ai_stats():
    return jsonify(AdminService.get_ai_stats())



# ══════════════════════════════════════════════
#  AdminService
# ══════════════════════════════════════════════
class AdminService:

    @classmethod
    def get_members(cls):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM members ORDER BY id DESC")
                return cursor.fetchall()
        except Exception as e:
            print(f"get_members() 오류: {e}")
            return []

    @classmethod
    def get_today_new_members(cls, members):
        since = datetime.now() - timedelta(hours=24)
        return len([m for m in members if m['created_at'] >= since])

    @classmethod
    def add_member(cls, uid, name, nickname, password, birthdate):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO members (uid, name, nickname, password, birthdate)
                    VALUES (%s, %s, %s, %s, %s)
                """, (uid, name, nickname, password, birthdate))
            conn.commit()
            return True
        except Exception as e:
            print(f"add_member() 오류: {e}")
            conn.rollback()
            return False

    @classmethod
    def update_member(cls, member_id, name, nickname, password, role, active, birthdate):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                if password:
                    cursor.execute("""
                        UPDATE members
                        SET name=%s, nickname=%s, password=%s, role=%s, active=%s, birthdate=%s
                        WHERE id=%s
                    """, (name, nickname, password, role, active, birthdate, member_id))
                else:
                    cursor.execute("""
                        UPDATE members
                        SET name=%s, nickname=%s, role=%s, active=%s, birthdate=%s
                        WHERE id=%s
                    """, (name, nickname, role, active, birthdate, member_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"update_member() 오류: {e}")
            conn.rollback()
            return False

    @classmethod
    def delete_member(cls, member_id):
        """active 토글 (0↔1)"""
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT active FROM members WHERE id=%s", (member_id,))
                row = cursor.fetchone()
                new_active = 0 if row['active'] == 1 else 1
                cursor.execute("UPDATE members SET active=%s WHERE id=%s", (new_active, member_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"delete_member() 오류: {e}")
            conn.rollback()
            return False

    @classmethod
    def get_boards(cls):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        b.id, b.title, b.created_at, b.visits,
                        b.active, b.is_pinned, b.category,
                        m.name     AS author,
                        m.nickname AS nickname,
                        COUNT(r.id) AS report_count
                    FROM boards b
                    LEFT JOIN members m ON b.member_id = m.id
                    LEFT JOIN reports r ON r.board_id  = b.id
                    GROUP BY b.id, b.title, b.created_at, b.visits,
                             b.active, b.is_pinned, b.category, m.name, m.nickname
                    ORDER BY b.created_at DESC
                """)
                return cursor.fetchall()
        except Exception as e:
            print(f"get_boards() 오류: {e}")
            return []

    @classmethod
    def get_today_new_boards(cls, boards):
        since = datetime.now() - timedelta(hours=3)
        return len([b for b in boards if b['created_at'] >= since])

    @classmethod
    def set_board_active(cls, board_id, active):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE boards SET active=%s WHERE id=%s", (active, board_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"set_board_active() 오류: {e}")
            conn.rollback()
            return False

    @classmethod
    def delete_board_reports(cls, board_id):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM reports WHERE board_id=%s", (board_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"delete_board_reports() 오류: {e}")
            conn.rollback()
            return False

    @classmethod
    def set_board_pinned(cls, board_id, is_pinned):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE boards SET is_pinned=%s WHERE id=%s", (is_pinned, board_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"set_board_pinned() 오류: {e}")
            conn.rollback()
            return False

    @classmethod
    def update_board(cls, board_id, title, content):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE boards SET title=%s, content=%s WHERE id=%s",
                    (title, content, board_id)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"update_board() 오류: {e}")
            conn.rollback()
            return False

    @classmethod
    def get_board_detail(cls, board_id):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT b.id, b.title, b.content, b.created_at,
                           b.visits, b.active, b.is_pinned,
                           m.name AS author
                    FROM boards b
                    LEFT JOIN members m ON b.member_id = m.id
                    WHERE b.id = %s
                """, (board_id,))
                board = cursor.fetchone()
                cursor.execute(
                    "SELECT reason FROM reports WHERE board_id = %s", (board_id,)
                )
                reports = cursor.fetchall()
                board['reports'] = [r['reason'] for r in reports] if reports else []
                return board
        except Exception as e:
            print(f"get_board_detail() 오류: {e}")
            return None

    @classmethod
    def get_visitor_stats(cls, range_type='today'):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                if range_type == 'today':
                    cursor.execute("""
                        SELECT
                            COUNT(*)                    AS total,
                            COUNT(member_id)            AS logged_in,
                            COUNT(*) - COUNT(member_id) AS anonymous
                        FROM system_logs
                        WHERE category = 'VISIT'
                          AND action   = 'PAGE_VIEW'
                          AND DATE(created_at) = CURDATE()
                    """)
                    row = cursor.fetchone()
                    return {
                        'total':     row['total'],
                        'logged_in': row['logged_in'],
                        'anonymous': row['anonymous'],
                    }
                else:
                    interval = 7 if range_type == 'week' else 365
                    cursor.execute("""
                        SELECT
                            DATE(created_at)            AS date,
                            COUNT(*)                    AS total,
                            COUNT(member_id)            AS logged_in,
                            COUNT(*) - COUNT(member_id) AS anonymous
                        FROM system_logs
                        WHERE category = 'VISIT'
                          AND action   = 'PAGE_VIEW'
                          AND created_at >= CURDATE() - INTERVAL %s DAY
                        GROUP BY DATE(created_at)
                        ORDER BY date ASC
                    """, (interval,))
                    return [
                        {
                            'date':      str(r['date']),
                            'total':     r['total'],
                            'logged_in': r['logged_in'],
                            'anonymous': r['anonymous'],
                        }
                        for r in cursor.fetchall()
                    ]
        except Exception as e:
            print(f"get_visitor_stats() 오류: {e}")
            return {'total': 0, 'logged_in': 0, 'anonymous': 0} if range_type == 'today' else []

    # ──────────────────────────────────────────────
    #  회원 상세 - 휴지통 영구삭제
    # ──────────────────────────────────────────────
    @admin_bp.route('/members/<int:member_id>/trash/<int:board_id>/delete', methods=['POST'])
    @admin_required
    def delete_member_trash(member_id, board_id):
        AdminService.delete_board_permanent(board_id)
        return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
            else redirect(url_for('admin.member_detail', member_id=member_id, tab='trash'))

    # ──────────────────────────────────────────────
    #  AdminService 추가 메서드들
    # ──────────────────────────────────────────────

    @classmethod
    def get_member_detail(cls, member_id):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM members WHERE id=%s", (member_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"get_member_detail() 오류: {e}")
            return None

    @classmethod
    def get_member_stats(cls, member_id):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        (SELECT COUNT(*) FROM boards
                         WHERE member_id=%s AND deleted_at IS NULL AND active=1) AS board_count,
                        (SELECT COUNT(*) FROM board_comments
                         WHERE member_id=%s)                                      AS comment_count,
                        (SELECT COUNT(*) FROM follows
                         WHERE following_id=%s)                                   AS follower_count,
                        (SELECT COUNT(*) FROM follows
                         WHERE follower_id=%s)                                    AS following_count,
                         (SELECT COUNT(*) FROM ai_analysis
                         WHERE user_id=%s)                                        AS ai_count
                """, (member_id, member_id, member_id, member_id, member_id))
                return cursor.fetchone()
        except Exception as e:
            print(f"get_member_stats() 오류: {e}")
            return {'board_count': 0, 'comment_count': 0, 'follower_count': 0, 'following_count': 0}

    @classmethod
    def get_member_tab_data(cls, member_id, tab, page, page_size=10):
        conn = Session.get_connection()
        offset = (page - 1) * page_size
        try:
            with conn.cursor() as cursor:
                if tab == 'boards':
                    cursor.execute("SELECT COUNT(*) AS cnt FROM boards WHERE member_id=%s AND deleted_at IS NULL",
                                   (member_id,))
                    total = cursor.fetchone()['cnt']
                    cursor.execute("""
                        SELECT id, title, category, is_pinned, visits, created_at, active
                        FROM boards
                        WHERE member_id=%s AND deleted_at IS NULL
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (member_id, page_size, offset))

                elif tab == 'comments':
                    cursor.execute("SELECT COUNT(*) AS cnt FROM board_comments WHERE member_id=%s", (member_id,))
                    total = cursor.fetchone()['cnt']
                    cursor.execute("""
                        SELECT c.id, c.content, c.created_at, c.active,
                               b.title AS board_title, b.id AS board_id
                        FROM board_comments c
                        LEFT JOIN boards b ON c.board_id = b.id
                        WHERE c.member_id=%s
                        ORDER BY c.created_at DESC
                        LIMIT %s OFFSET %s
                    """, (member_id, page_size, offset))

                elif tab == 'trash':
                    cursor.execute(
                        "SELECT COUNT(*) AS cnt FROM boards WHERE member_id=%s AND (active=0 OR deleted_at IS NOT NULL)",
                        (member_id,))
                    total = cursor.fetchone()['cnt']
                    cursor.execute("""
                        SELECT id, title, category, created_at, deleted_at, active
                        FROM boards
                        WHERE member_id=%s AND (active=0 OR deleted_at IS NOT NULL)
                        ORDER BY deleted_at DESC, created_at DESC
                        LIMIT %s OFFSET %s
                    """, (member_id, page_size, offset))

                elif tab == 'comment_trash':
                    cursor.execute("SELECT COUNT(*) AS cnt FROM board_comments WHERE member_id=%s AND active=0",
                                   (member_id,))
                    total = cursor.fetchone()['cnt']
                    cursor.execute("""
                        SELECT c.id, c.content, c.created_at, c.deleted_at, c.active,
                               b.title AS board_title, b.id AS board_id
                        FROM board_comments c
                        LEFT JOIN boards b ON c.board_id = b.id
                        WHERE c.member_id=%s AND c.active=0
                        ORDER BY c.created_at DESC
                        LIMIT %s OFFSET %s
                    """, (member_id, page_size, offset))

                elif tab == 'follows':
                    cursor.execute("SELECT COUNT(*) AS cnt FROM follows WHERE follower_id=%s", (member_id,))
                    total = cursor.fetchone()['cnt']
                    cursor.execute("""
                        SELECT m.id, m.nickname, m.name, m.profile_img, f.created_at
                        FROM follows f
                        JOIN members m ON f.following_id = m.id
                        WHERE f.follower_id=%s
                        ORDER BY f.created_at DESC
                        LIMIT %s OFFSET %s
                    """, (member_id, page_size, offset))

                elif tab == 'followers':
                    cursor.execute("SELECT COUNT(*) AS cnt FROM follows WHERE following_id=%s", (member_id,))
                    total = cursor.fetchone()['cnt']
                    cursor.execute("""
                        SELECT m.id, m.nickname, m.name, m.profile_img, f.created_at
                        FROM follows f
                        JOIN members m ON f.follower_id = m.id
                        WHERE f.following_id=%s
                        ORDER BY f.created_at DESC
                        LIMIT %s OFFSET %s
                    """, (member_id, page_size, offset))

                elif tab == 'blocks':
                    cursor.execute("SELECT COUNT(*) AS cnt FROM blocks WHERE blocker_id=%s", (member_id,))
                    total = cursor.fetchone()['cnt']
                    cursor.execute("""
                        SELECT m.id, m.nickname, m.name, m.profile_img, b.created_at
                        FROM blocks b
                        JOIN members m ON b.blocked_id = m.id
                        WHERE b.blocker_id=%s
                        ORDER BY b.created_at DESC
                        LIMIT %s OFFSET %s
                    """, (member_id, page_size, offset))

                else:
                    return [], 1

                rows = cursor.fetchall()
                total_pages = max((total + page_size - 1) // page_size, 1)
                return rows, total_pages
        except Exception as e:
            print(f"get_member_tab_data() 오류: {e}")
            return [], 1

    @classmethod
    def delete_board_by_admin(cls, board_id):
        """active 토글 (0↔1)"""
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT active FROM boards WHERE id=%s", (board_id,))
                row = cursor.fetchone()
                new_active = 0 if row['active'] == 1 else 1
                if new_active == 0:
                    # 숨김 처리 시 deleted_at 기록
                    cursor.execute("""
                        UPDATE boards
                        SET active=%s, deleted_at=NOW()
                        WHERE id=%s
                    """, (new_active, board_id))
                else:
                    # 복구 시 deleted_at 초기화
                    cursor.execute("""
                        UPDATE boards
                        SET active=%s, deleted_at=NULL
                        WHERE id=%s
                    """, (new_active, board_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"delete_board_by_admin() 오류: {e}")
            conn.rollback()
            return False

    @classmethod
    def delete_comment_by_admin(cls, comment_id):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT active FROM board_comments WHERE id=%s", (comment_id,))
                row = cursor.fetchone()
                new_active = 0 if row['active'] == 1 else 1
                if new_active == 0:
                    # 숨김 처리 시 deleted_at 기록
                    cursor.execute("""
                        UPDATE board_comments
                        SET active=%s, deleted_at=NOW()
                        WHERE id=%s
                    """, (new_active, comment_id))
                else:
                    # 복구 시 deleted_at 초기화
                    cursor.execute("""
                        UPDATE board_comments
                        SET active=%s, deleted_at=NULL
                        WHERE id=%s
                    """, (new_active, comment_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"delete_comment_by_admin() 오류: {e}")
            conn.rollback()
            return False

    @classmethod
    def delete_board_permanent(cls, board_id):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM boards WHERE id=%s", (board_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"delete_board_permanent() 오류: {e}")
            conn.rollback()
            return False

    @classmethod
    def get_ai_analysis_total(cls):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN DATE(created_at) = CURDATE() THEN 1 ELSE 0 END) AS today
                    FROM ai_analysis
                """)
                row = cursor.fetchone()
                return {
                    'total': row['total'] or 0,
                    'today': row['today'] or 0
                }
        except Exception as e:
            print(f"get_ai_analysis_total() 오류: {e}")
            return {'total': 0, 'today': 0}

    @classmethod
    def get_ai_stats(cls):
        """동물 누적 합계 + 최근 14일 날짜별 탐지 추이"""
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                # 누적 합계
                cursor.execute("""
                        SELECT
                            COALESCE(SUM(boar_count), 0)       AS total_boar,
                            COALESCE(SUM(water_deer_count), 0) AS total_deer,
                            COALESCE(SUM(racoon_count), 0)     AS total_racoon
                        FROM ai_analysis
                    """)
                totals = cursor.fetchone()

                # 날짜별 추이 (최근 14일)
                cursor.execute("""
                        SELECT
                            DATE(created_at)             AS date,
                            SUM(boar_count)       AS boar,
                            SUM(water_deer_count) AS deer,
                            SUM(racoon_count)     AS racoon
                        FROM ai_analysis
                        WHERE created_at >= CURDATE() - INTERVAL 14 DAY
                        GROUP BY DATE(created_at)
                        ORDER BY date ASC
                    """)
                rows = cursor.fetchall()
                trend = [
                    {
                        'date': str(r['date']),
                        'boar': int(r['boar'] or 0),
                        'deer': int(r['deer'] or 0),
                        'racoon': int(r['racoon'] or 0),
                    }
                    for r in rows
                ]

                return {
                    'totals': {
                        'boar': int(totals['total_boar']),
                        'deer': int(totals['total_deer']),
                        'racoon': int(totals['total_racoon']),
                    },
                    'trend': trend,
                }
        except Exception as e:
            print(f"get_ai_stats() 오류: {e}")
            return {
                'totals': {'boar': 0, 'deer': 0, 'racoon': 0},
                'trend': []
            }

    @classmethod
    def get_ai_analysis_members(cls):
        """AI 분석 파일이 있는 회원 목록 + 각 통계"""
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                        SELECT
                            m.id, m.name, m.nickname, m.profile_img, m.uid,
                            COUNT(a.id)              AS file_count,
                            SUM(a.boar_count)        AS total_boar,
                            SUM(a.water_deer_count)  AS total_deer,
                            SUM(a.racoon_count)      AS total_racoon,
                            MAX(a.created_at)        AS last_analysis
                        FROM ai_analysis a
                        JOIN members m ON a.user_id = m.id
                        GROUP BY m.id, m.name, m.nickname, m.profile_img, m.uid
                        ORDER BY last_analysis DESC
                    """)
                return cursor.fetchall()
        except Exception as e:
            print(f"get_ai_analysis_members() 오류: {e}")
            return []

    @classmethod
    def get_ai_analysis_files(cls, user_id, page=1, page_size=10):
        """특정 회원의 AI 분석 파일 목록"""
        conn = Session.get_connection()
        offset = (page - 1) * page_size
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM ai_analysis WHERE user_id=%s",
                    (user_id,)
                )
                total = cursor.fetchone()['cnt']
                cursor.execute("""
                        SELECT id, filename, boar_count, water_deer_count,
                               racoon_count, created_at, image_url
                        FROM ai_analysis
                        WHERE user_id=%s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (user_id, page_size, offset))
                rows = cursor.fetchall()
                total_pages = max((total + page_size - 1) // page_size, 1)
                return rows, total_pages
        except Exception as e:
            print(f"get_ai_analysis_files() 오류: {e}")
            return [], 1

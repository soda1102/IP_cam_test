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
    ctx.update({
        'active_nav':    'dashboard',
        'total_members': len(members),
        'total_boards':  len(boards),
        'new_members':   AdminService.get_today_new_members(members),
        'new_boards':    AdminService.get_today_new_boards(boards),
        'report_count':  sum(b['report_count'] for b in boards),
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
    filter_category = request.args.get('category', '')
    filter_status   = request.args.get('status', '')
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
    if filter_category == 'notice':
        filtered = [b for b in filtered if b['is_pinned']]
    elif filter_category == 'normal':
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
        'filter_status':    filter_status,
    })
    return render_template('admin/posts.html', **ctx)


# ──────────────────────────────────────────────
#  AI 자료실
# ──────────────────────────────────────────────
@admin_bp.route('/files')
@admin_required
def files():
    members = AdminService.get_members()
    boards  = AdminService.get_boards()
    ctx = _sidebar_context(members, boards)
    ctx['active_nav'] = 'files'
    return render_template('admin/files.html', **ctx)


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
    success = AdminService.update_member(
        member_id,
        request.form.get('name'),
        request.form.get('nickname'),
        request.form.get('password'),
        request.form.get('role'),
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
                        b.active, b.is_pinned,
                        m.name     AS author,
                        m.nickname AS nickname,
                        COUNT(r.id) AS report_count
                    FROM boards b
                    LEFT JOIN members m ON b.member_id = m.id
                    LEFT JOIN reports r ON r.board_id  = b.id
                    GROUP BY b.id, b.title, b.created_at, b.visits,
                             b.active, b.is_pinned, m.name, m.nickname
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
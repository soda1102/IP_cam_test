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

@admin_bp.route('/')
@admin_required
def dashboard():
    members = AdminService.get_members()
    new_members = AdminService.get_today_new_members(members)
    boards = AdminService.get_boards()
    new_boards = AdminService.get_today_new_boards(boards)
    report_count = sum(b['report_count'] for b in boards)

    # 주간 게시글 집계 (오늘 기준 최근 7일)
    week_counts = [0] * 7
    today = datetime.now().date()
    for b in boards:
        diff = (today - b['created_at'].date()).days
        if 0 <= diff <= 6:
            week_counts[6 - diff] += 1  # 오늘이 맨 오른쪽
    return render_template('admin/admin.html',
                           members=members, new_members=new_members, boards=boards,
                           new_boards=new_boards, report_count=report_count, week_counts=week_counts,today=today,
                           current_user_role=session.get('user_role'),
                           current_user_name=session.get('user_name'),
                           current_user_img=session.get('user_profile'),
                           )

@admin_bp.route('/member/delete/<int:member_id>', methods=['POST'])
def delete_member(member_id):
    success = AdminService.delete_member(member_id)
    if success:
        flash('멤버가 삭제되었습니다.', 'success')
    else:
        flash('삭제 중 오류가 발생했습니다.', 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/member/update/<int:member_id>', methods=['POST'])
def update_member(member_id):
    name      = request.form.get('name')
    password  = request.form.get('password')   # 빈 문자열이면 변경 안 함
    role      = request.form.get('role')
    active    = request.form.get('active')     # '1' or '0'
    birthdate = request.form.get('birthdate')  # 'YYYY-MM-DD'
    birthdate = birthdate if birthdate else None
    success = AdminService.update_member(member_id, name, password, role, active, birthdate)

    if success:
        flash('멤버 정보가 수정되었습니다.', 'success')
    else:
        flash('수정 중 오류가 발생했습니다.', 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/member/add', methods=['POST'])
def add_member():
    uid       = request.form.get('uid')
    name      = request.form.get('name')
    password  = request.form.get('password')
    birthdate = request.form.get('birthdate')

    success = AdminService.add_member(uid, name, password, birthdate)
    if success:
        flash('✅ 회원이 추가되었습니다.', 'success')
    else:
        flash('❌ 추가 중 오류가 발생했습니다.', 'danger')
    return redirect(url_for('admin.dashboard'))


# =============게시글================

@admin_bp.route('/board/hide/<int:board_id>', methods=['POST'])
def hide_board(board_id):
    AdminService.set_board_active(board_id, 0)
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/board/restore/<int:board_id>', methods=['POST'])
def restore_board(board_id):
    AdminService.set_board_active(board_id, 1)
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/board/unreport/<int:board_id>', methods=['POST'])
def unreport_board(board_id):
    AdminService.delete_board_reports(board_id)
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/board/pin/<int:board_id>', methods=['POST'])
def pin_board(board_id):
    AdminService.set_board_pinned(board_id, 1)
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/board/update/<int:board_id>', methods=['POST'])
def update_board(board_id):
    title   = request.form.get('title')
    content = request.form.get('content')
    AdminService.update_board(board_id, title, content)
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/board/detail/<int:board_id>')
def board_detail(board_id):
    board = AdminService.get_board_detail(board_id)
    if not board:
        return jsonify({'error': '게시글 없음'}), 404
    board['created_at'] = board['created_at'].strftime('%Y.%m.%d %H:%M') if board.get('created_at') else ''
    return jsonify(board)

class AdminService:
    # 멤버 전체 조회
    @classmethod
    def get_members(cls):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM members")
                return cursor.fetchall()
        except:
            print("AdminService.get_members() 오류발생....")
            return []
        finally:
            pass

    # 24시간 기준 신규 회원 조회
    @classmethod
    def get_today_new_members(cls, members):
        # 이미 넘어온 members 객체 재활용 → 쿼리 추가 없음
        since = datetime.now() - timedelta(hours=24)
        return len([m for m in members if m['created_at'] >= since])

    @classmethod
    def update_member(cls, member_id, name, password, role, active, birthdate):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                if password:  # 비밀번호 입력한 경우만 변경
                    # import hashlib
                    # hashed_pw = hashlib.sha256(password.encode()).hexdigest()
                    cursor.execute("""
                        UPDATE members
                        SET name=%s, password=%s, role=%s, active=%s, birthdate=%s
                        WHERE id=%s
                    """,(name, password, role, active, birthdate, member_id))
                    # (name, hashed_pw, role, active, birthdate, member_id))

                else:  # 비밀번호 미입력 시 기존 유지
                    cursor.execute("""
                        UPDATE members
                        SET name=%s, role=%s, active=%s, birthdate=%s
                        WHERE id=%s
                    """, (name, role, active, birthdate, member_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"AdminService.update_member() 오류발생.... {e}")
            conn.rollback()
            return False

    @classmethod
    def delete_member(cls, member_id):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                # 현재 active 값 조회 후 반전
                cursor.execute("SELECT active FROM members WHERE id=%s", (member_id,))
                row = cursor.fetchone()
                new_active = 0 if row['active'] == 1 else 1
                cursor.execute("UPDATE members SET active=%s WHERE id=%s", (new_active, member_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"AdminService.delete_member() 오류발생.... {e}")
            conn.rollback()
            return False

    @classmethod
    def add_member(cls, uid, name, password, birthdate):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                # TODO: 비밀번호 암호화 추후 적용
                cursor.execute("""
                    INSERT INTO members (uid, name, password, birthdate)
                    VALUES (%s, %s, %s, %s)
                """, (uid, name, password, birthdate if birthdate else None))
            conn.commit()
            return True
        except Exception as e:
            print(f"AdminService.add_member() 오류발생.... {e}")
            conn.rollback()
            return False

    # 게시글 전체 조회
    @classmethod
    def get_boards(cls):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                                SELECT
                                    b.id,
                                    b.title,
                                    b.created_at,
                                    b.visits,
                                    b.active,
                                    b.is_pinned,
                                    m.name AS author,
                                    COUNT(r.id) AS report_count
                                FROM boards b
                                LEFT JOIN members m ON b.member_id = m.id
                                LEFT JOIN reports r ON r.board_id = b.id
                                GROUP BY b.id, b.title, b.created_at, b.visits, b.active, b.is_pinned, m.name
                                ORDER BY b.created_at DESC
                            """)
                return cursor.fetchall()
        except Exception as e:
            print(f"AdminService.get_boards() 오류발생 : {e}")
            return []
        finally:
            pass

    # 3시간 기준 신규 게시글 조회
    @classmethod
    def get_today_new_boards(cls, boards):
        since = datetime.now() - timedelta(hours=3)
        return len([m for m in boards if m['created_at'] >= since])

    @classmethod
    def set_board_active(cls, board_id, active):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE boards SET active=%s WHERE id=%s",
                    (active, board_id)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"set_board_active() 오류: {e}")
            conn.rollback()
            return False
        finally:
            pass

    @classmethod
    def delete_board_reports(cls, board_id):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM reports WHERE board_id=%s",
                    (board_id,)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"delete_board_reports() 오류: {e}")
            conn.rollback()
            return False
        finally:
            pass

    @classmethod
    def set_board_pinned(cls, board_id, is_pinned):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE boards SET is_pinned=%s WHERE id=%s",
                    (is_pinned, board_id)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"set_board_pinned() 오류: {e}")
            conn.rollback()
            return False
        finally:
            pass

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
        finally:
            pass

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

                # 신고 이유 조회
                board = cursor.fetchone()
                cursor.execute("""
                                SELECT reason FROM reports
                                WHERE board_id = %s
                            """, (board_id,))
                reports = cursor.fetchall()
                board['reports'] = [r['reason'] for r in reports] if reports else []
                return board
        except Exception as e:
            print(f"get_board_detail() 오류: {e}")
            return None
        finally:
            pass
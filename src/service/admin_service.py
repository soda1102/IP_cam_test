from flask import (
    Blueprint,
    request, session, flash,
    render_template, redirect, url_for
)

from datetime import datetime, timedelta

from src.common import (
    Session,
    fetch_query, execute_query,
    log_system
)
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
def dashboard():
    members = AdminService.get_members()
    new_members = AdminService.get_today_new_members(members)
    boards = AdminService.get_boards()
    new_boards = AdminService.get_today_new_boards(boards)
    return render_template('admin/admin.html',members=members, new_members=new_members, boards=boards, new_boards=new_boards)

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

    # 게시글 전체 조회
    @classmethod
    def get_boards(cls):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM boards")
                return cursor.fetchall()
        except Exception as e:
            print(f"AdminService.get_boards() 오류발생 : {e}")
            return []
        finally:
            conn.close()

    # 3시간 기준 신규 게시글 조회
    @classmethod
    def get_today_new_boards(cls, boards):
        since = datetime.now() - timedelta(hours=3)
        return len([m for m in boards if m['created_at'] >= since])


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
                cursor.execute("""
                                UPDATE members
                                SET active=0
                                WHERE id=%s
                            """, (member_id,))
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
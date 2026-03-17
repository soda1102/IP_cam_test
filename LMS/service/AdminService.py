from flask import Blueprint, render_template, request, flash, session, redirect, url_for
from LMS.common.session import Session
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
def dashboard():
    members = AdminService.get_members()
    new_members = AdminService.get_today_new_members(members)
    boards = AdminService.get_boards()
    new_boards = AdminService.get_today_new_boards(boards)
    return render_template('admin.html',members=members, new_members=new_members, boards=boards, new_boards=new_boards)

class AdminService:
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
            conn.close()

    @classmethod
    def get_today_new_members(cls, members):
        # 이미 넘어온 members 객체 재활용 → 쿼리 추가 없음
        since = datetime.now() - timedelta(hours=24)
        return len([m for m in members if m['created_at'] >= since])

    @classmethod
    def get_boards(cls):
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM boards")
                return cursor.fetchall()
        except:
            print("AdminService.get_boards() 오류발생....")
            return []
        finally:
            conn.close()

    @classmethod
    def get_today_new_boards(cls, boards):
        since = datetime.now() - timedelta(hours=3)
        return len([m for m in boards if m['created_at'] >= since])
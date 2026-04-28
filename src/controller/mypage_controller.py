# src/controller/mypage_controller.py
from flask import (
    Blueprint, request, session, flash,
    render_template, redirect, url_for,
    jsonify, make_response
)
from src.common import login_required
from src.service.mypage_service import MypageService

mypage_bp = Blueprint('mypage', __name__)
mypage_service = MypageService()


# ════════════════════════════════════════
# 마이페이지 메인 / 정보
# ════════════════════════════════════════

@mypage_bp.route('/')
@login_required
def mypage_info():
    try:
        data = mypage_service.get_member_info(session['user_id'])
        return render_template('mypage/info.html', **data)
    except ValueError as e:
        return f"<script>alert('{e}'); history.back();</script>"


@mypage_bp.route('/main')
@login_required
def mypage():
    try:
        data = mypage_service.get_mypage(session['user_id'])
        return render_template('mypage/info.html', **data)
    except ValueError as e:
        return f"<script>alert('{e}'); history.back();</script>"


# ════════════════════════════════════════
# 회원 정보 수정
# ════════════════════════════════════════

@mypage_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def member_edit():
    if request.method == 'GET':
        data = mypage_service.get_member_info(session['user_id'])
        return render_template('mypage/edit.html', **data)

    try:
        updated_session = mypage_service.edit_member(
            user_id     = session['user_id'],
            name        = request.form.get('name'),
            nickname    = request.form.get('nickname'),
            password    = request.form.get('password'),
            birth_year  = request.form.get('birth_year'),
            birth_month = request.form.get('birth_month'),
            birth_day   = request.form.get('birth_day'),
        )
        # 세션 갱신은 Controller 책임
        session.update(updated_session)
        return "<script>alert('수정 완료'); location.href='/mypage';</script>"
    except Exception as e:
        return f"<script>alert('수정 중 오류 발생: {e}'); history.back();</script>"


# ════════════════════════════════════════
# 프로필 이미지
# ════════════════════════════════════════

@mypage_bp.route('/profile/upload', methods=['POST'])
@login_required
def profile_upload():
    try:
        file_url = mypage_service.upload_profile_image(
            user_id = session['user_id'],
            file    = request.files.get('profile_img'),
        )
        session['user_profile'] = file_url      # 세션 즉시 갱신
        return "<script>alert('프로필 사진이 변경되었습니다.'); location.href='/mypage/';</script>"
    except ValueError as e:
        return f"<script>alert('{e}'); history.back();</script>"
    except RuntimeError as e:
        return f"<script>alert('{e}'); history.back();</script>"
    except Exception as e:
        return f"<script>alert('오류 발생: {e}'); history.back();</script>"


@mypage_bp.route('/profile/delete', methods=['POST'])
@login_required
def profile_delete():
    try:
        mypage_service.delete_profile_image(session['user_id'])
        session['user_profile'] = None          # 세션 즉시 갱신
        return "<script>alert('프로필 사진이 삭제되었습니다.'); location.href='/mypage/';</script>"
    except Exception as e:
        return f"<script>alert('삭제 중 오류 발생: {e}'); history.back();</script>"


# ════════════════════════════════════════
# 나의 활동
# ════════════════════════════════════════

@mypage_bp.route('/my_activity/')
@login_required
def my_activity():
    try:
        data = mypage_service.get_my_activity(
            user_id = session['user_id'],
            page    = request.args.get('page', 1, type=int),
        )
        return render_template('mypage/my_activity.html', **data)
    except ValueError as e:
        return f"<script>alert('{e}'); history.back();</script>"


@mypage_bp.route('/my_activity/unblock/<int:blocked_id>')
@login_required
def unblock_user(blocked_id):
    mypage_service.unblock_user(session['user_id'], blocked_id)
    return redirect(url_for('mypage.my_activity') + '#blocks')


# ════════════════════════════════════════
# 회원 탈퇴
# ════════════════════════════════════════

@mypage_bp.route('/delete_account', methods=['GET', 'POST'])
@login_required
def delete_account():
    try:
        mypage_service.delete_account(session['user_id'])
        session.clear()
        return """
            <script>
                alert('회원 탈퇴가 완료되었습니다.\\n그동안 이용해 주셔서 감사합니다.');
                location.href='/';
            </script>
        """
    except ValueError as e:
        return f"<script>alert('{e}'); history.back();</script>"
    except Exception as e:
        return f"<script>alert('탈퇴 처리 중 오류: {e}'); history.back();</script>"


# ════════════════════════════════════════
# AI 분석 결과
# ════════════════════════════════════════

@mypage_bp.route('/save_result', methods=['POST'])
@login_required
def save_result():
    user_id = session.get('user_id')
    file = request.files.get('merged_image')

    if not file or not user_id:
        return jsonify({'success': False, 'message': '로그인 정보 또는 파일이 없습니다.'}), 400

    try:
        boar_count       = int(request.form.get('boar_count', 0))
        water_deer_count = int(request.form.get('water_deer_count', 0))
        racoon_count     = int(request.form.get('racoon_count', 0))
    except (ValueError, TypeError):
        boar_count = water_deer_count = racoon_count = 0

    try:
        result_url = mypage_service.save_ai_result(
            user_id          = user_id,
            file             = file,
            original_filename= request.form.get('original_filename') or '무제_분석결과',
            boar_count       = boar_count,
            water_deer_count = water_deer_count,
            racoon_count     = racoon_count,
        )
        return jsonify({'success': True, 'url': result_url, 'message': '성공적으로 저장되었습니다!'})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except RuntimeError as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'서버 오류: {e}'}), 500


@mypage_bp.route('/ai_results')
@login_required
def ai_results():
    try:
        data = mypage_service.get_ai_results(
            user_id = session['user_id'],
            page    = request.args.get('page', 1, type=int),
        )
        # pagination 키 없이 data를 바로 넘김
        return render_template('mypage/ai_model.html', pagination=data)
    except Exception as e:
        return render_template('mypage/ai_model.html', pagination={
            'records': [], 'page': 1, 'total_pages': 1,
            'has_prev': False, 'has_next': False,
            'prev_num': 0, 'next_num': 2
        })


@mypage_bp.route('/download_report/<int:analysis_id>')
@login_required
def download_ai_report(analysis_id):
    try:
        result = mypage_service.get_ai_report(analysis_id, session['user_id'])

        response = make_response(result.to_report_text())
        response.headers['Content-Disposition'] = (
            f"attachment; filename*=UTF-8''{result.encoded_filename()}"
        )
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        return response

    except ValueError as e:
        return str(e), 404
    except PermissionError as e:
        return str(e), 403
    except Exception as e:
        return f"다운로드 중 오류가 발생했습니다: {e}", 500


@mypage_bp.route('/delete_ai_result/<int:analysis_id>', methods=['POST'])
@login_required
def delete_ai_result(analysis_id):
    try:
        mypage_service.delete_ai_result(analysis_id, session['user_id'])
        return jsonify({'success': True})
    except (ValueError, PermissionError) as e:
        return jsonify({'success': False, 'message': str(e)}), 403
    except Exception as e:
        return jsonify({'success': False, 'message': '삭제 중 오류가 발생했습니다.'}), 500
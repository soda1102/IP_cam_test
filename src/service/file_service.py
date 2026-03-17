from flask import (
    Blueprint,
    request, session, flash,
    render_template, redirect, url_for
)

from src.common import (
    fetch_query, execute_query, upload_file,
    log_system,
    login_required
)

file_bp = Blueprint('file', __name__)

@file_bp.route('/profile/upload', methods=['POST'])
@login_required
def profile_upload():
    if 'profile_img' not in request.files:
        return "<script>alert('파일이 없습니다.');history.back();</script>"

    file = request.files['profile_img']

    if file.filename == '':
        return "<script>alert('선택된 파일이 없습니다.');history.back();</script>"

    if file:
        try:
            file_url = upload_file(file, folder="profiles")
            if file_url:
                origin_name = file.filename
                save_name = file_url
                file_path = file_url
                # [4] DB 업데이트
                sql = "UPDATE members SET profile_img = %s WHERE id = %s"
                execute_query(sql, (file_path, session['user_id']))

                return "<script>alert('프로필 사진이 변경되었습니다.');location.href='/mypage';</script>"
        except Exception as e:
            # 어떤 에러인지 정확히 알기 위해 f-string 사용
            return f"<script>alert('오류 발생: {str(e)}');history.back();</script>"

    return "<script>alert('업로드 실패');history.back();</script>"


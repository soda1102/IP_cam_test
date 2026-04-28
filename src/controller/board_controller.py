# src/controller/board_controller.py
from flask import Blueprint, session, request, render_template, url_for, redirect, jsonify, Response, flash
from src.service.board_service import BoardService

board_bp = Blueprint('board', __name__)
board_service = BoardService()


# ════════════════════════════════════════
# 게시글 CRUD
# ════════════════════════════════════════

@board_bp.route('/write', methods=['GET', 'POST'])
def board_write():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'GET':
        current_category = request.args.get('category', 'free')
        is_admin = (session.get('user_role') == 'admin')
        return render_template('board/write.html',
                               is_admin=is_admin,
                               current_category=current_category)

    # POST
    try:
        board_id = board_service.create_board(
            member_id = session['user_id'],
            category  = request.form.get('category'),
            title     = request.form.get('title'),
            content   = request.form.get('content'),
            file      = request.files.get('file'),
        )
        return redirect(url_for('board.board_list',
                                category=request.form.get('category')))
    except ValueError as e:
        return _alert_back(str(e))
    except RuntimeError as e:
        return _alert_back(str(e))


@board_bp.route('/list', methods=['GET'])
def board_list():
    result = board_service.get_board_list(
        category    = request.args.get('category', 'free'),
        viewer_id   = session.get('user_id'),
        user_role   = session.get('user_role'),
        show_pinned = request.args.get('show_pinned', 'on') == 'on',
        search      = request.args.get('search', '').strip(),
        search_type = request.args.get('search_type', 'title'),
        sort        = request.args.get('sort', 'latest'),
        page        = request.args.get('page', 1, type=int),
        per_page    = request.args.get('per_page', 15, type=int),
    )

    return render_template('board/list.html',
                           **result,
                           category    = request.args.get('category', 'free'),
                           search      = request.args.get('search', ''),
                           search_type = request.args.get('search_type', 'title'),
                           sort        = request.args.get('sort', 'latest'),
                           per_page    = request.args.get('per_page', 15, type=int),
                           show_pinned = request.args.get('show_pinned', 'on'))


@board_bp.route('/view/<int:board_id>')
def board_view(board_id):
    try:
        data = board_service.get_board(
            board_id  = board_id,
            user_id   = session.get('user_id'),
            user_role = session.get('user_role'),
        )
        return render_template('board/view.html', **data)

    except ValueError:
        return _alert_back("존재하지 않는 게시글입니다.")
    except PermissionError as e:
        return _alert_back(str(e))


@board_bp.route('/edit/<int:board_id>', methods=['GET', 'POST'])
def board_edit(board_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'GET':
        # 수정 폼 진입 — 권한 확인은 Service에서
        try:
            board = board_service.get_board(board_id,
                                            user_id=session['user_id'],
                                            user_role=session.get('user_role'))
            return render_template('board/edit.html', board=board['board'])
        except (ValueError, PermissionError) as e:
            return _alert_back(str(e))

    # POST
    try:
        board_service.edit_board(
            board_id = board_id,
            user_id  = session['user_id'],
            title    = request.form.get('title'),
            content  = request.form.get('content'),
        )
        return redirect(url_for('board.board_view', board_id=board_id))
    except ValueError as e:
        return _alert_back(str(e))
    except PermissionError as e:
        return _alert_back(str(e))


@board_bp.route('/delete/<int:board_id>')
def board_delete(board_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    try:
        msg = board_service.delete_board(
            board_id  = board_id,
            user_id   = session['user_id'],
            user_role = session.get('user_role', ''),
        )
        return _alert_redirect(msg, '/board/list')
    except ValueError as e:
        return _alert_back(str(e))
    except PermissionError as e:
        return _alert_back(str(e))


# ════════════════════════════════════════
# 파일 다운로드
# ════════════════════════════════════════

@board_bp.route('/download/<int:file_id>')
def download_file(file_id):
    try:
        import requests as req
        file = board_service.get_file_for_download(file_id)

        response = req.get(file.file_path)
        return Response(
            response.content,
            headers={
                'Content-Disposition': f"attachment; filename={file.encoded_name()}; "
                                       f"filename*=UTF-8''{file.encoded_name()}",
                'Content-Type': response.headers.get(
                    'Content-Type', 'application/octet-stream'
                )
            }
        )
    except ValueError as e:
        return _alert_back(str(e))


# ════════════════════════════════════════
# 좋아요 / 싫어요
# ════════════════════════════════════════

@board_bp.route('/like/<int:board_id>', methods=['POST'])
def board_like_toggle(board_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        result = board_service.toggle_like(board_id, session['user_id'])
        return jsonify({'success': True, **result})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404


@board_bp.route('/dislike/<int:board_id>', methods=['POST'])
def board_dislike_toggle(board_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        result = board_service.toggle_dislike(board_id, session['user_id'])
        return jsonify({'success': True, **result})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404


# ════════════════════════════════════════
# 댓글
# ════════════════════════════════════════

@board_bp.route('/comment/<int:board_id>', methods=['POST'])
def add_comment(board_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    data = request.get_json()
    try:
        comment_id = board_service.add_comment(
            board_id  = board_id,
            member_id = session['user_id'],
            content   = data.get('content'),
            parent_id = data.get('parent_id'),
        )
        return jsonify({'success': True, 'comment_id': comment_id})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@board_bp.route('/comment/edit/<int:comment_id>', methods=['POST'])
def edit_comment(comment_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    data = request.get_json()
    try:
        board_service.edit_comment(
            comment_id = comment_id,
            user_id    = session['user_id'],
            content    = data.get('content'),
        )
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except PermissionError as e:
        return jsonify({'success': False, 'message': str(e)}), 403


@board_bp.route('/comment/delete/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        board_service.delete_comment(
            comment_id = comment_id,
            user_id    = session['user_id'],
            user_role  = session.get('user_role', ''),
        )
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except PermissionError as e:
        return jsonify({'success': False, 'message': str(e)}), 403


# ════════════════════════════════════════
# 신고
# ════════════════════════════════════════

@board_bp.route('/report', methods=['POST'])
def board_report():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    data        = request.get_json()
    report_type = data.get('type')
    target_id   = int(data.get('target_id'))
    reason      = data.get('reason')
    detail      = data.get('detail', '')

    try:
        if report_type == 'board':
            board_service.report_board(
                board_id    = target_id,
                reporter_id = session['user_id'],
                reason      = reason,
                detail      = detail,
            )
        elif report_type == 'comment':
            board_service.report_comment(
                comment_id  = target_id,
                reporter_id = session['user_id'],
                reason      = reason,
                detail      = detail,
            )
        else:
            return jsonify({'success': False, 'message': '잘못된 신고 유형입니다.'}), 400

        return jsonify({'success': True, 'message': '신고가 접수되었습니다.'})

    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except PermissionError as e:
        return jsonify({'success': False, 'message': str(e)}), 403

# ════════════════════════════════════════
# 스크랩
# ════════════════════════════════════════

@board_bp.route('/view/scrap/<int:board_id>', methods=['POST'])
def board_scrap_toggle(board_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        result = board_service.toggle_scrap(board_id, session['user_id'])
        return jsonify({'success': True, **result})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404


# ════════════════════════════════════════
# 에디터 이미지 업로드
# ════════════════════════════════════════

@board_bp.route('/upload/image', methods=['POST'])
def upload_image():
    try:
        url = board_service.upload_editor_image(request.files.get('file'))
        return jsonify({'url': url})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500


# ════════════════════════════════════════
# 휴지통
# ════════════════════════════════════════

@board_bp.route('/trash')
def board_trash():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    posts = board_service.get_trash(session['user_id'])
    return render_template('board/trash.html', posts=posts)


@board_bp.route('/restore/<int:board_id>')
def board_restore(board_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    try:
        board_service.restore_board(board_id, session['user_id'])
        flash("게시물이 성공적으로 복구되었습니다.")
        return redirect(url_for('mypage.my_activity'))
    except (ValueError, PermissionError) as e:
        return _alert_back(str(e))


@board_bp.route('/permanent_delete/<int:board_id>')
def board_permanent_delete(board_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    try:
        board_service.permanent_delete(board_id, session['user_id'])
        flash("게시물이 영구 삭제되었습니다.")
        return redirect(url_for('mypage.my_activity'))
    except (ValueError, PermissionError) as e:
        return _alert_back(str(e))


# ════════════════════════════════════════
# 프로필 / 팔로우
# ════════════════════════════════════════

@board_bp.route('/profile/<int:member_id>')
def user_profile(member_id):
    from src.service import profile_service
    viewer_id = session.get('user_id')
    data = profile_service.get_user_profile_data(member_id, viewer_id)

    if not data:
        return _alert_back("존재하지 않는 사용자입니다.")
    return render_template('board/profile.html', **data)


@board_bp.route('/follow/<int:following_id>', methods=['POST'])
def follow_toggle(following_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    from src.service import profile_service
    success, result = profile_service.toggle_follow(session['user_id'], following_id)

    if success:
        return jsonify({'success': True, 'is_following': result})
    return jsonify({'success': False, 'message': result})


# ════════════════════════════════════════
# Private 헬퍼 — HTTP 응답 패턴
# ════════════════════════════════════════

def _alert_back(message: str) -> str:
    """alert 후 이전 페이지로"""
    return f"<script>alert('{message}'); history.back();</script>"


def _alert_redirect(message: str, url: str) -> str:
    """alert 후 지정 URL로 이동"""
    return f"<script>alert('{message}'); location.href='{url}';</script>"
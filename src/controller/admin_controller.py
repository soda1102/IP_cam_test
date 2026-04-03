# src/controller/admin_controller.py
from flask import (
    Blueprint, request, session, flash,
    render_template, redirect, url_for, jsonify
)
from src.common import admin_required
from src.service.admin_service import AdminService

admin_bp    = Blueprint('admin', __name__)
admin_service = AdminService()


# ════════════════════════════════════════
# 대시보드
# ════════════════════════════════════════

@admin_bp.route('/')
@admin_required
def dashboard():
    ctx = admin_service.get_dashboard(
        user_role = session.get('user_role'),
        user_name = session.get('user_name'),
        user_img  = session.get('user_profile'),
    )
    return render_template('admin/dashboard.html', **ctx)


# ════════════════════════════════════════
# 회원 관리
# ════════════════════════════════════════

@admin_bp.route('/members')
@admin_required
def members():
    ctx = admin_service.get_members_page(
        search_q      = request.args.get('q', '').strip(),
        filter_role   = request.args.get('role', ''),
        filter_active = request.args.get('active', ''),
        page          = max(int(request.args.get('page', 1)), 1),
    )
    return render_template('admin/members.html', **ctx)


@admin_bp.route('/members/<int:member_id>/detail')
@admin_required
def member_detail(member_id):
    try:
        ctx = admin_service.get_member_detail_page(
            member_id = member_id,
            tab       = request.args.get('tab', 'boards'),
            page      = max(int(request.args.get('page', 1)), 1),
        )
        return render_template('admin/member_detail.html', **ctx)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.members'))


@admin_bp.route('/member/add', methods=['POST'])
@admin_required
def add_member():
    success = admin_service.add_member(
        uid       = request.form.get('uid'),
        name      = request.form.get('name'),
        nickname  = request.form.get('nickname'),
        password  = request.form.get('password'),
        birthdate = request.form.get('birthdate') or None,
    )
    flash('✅ 회원이 추가되었습니다.' if success else '❌ 추가 중 오류가 발생했습니다.',
          'success' if success else 'danger')
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.members'))


@admin_bp.route('/member/update/<int:member_id>', methods=['POST'])
@admin_required
def update_member(member_id):
    try:
        success = admin_service.update_member(
            member_id    = member_id,
            name         = request.form.get('name'),
            nickname     = request.form.get('nickname'),
            password     = request.form.get('password'),
            role         = request.form.get('role'),
            active       = request.form.get('active'),
            birthdate    = request.form.get('birthdate') or None,
            current_role = session.get('user_role'),
        )
        flash('✅ 회원 정보가 수정되었습니다.' if success else '❌ 수정 중 오류가 발생했습니다.',
              'success' if success else 'danger')
    except PermissionError as e:
        flash(str(e), 'danger')
        return ('', 403) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
               else redirect(url_for('admin.members'))

    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.members'))


@admin_bp.route('/member/delete/<int:member_id>', methods=['POST'])
@admin_required
def delete_member(member_id):
    success = admin_service.toggle_member_active(member_id)
    flash('✅ 변경되었습니다.' if success else '❌ 변경 중 오류가 발생했습니다.',
          'success' if success else 'danger')
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.members'))


# ════════════════════════════════════════
# 회원 상세 — 게시글 / 댓글 / 휴지통 액션
# ════════════════════════════════════════

@admin_bp.route('/members/<int:member_id>/board/<int:board_id>/delete', methods=['POST'])
@admin_required
def delete_member_board(member_id, board_id):
    admin_service.toggle_board_by_admin(board_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.member_detail', member_id=member_id, tab='boards'))


@admin_bp.route('/members/<int:member_id>/comment/<int:comment_id>/delete', methods=['POST'])
@admin_required
def delete_member_comment(member_id, comment_id):
    admin_service.toggle_comment_by_admin(comment_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.member_detail', member_id=member_id, tab='comments'))


@admin_bp.route('/members/<int:member_id>/trash/<int:board_id>/delete', methods=['POST'])
@admin_required
def delete_member_trash(member_id, board_id):
    admin_service.delete_board_permanent(board_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.member_detail', member_id=member_id, tab='trash'))


@admin_bp.route('/members/<int:member_id>/trash/<int:board_id>/restore', methods=['POST'])
@admin_required
def restore_member_trash(member_id, board_id):
    admin_service.restore_board_from_trash(board_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.member_detail', member_id=member_id, tab='trash'))

# ════════════════════════════════════════
# 게시글 관리
# ════════════════════════════════════════

@admin_bp.route('/posts')
@admin_required
def posts():
    ctx = admin_service.get_posts_page(
        search_q        = request.args.get('q', '').strip(),
        filter_category = request.args.get('category', ''),
        filter_type     = request.args.get('type', ''),
        filter_status   = request.args.get('status', ''),
        page            = max(int(request.args.get('page', 1)), 1),
    )
    return render_template('admin/posts.html', **ctx)


@admin_bp.route('/board/hide/<int:board_id>', methods=['POST'])
@admin_required
def hide_board(board_id):
    admin_service.hide_board(board_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))


@admin_bp.route('/board/restore/<int:board_id>', methods=['POST'])
@admin_required
def restore_board(board_id):
    admin_service.restore_board(board_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))


@admin_bp.route('/board/unreport/<int:board_id>', methods=['POST'])
@admin_required
def unreport_board(board_id):
    admin_service.unreport_board(board_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))


@admin_bp.route('/board/pin/<int:board_id>', methods=['POST'])
@admin_required
def pin_board(board_id):
    admin_service.pin_board(board_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))


@admin_bp.route('/board/unpin/<int:board_id>', methods=['POST'])
@admin_required
def unpin_board(board_id):
    admin_service.unpin_board(board_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))


@admin_bp.route('/board/update/<int:board_id>', methods=['POST'])
@admin_required
def update_board(board_id):
    admin_service.update_board(
        board_id = board_id,
        title    = request.form.get('title'),
        content  = request.form.get('content'),
    )
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.posts'))


@admin_bp.route('/board/detail/<int:board_id>')
@admin_required
def board_detail(board_id):
    try:
        board = admin_service.get_board_detail(board_id)
        return jsonify(board)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


# ════════════════════════════════════════
# AI 자료실
# ════════════════════════════════════════

@admin_bp.route('/files')
@admin_required
def files():
    ctx = admin_service.get_files_page()
    return render_template('admin/files.html', **ctx)


@admin_bp.route('/files/<int:user_id>')
@admin_required
def files_detail(user_id):
    try:
        ctx = admin_service.get_files_detail_page(
            user_id = user_id,
            page    = max(int(request.args.get('page', 1)), 1),
        )
        return render_template('admin/files_detail.html', **ctx)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.files'))

@admin_bp.route('/files/<int:file_id>/toggle', methods=['POST'])
@admin_required
def toggle_ai_file(file_id):
    admin_service.toggle_ai_file(file_id)
    return ('', 200) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           else redirect(url_for('admin.files'))

# ════════════════════════════════════════
# 통계 API
# ════════════════════════════════════════

@admin_bp.route('/api/visitors')
@admin_required
def visitor_stats():
    return jsonify(admin_service.get_visitor_stats())


@admin_bp.route('/api/ai_stats')
@admin_required
def ai_stats():
    return jsonify(admin_service.get_ai_stats())
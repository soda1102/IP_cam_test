# src/controller/profile_controller.py
from flask import Blueprint, request, session, render_template, jsonify
from src.service.profile_service import ProfileService

profile_bp = Blueprint('profile', __name__)
profile_service = ProfileService()


@profile_bp.route('/<int:member_id>')
def user_view(member_id):
    try:
        data = profile_service.get_profile(
            member_id    = member_id,
            viewer_id    = session.get('user_id'),
            post_page    = request.args.get('p_page', 1, type=int),
            comment_page = request.args.get('c_page', 1, type=int),
        )
        return render_template('mypage/profile.html', **data)
    except ValueError as e:
        return f"<script>alert('{e}'); history.back();</script>"


@profile_bp.route('/follow/<int:following_id>', methods=['POST'])
def follow_api(following_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        is_following = profile_service.toggle_follow(
            follower_id  = session['user_id'],
            following_id = following_id,
        )
        return jsonify({'success': True, 'is_following': is_following})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@profile_bp.route('/block/<int:blocked_id>', methods=['POST'])
def block_api(blocked_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        is_blocked = profile_service.toggle_block(
            blocker_id = session['user_id'],
            blocked_id = blocked_id,
        )
        return jsonify({'success': True, 'is_blocked': is_blocked})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
from flask import Blueprint, render_template, request, jsonify, url_for
from flask import session as flask_session  # DB 세션과 충돌 방지
from src.common.db import fetch_query, execute_query
from src.common import login_required  # 기존에 쓰시던 로그인 체크

# 1. 블루프린트 설정 (파일명은 service지만 역할은 Blueprint 포함)
profile_bp = Blueprint('profile', __name__)


# ---------------------------------------------------------
# [Route] 프로필 메인 페이지
# ---------------------------------------------------------
@profile_bp.route('/<int:member_id>')
def user_view(member_id):
    viewer_id = flask_session.get('user_id')

    # 1. 페이지네이션 파라미터 받기 (기본값 1)
    post_page = request.args.get('p_page', 1, type=int)
    comment_page = request.args.get('c_page', 1, type=int)
    per_page = 5  # 한 페이지당 보여줄 개수

    # 2. 유저 정보 조회 (기존과 동일)
    user_sql = "SELECT id, uid, name, nickname, profile_img, role, created_at FROM members WHERE id = %s"
    user_info = fetch_query(user_sql, (member_id,), one=True)

    if not user_info:
        return "<script>alert('존재하지 않는 사용자입니다.'); history.back();</script>"

    if not user_info.get('profile_img'):
        user_info['profile_img'] = url_for('static', filename='logo/the_road_library_logo.png')

    # 3. 작성한 게시물 페이징 처리
    post_offset = (post_page - 1) * per_page
    posts = fetch_query("""
        SELECT id, title, created_at FROM boards 
        WHERE member_id = %s AND active = 1 
        ORDER BY created_at DESC LIMIT %s OFFSET %s
    """, (member_id, per_page, post_offset))

    # 게시물 총 페이지 수 계산
    post_total = \
    fetch_query("SELECT COUNT(*) as cnt FROM boards WHERE member_id = %s AND active = 1", (member_id,), one=True)['cnt']
    p_total_pages = (post_total + per_page - 1) // per_page

    # 4. 작성한 댓글 페이징 처리
    comment_offset = (comment_page - 1) * per_page
    comments = fetch_query("""
        SELECT board_id, content, created_at FROM board_comments 
        WHERE member_id = %s 
        ORDER BY created_at DESC LIMIT %s OFFSET %s
    """, (member_id, per_page, comment_offset))

    # 댓글 총 페이지 수 계산
    comment_total = \
    fetch_query("SELECT COUNT(*) as cnt FROM board_comments WHERE member_id = %s", (member_id,), one=True)['cnt']
    c_total_pages = (comment_total + per_page - 1) // per_page

    # 5. 팔로우 상태 및 카운트 (기존과 동일)
    is_following = False
    if viewer_id:
        is_following = bool(
            fetch_query("SELECT 1 FROM follows WHERE follower_id = %s AND following_id = %s", (viewer_id, member_id),
                        one=True))

    follower_cnt = fetch_query("SELECT COUNT(*) as cnt FROM follows WHERE following_id = %s", (member_id,), one=True)[
        'cnt']
    following_cnt = fetch_query("SELECT COUNT(*) as cnt FROM follows WHERE follower_id = %s", (member_id,), one=True)[
        'cnt']

    # [user_view 함수 내부]
    is_blocked = False
    if viewer_id:
        # 로그인한 사람이 이 프로필 주인을 차단했는지 확인
        is_blocked = bool(fetch_query(
            "SELECT 1 FROM blocks WHERE blocker_id = %s AND blocked_id = %s",
            (viewer_id, member_id),
            one=True
        ))

    # 6. 템플릿으로 데이터 전송 (페이지 정보 추가됨)
    return render_template('mypage/profile.html',
                           user=user_info,
                           posts=posts, p_page=post_page, p_total=p_total_pages,
                           comments=comments, c_page=comment_page, c_total=c_total_pages,
                           is_following=is_following, is_blocked=is_blocked,
                           follower_count=follower_cnt, following_count=following_cnt)


# ---------------------------------------------------------
# [Route] 팔로우 토글 API
# ---------------------------------------------------------
@profile_bp.route('/follow/<int:following_id>', methods=['POST'])
def follow_api(following_id):
    """자바스크립트 fetch 요청을 받는 라우트"""
    follower_id = flask_session.get('user_id')
    if not follower_id:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    # 아래 정의된 toggle_follow를 호출
    success, result = toggle_follow(follower_id, following_id)
    return jsonify({'success': success, 'is_following': result})

@profile_bp.route('/follow/<int:following_id>', methods=['POST'])
def toggle_follow(follower_id, following_id):
    # 본인 팔로우 방지
    if int(follower_id) == int(following_id):
        return False, "자기 자신은 팔로우할 수 없습니다."

    # DB 상태 확인
    check_sql = "SELECT id FROM follows WHERE follower_id = %s AND following_id = %s"
    existing = fetch_query(check_sql, (follower_id, following_id), one=True)

    if existing:
        # 이미 팔로우 중이면 삭제
        execute_query("DELETE FROM follows WHERE id = %s", (existing['id'],))
        status = False
    else:
        # 팔로우 안 되어 있으면 추가
        execute_query("INSERT INTO follows (follower_id, following_id) VALUES (%s, %s)", (follower_id, following_id))
        status = True

    return True, status


# [Route] 차단 토글 API
@profile_bp.route('/block/<int:blocked_id>', methods=['POST'])
def block_api(blocked_id):
    blocker_id = flask_session.get('user_id')
    if not blocker_id:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    success, result = toggle_block(blocker_id, blocked_id)
    return jsonify({'success': success, 'is_blocked': result})

# [Service] 차단 토글 함수
@profile_bp.route('/block/<int:blocked_id>', methods=['POST'])
def toggle_block(blocker_id, blocked_id):
    if int(blocker_id) == int(blocked_id):
        return False, "자기 자신은 차단할 수 없습니다."

    # 이미 차단했는지 확인
    check_sql = "SELECT id FROM blocks WHERE blocker_id = %s AND blocked_id = %s"
    existing = fetch_query(check_sql, (blocker_id, blocked_id), one=True)

    if existing:
        # 차단 해제
        execute_query("DELETE FROM blocks WHERE id = %s", (existing['id'],))
        status = False
    else:
        # 차단 하기 (차단할 때 팔로우 관계가 있다면 끊어주는 게 좋음)
        execute_query(
            "DELETE FROM follows WHERE (follower_id = %s AND following_id = %s) OR (follower_id = %s AND following_id = %s)",
            (blocker_id, blocked_id, blocked_id, blocker_id))
        execute_query("INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s, %s)", (blocker_id, blocked_id))
        status = True

    return True, status
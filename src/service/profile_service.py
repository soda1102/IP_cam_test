# src/service/profile_service.py
from typing import Optional
from flask import url_for

from src.repository.profile_repository import ProfileRepository


class ProfileService:

    def __init__(self):
        self.profile_repo = ProfileRepository()

    # ════════════════════════════════════════
    # 프로필 조회
    # ════════════════════════════════════════

    def get_profile(
        self,
        member_id: int,
        viewer_id: Optional[int] = None,
        post_page: int = 1,
        comment_page: int = 1,
    ) -> dict:
        """
        프로필 페이지에 필요한 전체 데이터 반환
        - 유저 정보
        - 게시물 / 댓글 페이징
        - 팔로우 / 차단 상태
        """
        # 1. 유저 정보 조회
        user_info = self.profile_repo.find_profile_by_id(member_id)
        if not user_info:
            raise ValueError("존재하지 않는 사용자입니다.")

        # 2. 기본 프로필 이미지 처리
        if not user_info.get('profile_img'):
            user_info['profile_img'] = url_for(
                'static', filename='logo/the_road_library_logo.png'
            )

        # 3. 게시물 페이징
        posts, post_total = self.profile_repo.find_posts_by_member(
            member_id, post_page
        )
        p_total_pages = (post_total + 4) // 5  # per_page=5

        # 4. 댓글 페이징
        comments, comment_total = self.profile_repo.find_comments_by_member(
            member_id, comment_page
        )
        c_total_pages = (comment_total + 4) // 5  # per_page=5

        # 5. 팔로우 상태 + 카운트
        is_following = False
        is_blocked   = False

        if viewer_id:
            is_following = self.profile_repo.find_follow(viewer_id, member_id) is not None
            is_blocked   = self.profile_repo.find_block(viewer_id, member_id) is not None

        return {
            'user':           user_info,
            'posts':          posts,
            'p_page':         post_page,
            'p_total':        p_total_pages,
            'comments':       comments,
            'c_page':         comment_page,
            'c_total':        c_total_pages,
            'is_following':   is_following,
            'is_blocked':     is_blocked,
            'follower_count':  self.profile_repo.count_followers(member_id),
            'following_count': self.profile_repo.count_following(member_id),
        }

    # ════════════════════════════════════════
    # 팔로우 토글
    # ════════════════════════════════════════

    def toggle_follow(self, follower_id: int, following_id: int) -> bool:
        """
        팔로우 토글
        - 본인 팔로우 방지
        Returns: 토글 후 팔로우 상태 (True=팔로우, False=언팔로우)
        """
        if follower_id == following_id:
            raise ValueError("자기 자신은 팔로우할 수 없습니다.")

        existing = self.profile_repo.find_follow(follower_id, following_id)

        if existing:
            self.profile_repo.remove_follow(existing['id'])
            return False
        else:
            self.profile_repo.add_follow(follower_id, following_id)
            return True

    # ════════════════════════════════════════
    # 차단 토글
    # ════════════════════════════════════════

    def toggle_block(self, blocker_id: int, blocked_id: int) -> bool:
        """
        차단 토글
        - 본인 차단 방지
        - 차단 시 양방향 팔로우 관계 자동 해제
        Returns: 토글 후 차단 상태 (True=차단, False=차단 해제)
        """
        if blocker_id == blocked_id:
            raise ValueError("자기 자신은 차단할 수 없습니다.")

        existing = self.profile_repo.find_block(blocker_id, blocked_id)

        if existing:
            self.profile_repo.remove_block(existing['id'])
            return False
        else:
            # 차단 시 양방향 팔로우 관계 먼저 제거
            self.profile_repo.remove_follow_both(blocker_id, blocked_id)
            self.profile_repo.add_block(blocker_id, blocked_id)
            return True
# src/repository/profile_repository.py
from typing import Optional
from src.common.db import fetch_query, execute_query


class ProfileRepository:

    # ════════════════════════════════════════
    # 유저 정보
    # ════════════════════════════════════════

    def find_profile_by_id(self, member_id: int) -> Optional[dict]:
        """프로필 페이지용 유저 정보 조회 (민감 정보 제외)"""
        return fetch_query(
            "SELECT id, uid, name, nickname, profile_img, role, created_at "
            "FROM members WHERE id = %s",
            (member_id,), one=True
        )

    # ════════════════════════════════════════
    # 게시물 / 댓글
    # ════════════════════════════════════════

    def find_posts_by_member(
        self,
        member_id: int,
        page: int = 1,
        per_page: int = 5,
    ) -> tuple[list[dict], int]:
        """작성 게시물 페이징 조회 + 전체 개수"""
        offset = (page - 1) * per_page

        total_row = fetch_query(
            "SELECT COUNT(*) AS cnt FROM boards WHERE member_id = %s AND active = 1",
            (member_id,), one=True
        )
        total_count = total_row['cnt'] if total_row else 0

        rows = fetch_query(
            """
            SELECT id, title, created_at FROM boards
            WHERE member_id = %s AND active = 1
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (member_id, per_page, offset)
        )
        return rows, total_count

    def find_comments_by_member(
        self,
        member_id: int,
        page: int = 1,
        per_page: int = 5,
    ) -> tuple[list[dict], int]:
        """작성 댓글 페이징 조회 + 전체 개수"""
        offset = (page - 1) * per_page

        total_row = fetch_query(
            "SELECT COUNT(*) AS cnt FROM board_comments WHERE member_id = %s",
            (member_id,), one=True
        )
        total_count = total_row['cnt'] if total_row else 0

        rows = fetch_query(
            """
            SELECT board_id, content, created_at FROM board_comments
            WHERE member_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (member_id, per_page, offset)
        )
        return rows, total_count

    # ════════════════════════════════════════
    # 팔로우
    # ════════════════════════════════════════

    def find_follow(self, follower_id: int, following_id: int) -> Optional[dict]:
        return fetch_query(
            "SELECT id FROM follows WHERE follower_id = %s AND following_id = %s",
            (follower_id, following_id), one=True
        )

    def add_follow(self, follower_id: int, following_id: int):
        execute_query(
            "INSERT INTO follows (follower_id, following_id) VALUES (%s, %s)",
            (follower_id, following_id)
        )

    def remove_follow(self, follow_id: int):
        execute_query(
            "DELETE FROM follows WHERE id = %s",
            (follow_id,)
        )

    def remove_follow_both(self, member_a: int, member_b: int):
        """차단 시 양방향 팔로우 관계 일괄 제거"""
        execute_query(
            """
            DELETE FROM follows
            WHERE (follower_id = %s AND following_id = %s)
               OR (follower_id = %s AND following_id = %s)
            """,
            (member_a, member_b, member_b, member_a)
        )

    def count_followers(self, member_id: int) -> int:
        row = fetch_query(
            "SELECT COUNT(*) AS cnt FROM follows WHERE following_id = %s",
            (member_id,), one=True
        )
        return row['cnt'] if row else 0

    def count_following(self, member_id: int) -> int:
        row = fetch_query(
            "SELECT COUNT(*) AS cnt FROM follows WHERE follower_id = %s",
            (member_id,), one=True
        )
        return row['cnt'] if row else 0

    # ════════════════════════════════════════
    # 차단
    # ════════════════════════════════════════

    def find_block(self, blocker_id: int, blocked_id: int) -> Optional[dict]:
        return fetch_query(
            "SELECT id FROM blocks WHERE blocker_id = %s AND blocked_id = %s",
            (blocker_id, blocked_id), one=True
        )

    def add_block(self, blocker_id: int, blocked_id: int):
        execute_query(
            "INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s, %s)",
            (blocker_id, blocked_id)
        )

    def remove_block(self, block_id: int):
        execute_query(
            "DELETE FROM blocks WHERE id = %s",
            (block_id,)
        )
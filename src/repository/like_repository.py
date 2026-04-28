# src/repository/like_repository.py
from typing import Optional
from src.common.db import fetch_query, execute_query


class LikeRepository:

    # ────────────────────────────────────────
    # 좋아요
    # ────────────────────────────────────────
    def find_like(self, board_id: int, member_id: int) -> Optional[dict]:
        """좋아요 단건 조회 (존재 여부 확인용)"""
        return fetch_query(
            "SELECT id FROM board_likes WHERE board_id = %s AND member_id = %s",
            (board_id, member_id), one=True
        )

    def add_like(self, board_id: int, member_id: int):
        execute_query(
            "INSERT INTO board_likes (board_id, member_id) VALUES (%s, %s)",
            (board_id, member_id)
        )

    def remove_like(self, board_id: int, member_id: int):
        execute_query(
            "DELETE FROM board_likes WHERE board_id = %s AND member_id = %s",
            (board_id, member_id)
        )

    def count_likes(self, board_id: int) -> int:
        row = fetch_query(
            "SELECT COUNT(*) AS cnt FROM board_likes WHERE board_id = %s",
            (board_id,), one=True
        )
        return row['cnt'] if row else 0

    # ────────────────────────────────────────
    # 싫어요
    # ────────────────────────────────────────
    def find_dislike(self, board_id: int, member_id: int) -> Optional[dict]:
        """싫어요 단건 조회 (존재 여부 확인용)"""
        return fetch_query(
            "SELECT id FROM board_dislikes WHERE board_id = %s AND member_id = %s",
            (board_id, member_id), one=True
        )

    def add_dislike(self, board_id: int, member_id: int):
        execute_query(
            "INSERT INTO board_dislikes (board_id, member_id) VALUES (%s, %s)",
            (board_id, member_id)
        )

    def remove_dislike(self, board_id: int, member_id: int):
        execute_query(
            "DELETE FROM board_dislikes WHERE board_id = %s AND member_id = %s",
            (board_id, member_id)
        )

    def count_dislikes(self, board_id: int) -> int:
        row = fetch_query(
            "SELECT COUNT(*) AS cnt FROM board_dislikes WHERE board_id = %s",
            (board_id,), one=True
        )
        return row['cnt'] if row else 0

    # ────────────────────────────────────────
    # 좋아요 + 싫어요 동시 집계
    # ────────────────────────────────────────
    def count_both(self, board_id: int) -> dict:
        """
        좋아요/싫어요 둘 다 필요한 경우 쿼리 2번을 묶어서 호출
        Returns: {'like_count': int, 'dislike_count': int}
        """
        return {
            'like_count':    self.count_likes(board_id),
            'dislike_count': self.count_dislikes(board_id),
        }

    # ────────────────────────────────────────
    # 유저 반응 상태 조회 (상세보기 진입 시)
    # ────────────────────────────────────────
    def get_user_reaction(self, board_id: int, member_id: int) -> dict:
        """
        상세 페이지 최초 렌더링 시 유저의 현재 반응 상태 반환
        Returns: {'user_liked': bool, 'user_disliked': bool}
        """
        return {
            'user_liked':    self.find_like(board_id, member_id) is not None,
            'user_disliked': self.find_dislike(board_id, member_id) is not None,
        }
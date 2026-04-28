# src/repository/scrap_repository.py
from typing import Optional
from src.common.db import fetch_query, execute_query
from src.domain.scrap import Scrap


class ScrapRepository:

    # ────────────────────────────────────────
    # 단건 조회
    # ────────────────────────────────────────
    def find_by_board_and_member(
        self,
        board_id: int,
        member_id: int,
    ) -> Optional[Scrap]:
        """스크랩 존재 여부 확인용"""
        row = fetch_query(
            "SELECT * FROM board_scrap WHERE board_id = %s AND member_id = %s",
            (board_id, member_id), one=True
        )
        return Scrap.from_db(row) if row else None

    def find_by_member_id(self, member_id: int) -> list[Scrap]:
        """마이페이지 스크랩 목록 조회"""
        rows = fetch_query(
            """
            SELECT s.*, b.title AS board_title, b.category AS board_category,
                   b.created_at AS board_created_at, b.active AS board_active
            FROM board_scrap s
            JOIN boards b ON s.board_id = b.id
            WHERE s.member_id = %s
            ORDER BY s.created_at DESC
            """,
            (member_id,)
        )
        return [Scrap.from_db(row) for row in rows]

    def is_scrapped(self, board_id: int, member_id: int) -> bool:
        """스크랩 여부 (bool 바로 반환)"""
        return self.find_by_board_and_member(board_id, member_id) is not None

    # ────────────────────────────────────────
    # 집계
    # ────────────────────────────────────────
    def count_by_board_id(self, board_id: int) -> int:
        """게시글 스크랩 수"""
        row = fetch_query(
            "SELECT COUNT(*) AS cnt FROM board_scrap WHERE board_id = %s",
            (board_id,), one=True
        )
        return row['cnt'] if row else 0

    # ────────────────────────────────────────
    # 생성
    # ────────────────────────────────────────
    def create(self, board_id: int, member_id: int) -> int:
        """스크랩 INSERT 후 새 scrap_id 반환"""
        execute_query(
            "INSERT INTO board_scrap (board_id, member_id) VALUES (%s, %s)",
            (board_id, member_id)
        )
        row = fetch_query("SELECT LAST_INSERT_ID() AS new_id", one=True)
        return row['new_id'] if row else -1

    # ────────────────────────────────────────
    # 삭제
    # ────────────────────────────────────────
    def delete_by_board_and_member(self, board_id: int, member_id: int):
        """스크랩 취소"""
        execute_query(
            "DELETE FROM board_scrap WHERE board_id = %s AND member_id = %s",
            (board_id, member_id)
        )

    def delete_by_board_id(self, board_id: int):
        """게시글 hard delete 시 스크랩 일괄 삭제"""
        execute_query(
            "DELETE FROM board_scrap WHERE board_id = %s",
            (board_id,)
        )

    def delete_by_member_id(self, member_id: int):
        """회원 탈퇴 시 스크랩 일괄 삭제"""
        execute_query(
            "DELETE FROM board_scrap WHERE member_id = %s",
            (member_id,)
        )
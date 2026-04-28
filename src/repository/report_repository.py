# src/repository/report_repository.py
from typing import Optional
from src.common.db import fetch_query, execute_query
from src.domain.report import Report, ReportSummary


class ReportRepository:

    # ────────────────────────────────────────
    # 단건 조회
    # ────────────────────────────────────────
    def find_by_board_and_reporter(
        self,
        board_id: int,
        reporter_id: int,
    ) -> Optional[Report]:
        """중복 신고 확인용"""
        row = fetch_query(
            "SELECT * FROM reports WHERE board_id = %s AND reporter_id = %s",
            (board_id, reporter_id), one=True
        )
        return Report.from_db(row) if row else None

    def find_by_board_id(self, board_id: int) -> list[Report]:
        """게시글의 전체 신고 목록 (관리자 페이지용)"""
        rows = fetch_query(
            """
            SELECT r.*, m.nickname AS reporter_nickname
            FROM reports r
            JOIN members m ON r.reporter_id = m.id
            WHERE r.board_id = %s
            ORDER BY r.created_at DESC
            """,
            (board_id,)
        )
        return [Report.from_db(row) for row in rows]

    # ────────────────────────────────────────
    # 집계 조회
    # ────────────────────────────────────────
    def get_summary(self, board_id: int) -> ReportSummary:
        """
        게시글 신고 집계
        → board_view()의 차단 판단, board_list()의 서브쿼리 대체용
        """
        row = fetch_query(
            "SELECT COUNT(*) AS cnt FROM reports WHERE board_id = %s",
            (board_id,), one=True
        )
        count = row['cnt'] if row else 0
        return ReportSummary(board_id=board_id, count=count)

    def is_duplicate(self, board_id: int, reporter_id: int) -> bool:
        """중복 신고 여부 (bool 바로 반환)"""
        return self.find_by_board_and_reporter(board_id, reporter_id) is not None

    # ────────────────────────────────────────
    # 생성
    # ────────────────────────────────────────
    def create(self, board_id: int, reporter_id: int, reason: str, detail: str = '') -> int:
        execute_query(
            "INSERT INTO reports (board_id, reporter_id, reason, detail) VALUES (%s, %s, %s, %s)",
            (board_id, reporter_id, reason, detail)
        )
        row = fetch_query("SELECT LAST_INSERT_ID() AS new_id", one=True)
        return row['new_id'] if row else -1

    # ────────────────────────────────────────
    # 삭제
    # ────────────────────────────────────────
    def delete_by_id(self, report_id: int):
        """신고 단건 취소 (관리자용)"""
        execute_query(
            "DELETE FROM reports WHERE id = %s",
            (report_id,)
        )

    def delete_by_board_id(self, board_id: int):
        """게시글 hard delete 시 신고 내역 일괄 삭제"""
        execute_query(
            "DELETE FROM reports WHERE board_id = %s",
            (board_id,)
        )

    # ────────────────────────────────────────
    # 댓글 신고
    # ────────────────────────────────────────
    def is_duplicate_comment(self, comment_id: int, reporter_id: int) -> bool:
        row = fetch_query(
            "SELECT 1 FROM comment_report WHERE comment_id = %s AND reporter_id = %s",
            (comment_id, reporter_id), one=True
        )
        return row is not None

    def create_comment_report(self, comment_id: int, reporter_id: int, reason: str, detail: str = '') -> int:
        execute_query(
            "INSERT INTO comment_report (comment_id, reporter_id, reason, detail) VALUES (%s, %s, %s, %s)",
            (comment_id, reporter_id, reason, detail)
        )
        row = fetch_query("SELECT LAST_INSERT_ID() AS new_id", one=True)
        return row['new_id'] if row else -1

    def delete_by_comment_id(self, comment_id: int):
        """댓글 hard delete 시 신고 내역 일괄 삭제"""
        execute_query(
            "DELETE FROM comment_report WHERE comment_id = %s",
            (comment_id,)
        )
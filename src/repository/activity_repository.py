# src/repository/activity_repository.py
from math import ceil
from typing import Optional
from src.common.db import fetch_query, execute_query
from src.domain.ai_analysis import AIAnalysis


class ActivityRepository:

    # ════════════════════════════════════════
    # 활동 요약
    # ════════════════════════════════════════

    def get_board_summary(self, member_id: int) -> dict:
        """작성 게시물 수 + 신고된 게시물 수"""
        row = fetch_query(
            """
            SELECT
                COUNT(*) AS total_cnt,
                COUNT(CASE WHEN (SELECT COUNT(*) FROM reports
                                 WHERE board_id = b.id) >= 1
                           THEN 1 END) AS reported_cnt
            FROM boards b
            WHERE b.member_id = %s AND b.active = 1
            """,
            (member_id,), one=True
        )
        return {
            'board_count':    row['total_cnt']    if row else 0,
            'reported_count': row['reported_cnt'] if row else 0,
        }

    # ════════════════════════════════════════
    # 작성 게시물
    # ════════════════════════════════════════

    def find_my_posts(
        self,
        member_id: int,
        page: int = 1,
        per_page: int = 10,
    ) -> tuple[list[dict], int]:
        """작성 게시물 목록 + 전체 개수"""
        offset = (page - 1) * per_page

        total_row = fetch_query(
            "SELECT COUNT(*) AS cnt FROM boards WHERE member_id = %s AND active = 1",
            (member_id,), one=True
        )
        total_count = total_row['cnt'] if total_row else 0

        rows = fetch_query(
            """
            SELECT * FROM boards
            WHERE member_id = %s AND active = 1
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (member_id, per_page, offset)
        )
        return rows, total_count

    # ════════════════════════════════════════
    # 좋아요 / 스크랩 / 댓글 / 휴지통 / 차단
    # ════════════════════════════════════════

    def find_my_likes(self, member_id: int) -> list[dict]:
        return fetch_query(
            """
            SELECT b.*, m.name AS writer_name
            FROM board_likes bl
            JOIN boards b  ON bl.board_id  = b.id
            JOIN members m ON b.member_id  = m.id
            WHERE bl.member_id = %s
            """,
            (member_id,)
        )

    def find_my_scraps(self, member_id: int) -> list[dict]:
        return fetch_query(
            """
            SELECT b.*, bs.created_at AS scrap_date
            FROM board_scrap bs
            JOIN boards b ON bs.board_id = b.id
            WHERE bs.member_id = %s
            """,
            (member_id,)
        )

    def find_my_comments(self, member_id: int) -> list[dict]:
        return fetch_query(
            """
            SELECT c.*, b.title AS board_title
            FROM board_comments c
            JOIN boards b ON c.board_id = b.id
            WHERE c.member_id = %s
            ORDER BY c.created_at DESC
            """,
            (member_id,)
        )

    def find_my_trash(self, member_id: int) -> list[dict]:
        return fetch_query(
            """
            SELECT *,
                   DATEDIFF(DATE_ADD(deleted_at, INTERVAL 30 DAY), NOW()) AS remaining_days
            FROM boards
            WHERE member_id = %s AND active = 0 AND deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
            """,
            (member_id,)
        )

    def find_my_blocks(self, member_id: int) -> list[dict]:
        return fetch_query(
            """
            SELECT b.*, m.name AS blocked_name
            FROM blocks b
            JOIN members m ON b.blocked_id = m.id
            WHERE b.blocker_id = %s
            ORDER BY b.created_at DESC
            """,
            (member_id,)
        )

    def unblock(self, blocker_id: int, blocked_id: int):
        execute_query(
            "DELETE FROM blocks WHERE blocker_id = %s AND blocked_id = %s",
            (blocker_id, blocked_id)
        )

    # ════════════════════════════════════════
    # AI 분석 결과
    # ════════════════════════════════════════

    def find_ai_results(
        self,
        user_id: int,
        page: int = 1,
        per_page: int = 5,
    ) -> tuple[list[AIAnalysis], int]:
        """AI 분석 결과 목록 + 전체 개수"""
        offset = (page - 1) * per_page

        total_row = fetch_query(
            "SELECT COUNT(*) AS cnt FROM ai_analysis WHERE user_id = %s",
            (user_id,), one=True
        )
        total_count = total_row['cnt'] if total_row else 0

        rows = fetch_query(
            """
            SELECT id, filename, boar_count, water_deer_count, racoon_count, created_at
            FROM ai_analysis
            WHERE user_id = %s AND active = 1
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, per_page, offset)
        )
        # user_id, image_url 없이 조회했으므로 직접 매핑
        items = [
            AIAnalysis(
                id=row['id'],
                user_id=user_id,
                filename=row.get('filename') or '무제_분석결과',
                image_url='',
                boar_count=row.get('boar_count', 0),
                water_deer_count=row.get('water_deer_count', 0),
                racoon_count=row.get('racoon_count', 0),
                created_at=row.get('created_at'),
            )
            for row in rows
        ]
        return items, total_count

    def find_ai_result_by_id(self, analysis_id: int) -> Optional[AIAnalysis]:
        """AI 분석 결과 단건 조회"""
        row = fetch_query(
            "SELECT * FROM ai_analysis WHERE id = %s",
            (analysis_id,), one=True
        )
        return AIAnalysis.from_db(row) if row else None

    def create_ai_result(
        self,
        user_id: int,
        filename: str,
        image_url: str,
        boar_count: int,
        water_deer_count: int,
        racoon_count: int,
    ):
        execute_query(
            """
            INSERT INTO ai_analysis
            (user_id, filename, image_url, boar_count, water_deer_count, racoon_count, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """,
            (user_id, filename, image_url, boar_count, water_deer_count, racoon_count)
        )

    def delete_ai_result(self, analysis_id: int, user_id: int):
        """본인 데이터만 비활성화"""
        execute_query(
            "UPDATE ai_analysis SET active = 0 WHERE id = %s AND user_id = %s",
            (analysis_id, user_id)
        )
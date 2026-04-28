# src/repository/board_repository.py
from math import ceil
from typing import Optional
from src.common.db import fetch_query, execute_query
from src.domain.Board import Board


class BoardRepository:

    # ────────────────────────────────────────
    # 단건 조회
    # ────────────────────────────────────────
    def find_by_id(self, board_id: int) -> Optional[Board]:
        """게시글 단건 조회 (작성자 조인 + 신고 수 포함)"""
        sql = """
            SELECT b.*,
                   m.nickname AS writer_nickname,
                   m.name     AS writer_name,
                   m.uid      AS writer_uid,
                   m.profile_img AS writer_profile,
                   (SELECT COUNT(*) FROM reports WHERE board_id = b.id) AS report_count
            FROM boards b
            JOIN members m ON b.member_id = m.id
            WHERE b.id = %s
        """
        row = fetch_query(sql, (board_id,), one=True)
        if not row:
            return None

        board = Board.from_db(row)
        board.report_count   = row['report_count']
        board.writer_nickname = row['writer_nickname']
        board.writer_name    = row['writer_name']
        board.writer_uid     = row['writer_uid']
        board.writer_profile = row['writer_profile']
        return board

    def find_raw_by_id(self, board_id: int) -> Optional[dict]:
        """수정/삭제 권한 확인용 — Board 객체 없이 dict 그대로 반환"""
        return fetch_query(
            "SELECT * FROM boards WHERE id = %s",
            (board_id,), one=True
        )

    # ────────────────────────────────────────
    # 목록 조회
    # ────────────────────────────────────────
    def find_list(
        self,
        category: str,
        viewer_id: Optional[int] = None,
        show_pinned: bool = True,
        search: str = '',
        search_type: str = 'title',
        sort: str = 'latest',
        page: int = 1,
        per_page: int = 15,
        is_admin: bool = False,
    ) -> tuple[list[Board], int]:
        """
        게시글 목록 조회
        Returns: (boards, total_count)
        """
        where_clauses, query_args = self._build_where(
            category, viewer_id, show_pinned, search, search_type, is_admin
        )
        where_sql = " WHERE " + " AND ".join(where_clauses)
        order_sql = self._build_order(sort)
        offset    = (page - 1) * per_page

        # 전체 개수
        count_row = fetch_query(
            f"SELECT COUNT(*) AS cnt FROM boards b {where_sql}",
            tuple(query_args), one=True
        )
        total_count = count_row['cnt'] if count_row else 0

        # 실제 데이터
        sql = f"""
            SELECT b.*,
                   m.name     AS writer_name,
                   m.nickname AS writer_nickname,
                   (SELECT COUNT(*) FROM board_likes    WHERE board_id = b.id) AS like_count,
                   (SELECT COUNT(*) FROM board_comments WHERE board_id = b.id) AS comment_count,
                   (SELECT COUNT(*) FROM files          WHERE board_id = b.id) AS file_count
            FROM boards b
            JOIN members m ON b.member_id = m.id
            {where_sql}
            {order_sql}
            LIMIT %s OFFSET %s
        """
        rows = fetch_query(sql, tuple(query_args + [per_page, offset]))

        boards = []
        for row in rows:
            board = Board.from_db(row)
            board.like_count      = row['like_count']
            board.comment_count   = row['comment_count']
            board.file_count      = row['file_count']
            board.writer_name     = row['writer_name']
            board.writer_nickname = row['writer_nickname']
            boards.append(board)

        return boards, total_count

    # ────────────────────────────────────────
    # 휴지통 목록
    # ────────────────────────────────────────
    def find_trash_by_member(self, member_id: int) -> list[dict]:
        """삭제된 지 30일 이내 게시물 조회 (남은 일수 포함)"""
        sql = """
            SELECT *,
                   DATEDIFF(DATE_ADD(deleted_at, INTERVAL 30 DAY), NOW()) AS remaining_days
            FROM boards
            WHERE member_id = %s
              AND active = 0
              AND deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
        """
        return fetch_query(sql, (member_id,))

    # ────────────────────────────────────────
    # 생성
    # ────────────────────────────────────────
    def create(
        self,
        member_id: int,
        category: str,
        title: str,
        content: str,
    ) -> int:
        """INSERT 후 새 board_id 반환"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO boards (member_id, category, title, content) VALUES (%s, %s, %s, %s)",
                    (member_id, category, title, content)
                )
                new_id = cursor.lastrowid
            conn.commit()
            return new_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ────────────────────────────────────────
    # 수정
    # ────────────────────────────────────────
    def update(self, board_id: int, title: str, content: str):
        execute_query(
            "UPDATE boards SET title = %s, content = %s WHERE id = %s",
            (title, content, board_id)
        )

    def increment_visits(self, board_id: int):
        execute_query(
            "UPDATE boards SET visits = visits + 1 WHERE id = %s",
            (board_id,)
        )

    # ────────────────────────────────────────
    # 삭제
    # ────────────────────────────────────────
    def soft_delete(self, board_id: int):
        """휴지통으로 이동 (active=0)"""
        execute_query(
            "UPDATE boards SET active = 0, deleted_at = NOW() WHERE id = %s",
            (board_id,)
        )

    def restore(self, board_id: int):
        """휴지통에서 복구 (active=1)"""
        execute_query(
            "UPDATE boards SET active = 1, deleted_at = NULL WHERE id = %s",
            (board_id,)
        )

    def hard_delete(self, board_id: int):
        """영구 삭제"""
        execute_query("DELETE FROM boards WHERE id = %s", (board_id,))

    def cleanup_expired_trash(self):
        """30일 지난 휴지통 게시물 자동 영구 삭제 (스케줄러용)"""
        execute_query("""
            DELETE FROM boards
            WHERE active = 0
              AND deleted_at IS NOT NULL
              AND deleted_at < NOW() - INTERVAL 30 DAY
        """)

    # ────────────────────────────────────────
    # Private 헬퍼
    # ────────────────────────────────────────
    def _build_where(
        self,
        category: str,
        viewer_id: Optional[int],
        show_pinned: bool,
        search: str,
        search_type: str,
        is_admin: bool,
    ) -> tuple[list[str], list]:

        clauses = [] if is_admin else ["b.active = 1"]
        args    = []

        # 카테고리 (공지글은 카테고리 무관 표시)
        clauses.append("(b.category = %s OR b.is_pinned = 1)")
        args.append(category)

        # 차단 유저 필터
        if viewer_id:
            clauses.append(
                "b.member_id NOT IN (SELECT blocked_id FROM blocks WHERE blocker_id = %s)"
            )
            args.append(viewer_id)

        # 공지글 숨김
        if not show_pinned:
            clauses.append("b.is_pinned = 0")

        # 검색
        if search:
            if search_type == 'title':
                clauses.append("b.title LIKE %s")
                args.append(f"%{search}%")
            elif search_type == 'content':
                clauses.append("b.content LIKE %s")
                args.append(f"%{search}%")
            elif search_type == 'all':
                clauses.append("(b.title LIKE %s OR b.content LIKE %s)")
                args.extend([f"%{search}%", f"%{search}%"])

        return clauses, args

    def _build_order(self, sort: str) -> str:
        if sort == 'popular':
            return "ORDER BY b.is_pinned DESC, like_count DESC, b.created_at DESC"
        return "ORDER BY b.is_pinned DESC, b.created_at DESC"

    @staticmethod
    def _get_conn():
        from src.common import Session
        return Session.get_connection()
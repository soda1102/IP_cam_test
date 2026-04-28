# src/repository/comment_repository.py
from typing import Optional
from src.common.db import fetch_query, execute_query
from src.domain.comment import Comment


class CommentRepository:

    # ────────────────────────────────────────
    # 단건 조회
    # ────────────────────────────────────────
    def find_by_id(self, comment_id: int) -> Optional[Comment]:
        row = fetch_query(
            "SELECT * FROM board_comments WHERE id = %s",
            (comment_id,), one=True
        )
        return Comment.from_db(row) if row else None

    # ────────────────────────────────────────
    # 목록 조회
    # ────────────────────────────────────────
    def find_by_board_id(
        self,
        board_id: int,
        viewer_id: Optional[int] = None,
    ) -> list[dict]:
        """
        [upstream 반영]
        - active, deleted_at 컬럼 추가
        - active = 0 이면 content를 '삭제된 댓글입니다.'로 CASE WHEN 처리
        """
        if viewer_id:
            sql = """
                SELECT c.id, c.board_id, c.member_id, c.parent_id,
                       c.active, c.created_at, c.deleted_at,
                       CASE WHEN c.active = 0
                            THEN '삭제된 댓글입니다.'
                            ELSE c.content
                       END AS content,
                       m.name     AS writer_name,
                       m.nickname AS writer_nickname,
                       m.uid      AS writer_uid,
                       (SELECT COUNT(*) FROM blocks
                        WHERE blocker_id = %s
                          AND blocked_id = c.member_id) AS is_blocked
                FROM board_comments c
                JOIN members m ON c.member_id = m.id
                WHERE c.board_id = %s
                ORDER BY c.created_at ASC
            """
            return fetch_query(sql, (viewer_id, board_id))
        else:
            sql = """
                SELECT c.id, c.board_id, c.member_id, c.parent_id,
                       c.active, c.created_at, c.deleted_at,
                       CASE WHEN c.active = 0
                            THEN '삭제된 댓글입니다.'
                            ELSE c.content
                       END AS content,
                       m.name     AS writer_name,
                       m.nickname AS writer_nickname,
                       m.uid      AS writer_uid,
                       0 AS is_blocked
                FROM board_comments c
                JOIN members m ON c.member_id = m.id
                WHERE c.board_id = %s
                ORDER BY c.created_at ASC
            """
            return fetch_query(sql, (board_id,))

    # ────────────────────────────────────────
    # 생성
    # ────────────────────────────────────────
    def create(
        self,
        board_id: int,
        member_id: int,
        content: str,
        parent_id: Optional[int] = None,
    ) -> int:
        execute_query(
            "INSERT INTO board_comments (board_id, member_id, parent_id, content) VALUES (%s, %s, %s, %s)",
            (board_id, member_id, parent_id, content)
        )
        row = fetch_query("SELECT LAST_INSERT_ID() AS new_id", one=True)
        return row['new_id'] if row else -1

    # ────────────────────────────────────────
    # 수정
    # ────────────────────────────────────────
    def update(self, comment_id: int, content: str):
        execute_query(
            "UPDATE board_comments SET content = %s WHERE id = %s",
            (content, comment_id)
        )

    # ────────────────────────────────────────
    # 삭제
    # ────────────────────────────────────────
    def soft_delete(self, comment_id: int):
        """
        [upstream 반영]
        content 교체 방식 → active = 0, deleted_at = NOW() 방식으로 변경
        조회 시 CASE WHEN으로 '삭제된 댓글입니다.' 처리하므로 content 건드리지 않음
        """
        execute_query(
            "UPDATE board_comments SET active = 0, deleted_at = NOW() WHERE id = %s",
            (comment_id,)
        )

    # ────────────────────────────────────────
    # 트리 조립
    # ────────────────────────────────────────
    @staticmethod
    def build_comment_tree(flat_comments: list[dict]) -> list[dict]:
        comment_dict = {c['id']: {**c, 'children': []} for c in flat_comments}
        root_comments = []

        for c_id, c_data in comment_dict.items():
            parent_id = c_data['parent_id']
            if parent_id and parent_id in comment_dict:
                comment_dict[parent_id]['children'].append(c_data)
            else:
                root_comments.append(c_data)

        return root_comments
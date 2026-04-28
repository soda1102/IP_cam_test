# src/domain/comment.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Comment:
    # ── PK / FK ──────────────────────────────
    id: int
    board_id: int
    member_id: int

    # ── 본문 ─────────────────────────────────
    content: str
    parent_id: Optional[int] = None

    # ── 상태 [upstream 반영: active + deleted_at 추가] ──
    active: bool = True
    deleted_at: Optional[datetime] = None

    # ── 시간 ─────────────────────────────────
    created_at: Optional[datetime] = None

    # ── 조인 결과 (DB 컬럼 아님) ──────────────
    writer_name: Optional[str] = None
    writer_nickname: Optional[str] = None
    writer_uid: Optional[str] = None
    is_blocked: bool = False

    # ────────────────────────────────────────
    # Factory
    # ────────────────────────────────────────
    @classmethod
    def from_db(cls, row: dict) -> "Comment":
        return cls(
            id=row['id'],
            board_id=row['board_id'],
            member_id=row['member_id'],
            content=row['content'],
            parent_id=row.get('parent_id'),
            # [upstream 반영]
            active=bool(row.get('active', 1)),
            deleted_at=row.get('deleted_at'),
            created_at=row.get('created_at'),
            writer_name=row.get('writer_name'),
            writer_nickname=row.get('writer_nickname'),
            writer_uid=row.get('writer_uid'),
            is_blocked=bool(row.get('is_blocked', 0)),
        )

    # ────────────────────────────────────────
    # 비즈니스 규칙
    # ────────────────────────────────────────
    def is_reply(self) -> bool:
        return self.parent_id is not None

    def is_deleted(self) -> bool:
        """
        [upstream 반영]
        content 문자열 비교 → active 컬럼 기준으로 변경
        """
        return not self.active and self.deleted_at is not None

    def can_be_edited_by(self, user_id: int) -> bool:
        return self.member_id == user_id

    def can_be_deleted_by(self, user_id: int, user_role: str) -> bool:
        return user_role == 'admin' or self.member_id == user_id
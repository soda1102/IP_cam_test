# src/domain/scrap.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Scrap:
    # ── PK / FK ──────────────────────────────
    id: int
    board_id: int
    member_id: int

    # ── 시간 ─────────────────────────────────
    created_at: Optional[datetime] = None

    # ── 조인 결과 (DB 컬럼 아님) ──────────────
    board_title: Optional[str] = None
    board_category: Optional[str] = None
    board_created_at: Optional[datetime] = None
    board_active: bool = True           # 원본 게시글 활성 여부

    # ────────────────────────────────────────
    # Factory
    # ────────────────────────────────────────
    @classmethod
    def from_db(cls, row: dict) -> "Scrap":
        return cls(
            id=row['id'],
            board_id=row['board_id'],
            member_id=row['member_id'],
            created_at=row.get('created_at'),
            board_title=row.get('board_title'),
            board_category=row.get('board_category'),
            board_created_at=row.get('board_created_at'),
            board_active=bool(row.get('board_active', 1)),
        )

    # ────────────────────────────────────────
    # 비즈니스 규칙
    # ────────────────────────────────────────
    def is_origin_deleted(self) -> bool:
        """원본 게시글이 삭제(휴지통)된 스크랩인지"""
        return not self.board_active

    def is_owner(self, member_id: int) -> bool:
        """스크랩 소유자 확인"""
        return self.member_id == member_id
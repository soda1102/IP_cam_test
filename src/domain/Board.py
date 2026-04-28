from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.domain.report import REPORT_BLOCK_THRESHOLD

@dataclass
class Board:
    id: int
    member_id: int
    category: str # default : free
    title: str
    content: str
    visits: int = 0 # DB default : 0
    active: bool = True # DB default : 1
    is_pinned: bool = False # DB default : 0
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    writer_nickname: Optional[str] = None
    writer_name: Optional[str] = None
    writer_uid: Optional[str] = None
    writer_profile: Optional[str] = None
    like_count: int = 0
    dislike_count: int = 0
    comment_count: int = 0
    file_count: int = 0
    report_count: int = 0

    @classmethod
    def from_db(cls, row: dict) -> "Board":
        """fetch_query 결과 dict → Board 객체"""
        return cls(
            id=row['id'],
            member_id=row['member_id'],
            category=row.get('category', 'free'),
            title=row['title'],
            content=row['content'],
            visits=row.get('visits', 0),
            active=bool(row.get('active', 1)),
            is_pinned=bool(row.get('is_pinned', 0)),
            created_at=row.get('created_at'),
            deleted_at=row.get('deleted_at'),
        )

    def can_be_edited_by(self, user_id: int, user_role: str) -> bool:
        """수정은 본인만 가능 (관리자도 타인 글 수정 불가)"""
        return self.member_id == user_id

    def can_be_deleted_by(self, user_id: int, user_role: str) -> bool:
        """삭제는 본인 또는 관리자"""
        return user_role == 'admin' or self.member_id == user_id

    def is_soft_deleted(self) -> bool:
        """휴지통에 있는 글인지"""
        return not self.active and self.deleted_at is not None

    def is_blocked_by_reports(self) -> bool:
        """신고 5개 이상이면 일반 유저에게 차단"""
        return self.report_count >= REPORT_BLOCK_THRESHOLD

    def days_until_permanent_delete(self) -> Optional[int]:
        """휴지통 진입 후 영구 삭제까지 남은 일수 (deleted_at 기준)"""
        if self.deleted_at is None:
            return None
        from datetime import timezone
        now = datetime.now()
        delta = (self.deleted_at - now).days + 30
        return max(delta, 0)
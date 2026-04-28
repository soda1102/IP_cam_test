from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class ReportReason:
    SPAM     = '부적절한 홍보 게시글'
    OBSCENE  = '음란성 내용'
    DEFAME   = '명예훼손/저작권 침해'
    ABUSE    = '욕설 및 비하 발언'
    OTHER    = '기타'

    _VALID = {SPAM, OBSCENE, DEFAME, ABUSE, OTHER}

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls._VALID

    @classmethod
    def label(cls, value: str) -> str:
        return {
            cls.SPAM:    '부적절한 홍보 게시글',
            cls.OBSCENE: '음란성 내용',
            cls.DEFAME:  '명예훼손/저작권 침해',
            cls.ABUSE:   '욕설 및 비하 발언',
            cls.OTHER:   '기타',
        }.get(value, '알 수 없음')

@dataclass
class Report:
    id: int
    board_id: int
    reporter_id: int          # 신고한 사람 (members.id)
    reason: str               # ReportReason 상수값
    created_at: Optional[datetime] = None

    @classmethod
    def from_db(cls, row: dict) -> "Report":
        return cls(
            id=row['id'],
            board_id=row['board_id'],
            reporter_id=row['reporter_id'],
            reason=row.get('reason', ReportReason.OTHER),
            created_at=row.get('created_at'),
        )

    def is_self_report(self, board_owner_id: int) -> bool:
        """본인 글 신고 여부"""
        return self.reporter_id == board_owner_id

    def has_valid_reason(self) -> bool:
        """유효한 신고 사유인지"""
        return ReportReason.is_valid(self.reason)

    def reason_label(self) -> str:
        """신고 사유 한국어 라벨"""
        return ReportReason.label(self.reason)


REPORT_BLOCK_THRESHOLD = 5  # 이 숫자 이상이면 게시글 차단

@dataclass(frozen=True)
class ReportSummary:
    board_id: int
    count: int

    def is_blocked(self) -> bool:
        """게시글 차단 임계값 초과 여부"""
        return self.count >= REPORT_BLOCK_THRESHOLD

    def remaining_until_block(self) -> int:
        """차단까지 남은 신고 수"""
        return max(REPORT_BLOCK_THRESHOLD - self.count, 0)
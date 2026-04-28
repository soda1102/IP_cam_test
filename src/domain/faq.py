# src/domain/faq.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class FAQ:
    # ── PK ───────────────────────────────────
    id: int

    # ── 본문 ─────────────────────────────────
    question: str
    answer: str
    category: str = 'general'   # 'general' | 'account' | 'payment' 등

    # ── 상태 ─────────────────────────────────
    active: bool = True
    order: int = 0              # 노출 순서

    # ────────────────────────────────────────
    # Factory
    # ────────────────────────────────────────
    @classmethod
    def from_db(cls, row: dict) -> "FAQ":
        return cls(
            id=row['id'],
            question=row['question'],
            answer=row['answer'],
            category=row.get('category', 'general'),
            active=bool(row.get('active', 1)),
            order=row.get('order', 0),
        )

    # ────────────────────────────────────────
    # 비즈니스 규칙
    # ────────────────────────────────────────
    def is_visible(self) -> bool:
        """노출 가능한 FAQ 여부"""
        return self.active
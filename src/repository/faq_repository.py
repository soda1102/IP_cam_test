# src/repository/faq_repository.py
from typing import Optional
from src.common.db import fetch_query, execute_query
from src.domain.faq import FAQ


class FAQRepository:

    # ────────────────────────────────────────
    # 목록 조회
    # ────────────────────────────────────────
    def find_all_active(self) -> list[FAQ]:
        """노출 가능한 전체 FAQ 조회 (순서 정렬)"""
        rows = fetch_query(
            """
            SELECT * FROM faqs
            WHERE active = 1
            ORDER BY `order` ASC, id ASC
            """
        )
        return [FAQ.from_db(row) for row in rows]

    def find_by_category(self, category: str) -> list[FAQ]:
        """카테고리별 FAQ 조회"""
        rows = fetch_query(
            """
            SELECT * FROM faqs
            WHERE active = 1 AND category = %s
            ORDER BY `order` ASC, id ASC
            """,
            (category,)
        )
        return [FAQ.from_db(row) for row in rows]

    # ────────────────────────────────────────
    # 단건 조회
    # ────────────────────────────────────────
    def find_by_id(self, faq_id: int) -> Optional[FAQ]:
        row = fetch_query(
            "SELECT * FROM faqs WHERE id = %s",
            (faq_id,), one=True
        )
        return FAQ.from_db(row) if row else None

    # ────────────────────────────────────────
    # 생성 / 수정 / 삭제 (관리자용)
    # ────────────────────────────────────────
    def create(
        self,
        question: str,
        answer: str,
        category: str = 'general',
        order: int = 0,
    ) -> int:
        execute_query(
            "INSERT INTO faqs (question, answer, category, `order`) "
            "VALUES (%s, %s, %s, %s)",
            (question, answer, category, order)
        )
        row = fetch_query("SELECT LAST_INSERT_ID() AS new_id", one=True)
        return row['new_id'] if row else -1

    def update(
        self,
        faq_id: int,
        question: str,
        answer: str,
        category: str,
        order: int,
    ):
        execute_query(
            "UPDATE faqs SET question = %s, answer = %s, "
            "category = %s, `order` = %s WHERE id = %s",
            (question, answer, category, order, faq_id)
        )

    def deactivate(self, faq_id: int):
        """soft delete"""
        execute_query(
            "UPDATE faqs SET active = 0 WHERE id = %s",
            (faq_id,)
        )
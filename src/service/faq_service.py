# src/service/faq_service.py
from typing import Optional  # ← 이거 추가

from src.domain.faq import FAQ
from src.repository.faq_repository import FAQRepository


class FAQService:

    def __init__(self):
        self.faq_repo = FAQRepository()

    # ════════════════════════════════════════
    # 조회
    # ════════════════════════════════════════

    def get_faq_list(self, category: Optional[str] = None) -> dict:
        """
        FAQ 목록 반환
        - category 없으면 전체 조회
        - category 있으면 해당 카테고리만 조회
        """
        if category:
            faqs = self.faq_repo.find_by_category(category)
        else:
            faqs = self.faq_repo.find_all_active()

        return {
            'faqs':     faqs,
            'category': category or 'all',
        }

    def get_faq(self, faq_id: int) -> FAQ:
        """FAQ 단건 조회"""
        faq = self.faq_repo.find_by_id(faq_id)
        if not faq:
            raise ValueError("존재하지 않는 FAQ입니다.")
        if not faq.is_visible():
            raise PermissionError("비활성화된 FAQ입니다.")
        return faq

    # ════════════════════════════════════════
    # 관리자용 CRUD
    # ════════════════════════════════════════

    def create_faq(
        self,
        question: str,
        answer: str,
        category: str = 'general',
        order: int = 0,
    ) -> int:
        """FAQ 생성"""
        if not question or not question.strip():
            raise ValueError("질문을 입력해주세요.")
        if not answer or not answer.strip():
            raise ValueError("답변을 입력해주세요.")

        return self.faq_repo.create(question, answer, category, order)

    def edit_faq(
        self,
        faq_id: int,
        question: str,
        answer: str,
        category: str,
        order: int,
    ):
        """FAQ 수정"""
        faq = self.faq_repo.find_by_id(faq_id)
        if not faq:
            raise ValueError("존재하지 않는 FAQ입니다.")

        self.faq_repo.update(faq_id, question, answer, category, order)

    def delete_faq(self, faq_id: int):
        """FAQ soft delete"""
        faq = self.faq_repo.find_by_id(faq_id)
        if not faq:
            raise ValueError("존재하지 않는 FAQ입니다.")

        self.faq_repo.deactivate(faq_id)
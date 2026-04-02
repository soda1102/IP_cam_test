# src/service/mypage_service.py
import math
from typing import Optional
from werkzeug.datastructures import FileStorage

from src.domain.file import AllowedExtension
from src.domain.ai_analysis import AIAnalysis
from src.repository.member_repository import MemberRepository
from src.repository.activity_repository import ActivityRepository
from src.common.storage import upload_file


class MypageService:

    def __init__(self):
        self.member_repo   = MemberRepository()
        self.activity_repo = ActivityRepository()

    # ════════════════════════════════════════
    # 마이페이지 메인 / 정보
    # ════════════════════════════════════════

    def get_mypage(self, user_id: int) -> dict:
        """마이페이지 메인 — 유저 정보 + 활동 요약"""
        member = self.member_repo.find_by_id(user_id)
        if not member:
            raise ValueError("존재하지 않는 사용자입니다.")

        summary = self.activity_repo.get_board_summary(user_id)
        return {'user': member, **summary}

    def get_member_info(self, user_id: int) -> dict:
        """회원 정보 상세 페이지"""
        member = self.member_repo.find_by_id(user_id)
        if not member:
            raise ValueError("존재하지 않는 사용자입니다.")
        return {'user': member}

    # ════════════════════════════════════════
    # 회원 정보 수정
    # ════════════════════════════════════════

    def edit_member(
        self,
        user_id: int,
        name: Optional[str] = None,
        nickname: Optional[str] = None,
        password: Optional[str] = None,
        birth_year: Optional[str] = None,
        birth_month: Optional[str] = None,
        birth_day: Optional[str] = None,
    ) -> dict:
        """
        회원 정보 수정
        Returns: 갱신된 세션 데이터
        """
        # 생년월일 처리
        birthdate = None
        if birth_year and birth_month and birth_day:
            birthdate = f"{birth_year}-{birth_month.zfill(2)}-{birth_day.zfill(2)}"

        self.member_repo.update_info(
            member_id = user_id,
            name      = name,
            nickname  = nickname,
            password  = password,
            birthdate = birthdate,
        )

        # 갱신된 세션 데이터 반환 (Controller에서 session 업데이트)
        return {
            'user_name':     name,
            'user_nickname': nickname,
        }

    # ════════════════════════════════════════
    # 프로필 이미지
    # ════════════════════════════════════════

    def upload_profile_image(self, user_id: int, file: FileStorage) -> str:
        """프로필 이미지 업로드 후 URL 반환"""
        if not file or file.filename == '':
            raise ValueError("선택된 파일이 없습니다.")

        if not AllowedExtension.is_image(file.filename):
            raise ValueError("이미지 파일만 업로드 가능합니다.")

        file_url = upload_file(file, folder=f"user_profiles/{user_id}")
        if not file_url:
            raise RuntimeError("파일 업로드에 실패했습니다.")

        self.member_repo.update_profile_img(user_id, file_url)
        return file_url

    def delete_profile_image(self, user_id: int):
        """프로필 이미지 삭제 (NULL로 업데이트)"""
        self.member_repo.update_profile_img(user_id, None)

    # ════════════════════════════════════════
    # 나의 활동
    # ════════════════════════════════════════

    def get_my_activity(self, user_id: int, page: int = 1) -> dict:
        """나의 활동 전체 데이터 일괄 반환"""
        per_page = 10
        my_posts, total_count = self.activity_repo.find_my_posts(user_id, page, per_page)
        total_pages = math.ceil(total_count / per_page) if total_count else 1

        return {
            'my_posts':    my_posts,
            'my_likes':    self.activity_repo.find_my_likes(user_id),
            'my_scraps':   self.activity_repo.find_my_scraps(user_id),
            'my_comments': self.activity_repo.find_my_comments(user_id),
            'my_trash':    self.activity_repo.find_my_trash(user_id),
            'my_blocks':   self.activity_repo.find_my_blocks(user_id),
            'pagination': {
                'page':        page,
                'total_pages': total_pages,
                'has_prev':    page > 1,
                'has_next':    page < total_pages,
                'prev_num':    page - 1,
                'next_num':    page + 1,
            }
        }

    def unblock_user(self, blocker_id: int, blocked_id: int):
        """차단 해제"""
        self.activity_repo.unblock(blocker_id, blocked_id)

    # ════════════════════════════════════════
    # 회원 탈퇴
    # ════════════════════════════════════════

    def delete_account(self, user_id: int):
        """회원 탈퇴 (soft delete)"""
        member = self.member_repo.find_by_id(user_id)
        if not member:
            raise ValueError("존재하지 않는 사용자입니다.")
        self.member_repo.deactivate(user_id)

    # ════════════════════════════════════════
    # AI 분석 결과
    # ════════════════════════════════════════

    def save_ai_result(
        self,
        user_id: int,
        file: FileStorage,
        original_filename: str,
        boar_count: int,
        water_deer_count: int,
        racoon_count: int,
    ) -> str:
        """AI 분석 결과 저장 후 이미지 URL 반환"""
        if not file:
            raise ValueError("파일이 없습니다.")

        result_url = upload_file(file, folder="results")
        if not result_url:
            raise RuntimeError("업로드된 URL을 찾을 수 없습니다.")

        self.activity_repo.create_ai_result(
            user_id          = user_id,
            filename         = original_filename or '무제_분석결과',
            image_url        = result_url,
            boar_count       = boar_count,
            water_deer_count = water_deer_count,
            racoon_count     = racoon_count,
        )
        return result_url

    def get_ai_results(self, user_id: int, page: int = 1) -> dict:
        """AI 분석 결과 목록 + 페이지네이션"""
        per_page = 5
        items, total_count = self.activity_repo.find_ai_results(user_id, page, per_page)
        total_pages = math.ceil(total_count / per_page) if total_count else 1

        return {
            'records':     items,
            'page':        page,
            'total_pages': total_pages,
            'has_prev':    page > 1,
            'has_next':    page < total_pages,
            'prev_num':    page - 1,
            'next_num':    page + 1,
        }

    def get_ai_report(self, analysis_id: int, user_id: int) -> AIAnalysis:
        """AI 분석 보고서 다운로드용 단건 조회"""
        result = self.activity_repo.find_ai_result_by_id(analysis_id)
        if not result:
            raise ValueError("파일을 찾을 수 없습니다.")
        if not result.is_owned_by(user_id):
            raise PermissionError("본인의 분석 결과만 다운로드할 수 있습니다.")
        return result

    def delete_ai_result(self, analysis_id: int, user_id: int):
        """AI 분석 결과 삭제"""
        result = self.activity_repo.find_ai_result_by_id(analysis_id)
        if not result:
            raise ValueError("존재하지 않는 분석 결과입니다.")
        if not result.is_owned_by(user_id):
            raise PermissionError("본인의 분석 결과만 삭제할 수 있습니다.")
        self.activity_repo.delete_ai_result(analysis_id, user_id)
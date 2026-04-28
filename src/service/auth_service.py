# src/service/auth_service.py
from datetime import date
from typing import Optional

from src.domain.Member import Member, is_old_enough
from src.repository.member_repository import MemberRepository
from src.common import log_system


class AuthService:

    def __init__(self):
        self.member_repo = MemberRepository()

    # ════════════════════════════════════════
    # 로그인
    # ════════════════════════════════════════

    def login(self, uid: str, password: str) -> Member:
        """
        로그인 검증
        - 존재하지 않는 UID
        - 비활성 계정
        - 비밀번호 불일치
        Returns: 검증 통과한 Member 객체
        """
        member = self.member_repo.find_by_uid(uid)

        # 1. 존재하지 않는 UID
        if member is None:
            log_system('SECURITY', 'WARNING', 'LOGIN_FAIL', f'존재하지 않는 UID 시도: {uid}')
            raise ValueError("존재하지 않는 아이디입니다.")

        # 2. 비활성 계정
        if not member.is_active():
            log_system('SECURITY', 'WARNING', 'LOGIN_FAIL', f'탈퇴한 계정 접속 시도: {uid}')
            raise PermissionError("비활성화 처리된 계정입니다.\n관리자에게 문의해 주세요.")

        # 3. 비밀번호 불일치
        if not member.check_password(password):
            log_system('SECURITY', 'WARNING', 'LOGIN_FAIL', f'비밀번호 불일치 UID: {uid}')
            raise ValueError("아이디 또는 비밀번호가 일치하지 않습니다.")

        log_system('ACCESS', 'INFO', 'LOGIN_SUCCESS', f'로그인 UID : {uid}')
        return member

    # ════════════════════════════════════════
    # 회원가입
    # ════════════════════════════════════════

    def signup(
        self,
        uid: str,
        password: str,
        name: str,
        nickname: str,
        birth_year: str,
        birth_month: str,
        birth_day: str,
    ):
        """
        회원가입
        - 생년월일 누락 확인
        - 만 14세 미만 차단
        - UID 중복 확인
        - DB INSERT
        """
        # 1. 생년월일 누락 확인
        if not all([birth_year, birth_month, birth_day]):
            raise ValueError("생년월일을 모두 입력해주세요.")

        # 2. 만 14세 미만 차단
        try:
            birthdate = date(int(birth_year), int(birth_month), int(birth_day))
        except (ValueError, TypeError):
            raise ValueError("올바른 생년월일을 입력해주세요.")

        if not is_old_enough(birthdate):
            raise PermissionError("만 14세 이상만 가입 가능합니다.")

        # 3. UID 중복 확인
        if self.member_repo.exists_by_uid(uid):
            raise ValueError("이미 존재하는 아이디입니다.")

        # 4. DB INSERT
        birthdate_str = birthdate.strftime('%Y-%m-%d')
        self.member_repo.create(uid, password, name, nickname, birthdate_str)

    # ════════════════════════════════════════
    # 로그아웃
    # ════════════════════════════════════════

    def logout(self):
        """
        현재는 session.clear()만으로 충분하지만
        추후 토큰 무효화, 로그 기록 등 확장 가능하도록 Service에 위치
        """
        pass
# src/repository/member_repository.py
from typing import Optional
from src.common.db import fetch_query, execute_query
from src.domain.member import Member


class MemberRepository:

    # ────────────────────────────────────────
    # 단건 조회
    # ────────────────────────────────────────
    def find_by_uid(self, uid: str) -> Optional[Member]:
        row = fetch_query(
            "SELECT * FROM members WHERE uid = %s",
            (uid,), one=True
        )
        return Member.from_db(row) if row else None

    def find_by_id(self, member_id: int) -> Optional[Member]:
        row = fetch_query(
            "SELECT * FROM members WHERE id = %s",
            (member_id,), one=True
        )
        return Member.from_db(row) if row else None

    # ────────────────────────────────────────
    # 중복 확인
    # ────────────────────────────────────────
    def exists_by_uid(self, uid: str) -> bool:
        row = fetch_query(
            "SELECT id FROM members WHERE uid = %s",
            (uid,), one=True
        )
        return row is not None

    # ────────────────────────────────────────
    # 생성
    # ────────────────────────────────────────
    def create(
        self,
        uid: str,
        password: str,
        name: str,
        nickname: str,
        birthdate: str,         # 'YYYY-MM-DD' 형식
    ) -> int:
        execute_query(
            "INSERT INTO members (uid, password, name, nickname, birthdate) "
            "VALUES (%s, %s, %s, %s, %s)",
            (uid, password, name, nickname, birthdate)
        )
        row = fetch_query("SELECT LAST_INSERT_ID() AS new_id", one=True)
        return row['new_id'] if row else -1

    def update_profile_img(self, member_id: int, file_url: Optional[str]):
        """프로필 이미지 업데이트 (None이면 삭제)"""
        execute_query(
            "UPDATE members SET profile_img = %s WHERE id = %s",
            (file_url, member_id)
        )

    def update_info(
            self,
            member_id: int,
            name: Optional[str] = None,
            nickname: Optional[str] = None,
            password: Optional[str] = None,
            birthdate: Optional[str] = None,
    ):
        """회원 정보 수정 — 입력된 필드만 동적으로 UPDATE"""
        set_clauses, params = [], []

        if name:
            set_clauses.append("name = %s")
            params.append(name)
        if nickname:
            set_clauses.append("nickname = %s")
            params.append(nickname)
        if password:
            set_clauses.append("password = %s")
            params.append(password)
        if birthdate:
            set_clauses.append("birthdate = %s")
            params.append(birthdate)

        if not set_clauses:
            return  # 수정할 내용 없음

        params.append(member_id)
        execute_query(
            f"UPDATE members SET {', '.join(set_clauses)} WHERE id = %s",
            tuple(params)
        )

    def deactivate(self, member_id: int):
        """회원 탈퇴 (soft delete)"""
        execute_query(
            "UPDATE members SET active = 0 WHERE id = %s",
            (member_id,)
        )
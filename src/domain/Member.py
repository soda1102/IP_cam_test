# src/domain/member.py
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Member:
    # ── PK / FK ──────────────────────────────
    id: int
    uid: str

    # ── 본문 ─────────────────────────────────
    password: str
    name: str
    nickname: str
    role: str = 'user'

    # ── 상태 ─────────────────────────────────
    active: bool = True

    # ── 선택 정보 ─────────────────────────────
    birthdate: Optional[date] = None
    profile_img: Optional[str] = None
    created_at: Optional[datetime] = None

    # ────────────────────────────────────────
    # Factory
    # ────────────────────────────────────────
    @classmethod
    def from_db(cls, row: dict) -> "Member":
        return cls(
            id=row['id'],
            uid=row['uid'],
            password=row['password'],
            name=row['name'],
            nickname=row['nickname'],
            role=row.get('role', 'user'),
            active=bool(row.get('active', 1)),
            birthdate=row.get('birthdate'),
            profile_img=row.get('profile_img'),
            created_at=row.get('created_at'),
        )

    # ────────────────────────────────────────
    # 비즈니스 규칙
    # ────────────────────────────────────────
    def is_active(self) -> bool:
        """활성 계정 여부"""
        return self.active

    def check_password(self, raw_password: str) -> bool:
        """비밀번호 일치 여부"""
        return self.password == raw_password

    def is_admin(self) -> bool:
        return self.role == 'admin'

    def to_session(self) -> dict:
        """로그인 성공 시 session에 저장할 데이터"""
        return {
            'user_id':       self.id,
            'user_name':     self.name,
            'user_nickname': self.nickname,
            'user_role':     self.role,
            'user_profile':  self.profile_img,
        }


# ────────────────────────────────────────
# Value Object — 나이 검증
# ────────────────────────────────────────
MIN_AGE = 14

def calculate_age(birthdate: date) -> int:
    today = date.today()
    return (today.year - birthdate.year
            - ((today.month, today.day) < (birthdate.month, birthdate.day)))

def is_old_enough(birthdate: date) -> bool:
    """만 14세 이상 여부"""
    return calculate_age(birthdate) >= MIN_AGE
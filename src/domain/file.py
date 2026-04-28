# src/domain/file.py
from dataclasses import dataclass
from typing import Optional


# ────────────────────────────────────────
# Value Object — 허용 확장자
# ────────────────────────────────────────
class AllowedExtension:
    IMAGE    = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    DOCUMENT = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}
    ALL      = IMAGE | DOCUMENT

    @classmethod
    def is_allowed(cls, filename: str) -> bool:
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return ext in cls.ALL

    @classmethod
    def is_image(cls, filename: str) -> bool:
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return ext in cls.IMAGE


# ────────────────────────────────────────
# Value Object — 파일 크기 제한
# ────────────────────────────────────────
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ────────────────────────────────────────
# Entity
# ────────────────────────────────────────
@dataclass
class File:
    # ── PK / FK ──────────────────────────────
    id: int
    board_id: int

    # ── 파일 정보 ─────────────────────────────
    origin_name: str        # 원본 파일명 (한글 가능)
    save_name: str          # Cloudinary URL (저장된 이름)
    file_path: str          # Cloudinary secure_url
    file_size: int          # bytes

    # ────────────────────────────────────────
    # Factory
    # ────────────────────────────────────────
    @classmethod
    def from_db(cls, row: dict) -> "File":
        return cls(
            id=row['id'],
            board_id=row['board_id'],
            origin_name=row['origin_name'],
            save_name=row['save_name'],
            file_path=row['file_path'],
            file_size=row['file_size'],
        )

    # ────────────────────────────────────────
    # 비즈니스 규칙
    # ────────────────────────────────────────
    def is_image(self) -> bool:
        """이미지 파일 여부 (미리보기 렌더링 판단용)"""
        return AllowedExtension.is_image(self.origin_name)

    def is_allowed(self) -> bool:
        """허용된 확장자인지"""
        return AllowedExtension.is_allowed(self.origin_name)

    def exceeds_size_limit(self) -> bool:
        """파일 크기 초과 여부"""
        return self.file_size > MAX_FILE_SIZE

    def size_in_mb(self) -> float:
        """MB 단위 파일 크기 (소수점 1자리)"""
        return round(self.file_size / (1024 * 1024), 1)

    def encoded_name(self) -> str:
        """다운로드 헤더용 URL 인코딩된 파일명"""
        import urllib.parse
        return urllib.parse.quote(self.origin_name)
# src/domain/ai_analysis.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import urllib.parse


@dataclass
class AIAnalysis:
    # ── PK / FK ──────────────────────────────
    id: int
    user_id: int

    # ── 본문 ─────────────────────────────────
    filename: str
    image_url: str
    boar_count: int = 0          # 멧돼지
    water_deer_count: int = 0    # 고라니
    racoon_count: int = 0        # 너구리

    # ── 시간 ─────────────────────────────────
    created_at: Optional[datetime] = None

    # ────────────────────────────────────────
    # Factory
    # ────────────────────────────────────────
    @classmethod
    def from_db(cls, row: dict) -> "AIAnalysis":
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            filename=row.get('filename') or '무제_분석결과',
            image_url=row.get('image_url', ''),
            boar_count=row.get('boar_count', 0),
            water_deer_count=row.get('water_deer_count', 0),
            racoon_count=row.get('racoon_count', 0),
            created_at=row.get('created_at'),
        )

    # ────────────────────────────────────────
    # 비즈니스 규칙
    # ────────────────────────────────────────
    def is_owned_by(self, user_id: int) -> bool:
        return self.user_id == user_id

    def total_count(self) -> int:
        """탐지된 동물 총 마리 수"""
        return self.boar_count + self.water_deer_count + self.racoon_count

    def to_report_text(self) -> str:
        """텍스트 보고서 내용 생성"""
        return (
            f"AI 분석 결과 보고서\n"
            f"====================\n"
            f"파일명: {self.filename}\n"
            f"멧돼지: {self.boar_count}마리\n"
            f"고라니: {self.water_deer_count}마리\n"
            f"너구리: {self.racoon_count}마리\n"
            f"====================\n"
            f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def encoded_filename(self) -> str:
        """다운로드 헤더용 URL 인코딩 파일명"""
        return urllib.parse.quote(f"{self.filename}.txt")
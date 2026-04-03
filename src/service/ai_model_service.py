# src/service/ai_model_service.py
import os
import datetime
from typing import Optional
from werkzeug.datastructures import FileStorage
from flask import current_app

from src.infrastructure.yolo_detector import YoloDetector
from src.repository.ai_model_repository import AIModelRepository
from src.common.storage import upload_file


VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}


class AIModelService:

    def __init__(self):
        self.detector = YoloDetector()
        self.ai_repo  = AIModelRepository()

    # ════════════════════════════════════════
    # 이미지 탐지
    # ════════════════════════════════════════

    def detect_image(self, file: FileStorage) -> dict:
        """
        이미지 단일 프레임 탐지
        - 디스크 저장 없이 메모리에서 바로 추론
        Returns: {'counts': [...], 'detections': [...]}
        """
        if not file:
            raise ValueError("파일이 없습니다.")

        file_bytes = file.read()
        return self.detector.detect_from_bytes(file_bytes, conf=0.4)

    # ════════════════════════════════════════
    # 영상 스트리밍
    # ════════════════════════════════════════

    def get_video_stream(self, filename: str):
        """
        실시간 영상 스트리밍 제너레이터 반환
        """
        temp_path = os.path.join('static/temp', filename)
        if not os.path.exists(temp_path):
            raise FileNotFoundError("파일을 찾을 수 없습니다.")

        return self.detector.generate_frames(temp_path, conf=0.75)

    # ════════════════════════════════════════
    # 결과 저장
    # ════════════════════════════════════════

    def save_result(
        self,
        user_id: int,
        file: FileStorage,
        original_filename: str,
        boar_count: int,
        water_deer_count: int,
        racoon_count: int,
    ) -> str:
        """
        분석 결과 저장
        - 이미지: 로컬 저장 → Cloudinary 업로드 → DB 저장
        - 영상: YOLO 추론 → 로컬 저장 → Cloudinary 업로드 → DB 저장
        Returns: Cloudinary URL
        """
        if not file:
            raise ValueError("데이터가 없습니다.")

        save_dir = os.path.join(current_app.root_path, 'static', 'results')
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs('static/temp', exist_ok=True)

        now_str    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ext        = os.path.splitext(original_filename.lower())[1]
        is_video   = ext in VIDEO_EXTENSIONS
        local_path = None

        try:
            if is_video:
                local_path = self._save_video_result(file, original_filename, save_dir, now_str)
            else:
                local_path = self._save_image_result(file, save_dir, now_str)

            # Cloudinary 업로드
            result_url = self._upload_to_cloudinary(local_path)

            # DB 저장
            self.ai_repo.save_result(
                user_id=user_id,
                original_filename=original_filename,
                result_url=result_url,
                boar_count=boar_count,
                water_deer_count=water_deer_count,
                racoon_count=racoon_count,
            )
            return result_url

        finally:
            # 로컬 임시 파일 정리
            if local_path and os.path.exists(local_path):
                os.remove(local_path)

    # ════════════════════════════════════════
    # Private 헬퍼
    # ════════════════════════════════════════

    def _save_image_result(self, file: FileStorage, save_dir: str, now_str: str) -> str:
        """이미지 로컬 저장 후 경로 반환"""
        local_path = os.path.join(save_dir, f"detection_{now_str}.jpg")
        file.save(local_path)
        return local_path

    def _save_video_result(
        self,
        file: FileStorage,
        original_filename: str,
        save_dir: str,
        now_str: str,
    ) -> str:
        """영상 YOLO 추론 후 결과 경로 반환"""
        temp_input = os.path.join('static', 'temp', f"temp_{original_filename}")
        file.save(temp_input)

        try:
            local_path = self.detector.predict_video(
                source_path = temp_input,
                save_dir    = save_dir,
                name        = now_str,
                conf        = 0.25,
            )
        finally:
            if os.path.exists(temp_input):
                os.remove(temp_input)

        return local_path

    def _upload_to_cloudinary(self, local_path: str) -> str:
        """로컬 파일 Cloudinary 업로드 후 URL 반환"""
        with open(local_path, 'rb') as f:
            result_url = upload_file(f, folder="results")

        if not result_url:
            raise RuntimeError("파일 업로드 실패")

        return result_url
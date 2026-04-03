# src/infrastructure/yolo_detector.py
import cv2
import numpy as np
import os
import shutil
import datetime
import time
from ultralytics import YOLO

MODEL_PATH = 'static/model/best.pt'

# 라벨 매핑
LABEL_MAP = {
    'boar': '멧돼지',
    'water_deer': '고라니',
    'racoon': '너구리',
}


class YoloDetector:
    """
    YOLOv11 모델 래퍼
    - 모델 로드는 앱 시작 시 한 번만
    - 이미지/영상 추론 전담
    """

    def __init__(self):
        self.model = YOLO(MODEL_PATH)

    # ════════════════════════════════════════
    # 이미지 추론
    # ════════════════════════════════════════

    def detect_from_bytes(self, file_bytes: bytes, conf: float = 0.4) -> dict:
        """
        메모리 버퍼에서 바로 이미지 추론
        Returns: {'counts': [...], 'detections': [...]}
        """
        np_arr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return self._run_detection(img, conf)

    def detect_from_path(self, image_path: str, conf: float = 0.4) -> dict:
        """파일 경로에서 이미지 추론"""
        img = cv2.imread(image_path)
        return self._run_detection(img, conf)

    def _run_detection(self, img, conf: float) -> dict:
        results = self.model.predict(img, conf=conf, save=False, verbose=False)
        counts = {v: 0 for v in LABEL_MAP.values()}
        detections = []

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                eng_label = self.model.names[cls_id]
                kor_label = LABEL_MAP.get(eng_label, eng_label)
                conf_val = float(box.conf[0])
                bbox = box.xyxyn[0].tolist()

                detections.append({
                    'label': kor_label,
                    'conf': f"{conf_val:.2f}",
                    'bbox': bbox,
                })
                if kor_label in counts:
                    counts[kor_label] += 1

        return {
            'counts': [counts['멧돼지'], counts['고라니'], counts['너구리']],
            'detections': detections,
        }

    # ════════════════════════════════════════
    # 영상 스트리밍
    # ════════════════════════════════════════

    def generate_frames(self, video_path: str, conf: float = 0.75):
        """
        실시간 스트리밍용 프레임 제너레이터
        영상 종료 후 파일 자동 삭제
        """
        cap = cv2.VideoCapture(video_path)

        try:
            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    break

                results = self.model.predict(frame, conf=conf, verbose=False)
                annotated_frame = results[0].plot()
                ret, buffer = cv2.imencode('.jpg', annotated_frame)

                if not ret:
                    continue

                yield (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n'
                        + buffer.tobytes()
                        + b'\r\n'
                )
        finally:
            cap.release()
            if os.path.exists(video_path):
                os.remove(video_path)

    # ════════════════════════════════════════
    # 영상 결과 저장
    # ════════════════════════════════════════

    def predict_video(self, source_path: str, save_dir: str, name: str, conf: float = 0.25) -> str:

        if not os.path.exists(source_path):
            print(f"❌ ERROR: 원본 파일이 존재하지 않음 -> {source_path}")
            raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {source_path}")

        print(f"🚀 분석 시작: {source_path} (Ext: {os.path.splitext(source_path)[1]})")
        results = self.model.predict(
            source=source_path,
            save=True,
            project=save_dir,
            name=name,
            conf=conf,
            stream=True
        )

        for _ in results:
            pass

        yolo_output_dir = os.path.join(save_dir, name)
        print(f"📂 YOLO 출력 경로 확인: {yolo_output_dir}")

        if not os.path.exists(yolo_output_dir) or not os.listdir(yolo_output_dir):
            raise FileNotFoundError("YOLO 결과 파일 생성 실패")

        all_files = [f for f in os.listdir(yolo_output_dir) if not f.startswith('.')]
        video_files = [f for f in all_files if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
        target_file = video_files[0] if video_files else all_files[0]
        target_full_path = os.path.join(yolo_output_dir, target_file)

        # 파일 크기가 안정될 때까지 대기 (최대 30초)
        prev_size = -1
        for _ in range(60):
            time.sleep(0.5)
            if not os.path.exists(target_full_path):
                continue
            curr_size = os.path.getsize(target_full_path)
            if curr_size > 0 and curr_size == prev_size:
                break
            prev_size = curr_size

        print(f"📄 선택된 결과 파일: {target_file}")

        # ✅ now_str 새로 생성하지 않고 name 그대로 사용 → temp_key와 일치
        ext = os.path.splitext(target_file)[1]
        local_path = os.path.join(save_dir, f"detection_{name}{ext}")

        shutil.move(target_full_path, local_path)
        shutil.rmtree(yolo_output_dir)

        print(f"✅ 분석 완료 및 저장: {local_path}")
        return local_path
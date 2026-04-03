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
        local_path = os.path.join(save_dir, f"detection_{name}.mp4")

        shutil.move(target_full_path, local_path)
        shutil.rmtree(yolo_output_dir)

        print(f"✅ 분석 완료 및 저장: {local_path}")
        return local_path

    def compress_video(self, input_path: str, output_path: str, target_mb: int = 8) -> str:
        """
        OpenCV로 영상 화질을 낮춰 용량 압축
        target_mb 이하가 될 때까지 품질을 낮춤
        Returns: 압축된 파일 경로
        """
        cap = cv2.VideoCapture(input_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 해상도 스케일 (720p 초과면 720p로 줄임)
        scale = min(1.0, 720 / max(height, 1))
        new_w = int(width * scale) // 2 * 2
        new_h = int(height * scale) // 2 * 2

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (new_w, new_h))

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if scale < 1.0:
                frame = cv2.resize(frame, (new_w, new_h))
            out.write(frame)

        cap.release()
        out.release()

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"📦 압축 완료: {file_size_mb:.1f}MB → {output_path}")
        return output_path

    def annotate_image(self, file_bytes: bytes, detections: list) -> bytes:
        """
        탐지 결과를 이미지에 직접 그려서 bytes로 반환
        PIL로 한글 폰트 렌더링
        """
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont

        np_arr = np.frombuffer(file_bytes, np.uint8)
        img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # OpenCV BGR → PIL RGB 변환
        img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        w, h = img_pil.size

        # 한글 폰트 로드 (없으면 기본 폰트)
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", size=18)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", size=18)
            except:
                font = ImageFont.load_default()

        BOX_COLOR = (0, 230, 118)  # 초록
        TEXT_COLOR = (0, 0, 0)  # 검정

        for det in detections:
            if not det.get('bbox'):
                continue
            conf = float(det.get('conf', 0))
            if conf < 0.4:
                continue

            x1, y1, x2, y2 = det['bbox']
            sx = int(x1 * w)
            sy = int(y1 * h)
            ex = int(x2 * w)
            ey = int(y2 * h)

            # 박스 그리기
            draw.rectangle([sx, sy, ex, ey], outline=BOX_COLOR, width=2)

            # 라벨 텍스트
            label = f"{det['label']} {det['conf']}"
            bbox_text = font.getbbox(label)
            tw = bbox_text[2] - bbox_text[0]
            th = bbox_text[3] - bbox_text[1]

            label_y = sy - th - 6 if sy - th - 6 > 0 else sy + 2

            # 라벨 배경
            draw.rectangle([sx, label_y, sx + tw + 8, label_y + th + 4], fill=BOX_COLOR)
            # 라벨 텍스트
            draw.text((sx + 4, label_y + 2), label, fill=TEXT_COLOR, font=font)

        # PIL RGB → OpenCV BGR → jpg bytes
        img_result = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        _, buffer = cv2.imencode('.jpg', img_result, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buffer.tobytes()
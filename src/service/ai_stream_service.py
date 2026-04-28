import cv2
import torch
import base64
import time
import os
from ultralytics import YOLO


class AiStreamService:
    _model = None
    _target_label = ""
    _device = 'cuda' if torch.cuda.is_available() else 'cpu'

    @classmethod
    def load_model(cls):
        if cls._model is None:
            cls._model = YOLO('yolov8n.pt')
            cls._model.to(cls._device)
            print(f"[AI] 모델 로드 완료 (Device: {cls._device})")
        return cls._model

    @classmethod
    def set_target(cls, label: str):
        cls._target_label = label.strip().lower()

    @classmethod
    def run_rtsp_stream(cls, socketio, rtsp_url: str):
        print(f"[DEBUG] run_rtsp_stream 호출됨: {rtsp_url}")  # ← 추가
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        print(f"[DEBUG] cap.isOpened(): {cap.isOpened()}")  # ← 추가
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            print(f"[ERROR] RTSP 연결 실패: {rtsp_url}")
            socketio.emit('stream_error', {'message': 'RTSP 연결 실패'})
            return

        model = cls.load_model()
        frame_count = 0
        print(f"[START] IP캠 스트리밍 시작")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                socketio.sleep(0.1)
                continue

            frame = cv2.resize(frame, (640, 480))
            frame_count += 1

            if frame_count % 3 != 0:
                continue

            results = model.predict(frame, device=cls._device, conf=0.7, verbose=False, imgsz=640)
            boxes = results[0].boxes
            annotated_frame = results[0].plot()

            _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            encoded_image = base64.b64encode(buffer).decode('utf-8')

            socketio.emit('ai_frame', {
                'image': encoded_image,
                'count': frame_count
            })

            # 타겟 감지 알림
            if cls._target_label and boxes is not None:
                detected_names = [model.names[int(i)].lower() for i in boxes.cls.tolist()]
                if cls._target_label in detected_names:
                    socketio.emit('detection_alert', {
                        'label': cls._target_label,
                        'time': time.strftime('%H:%M:%S')
                    })

            socketio.sleep(0.01)

        cap.release()
        print(f"[END] IP캠 스트리밍 종료")
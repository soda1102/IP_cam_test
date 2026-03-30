import cv2
import os
import datetime # 추가
from flask import Blueprint, render_template, request, jsonify, Response, current_app # current_app 추가
from src.common import login_required
from src.common.storage import upload_file # 추가
from ultralytics import YOLO

model_bp = Blueprint('model', __name__)

# 1. YOLOv11 모델 로드
MODEL_PATH = 'static/model/best.pt'
model = YOLO(MODEL_PATH)

@model_bp.route('/', methods=['GET'])
@login_required
def get_model_page():
    return render_template('ai_model/model.html')

# 실시간 분석 프레임 생성기
def generate_frames(video_path):
    cap = cv2.VideoCapture(video_path)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # YOLOv11 분석 (화면에 직접 그리기 위해 verbose=False)
        results = model.predict(frame, conf=0.25, verbose=False)

        # [핵심] 박스가 그려진 결과 화면(Annotated Frame) 가져오기
        annotated_frame = results[0].plot()

        # JPEG 인코딩
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if not ret: continue

        frame_bytes = buffer.tobytes()

        # MJPEG 스트리밍 규격에 맞게 yield
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()
    # 스트리밍이 완전히 끝나면 파일 삭제 (여기서 지워야 영상이 끝까지 나옴)
    if os.path.exists(video_path):
        os.remove(video_path)

# 실시간 영상 스트리밍 라우트
@model_bp.route('/video_feed/<filename>')
@login_required
def video_feed(filename):
    temp_path = os.path.join('static/temp', filename)
    if not os.path.exists(temp_path):
        return "파일을 찾을 수 없습니다.", 404

    return Response(generate_frames(temp_path),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# 결과 저장 (기존 분석 로직)
@model_bp.route('/detect', methods=['POST'])
@login_required
def detect_objects():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    # 임시 파일 저장 (분석용)
    temp_path = os.path.join('static/temp', 'temp_frame.jpg')
    os.makedirs('static/temp', exist_ok=True)
    file.save(temp_path)

    try:
        # 분석 수행
        results = model.predict(temp_path, conf=0.4, save=False)

        label_map = {'boar': '멧돼지', 'water_deer': '고라니', 'racoon': '너구리'}
        counts = {"멧돼지": 0, "고라니": 0, "너구리": 0}
        detections = []

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                eng_label = model.names[cls_id]
                kor_label = label_map.get(eng_label, eng_label)
                conf = float(box.conf[0])

                # 좌표 추출 [x1, y1, x2, y2] (0~1 사이의 정규화된 값으로 변환)
                b = box.xyxyn[0].tolist()

                detections.append({
                    'label': kor_label,
                    'conf': f"{conf:.2f}",
                    'bbox': b
                })

                if kor_label in counts:
                    counts[kor_label] += 1

        return jsonify({
            'success': True,
            'counts': [counts["멧돼지"], counts["고라니"], counts["너구리"]],
            'detections': detections  # 이제 좌표 데이터가 포함됩니다!
        })

    except Exception as e:
        print(f"Error during detection: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- 여기서부터 추가된 저장 로직입니다 (형식 유지) ---

@model_bp.route('/save_result', methods=['POST'])
@login_required
def save_result():
    """
    분석된 결과 이미지를 로컬 static/results 폴더와 Cloudinary에 동시 저장
    """
    file = request.files.get('merged_image')

    if not file:
        return jsonify({"success": False, "message": "데이터가 없습니다."}), 400

    try:
        # 1. 로컬 저장 경로 설정 및 폴더 생성
        save_dir = os.path.join(current_app.root_path, 'static', 'results')
        os.makedirs(save_dir, exist_ok=True)

        # 파일명 생성 (시간 기반)
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detection_{now_str}.jpg"
        local_path = os.path.join(save_dir, filename)

        # 로컬에 파일 실제 저장
        file.save(local_path)

        # 2. Cloudinary 업로드
        with open(local_path, 'rb') as f:
            result_url = upload_file(f, folder="results")

        if result_url:
            return jsonify({
                "success": True,
                "url": result_url,
                "message": "로컬 및 클라우드 저장 성공!"
            })
        else:
            return jsonify({"success": False, "message": "클라우드 업로드 실패"}), 500

    except Exception as e:
        print(f"Error during save_result: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
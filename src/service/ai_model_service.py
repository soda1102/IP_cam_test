import cv2
import os
import datetime
import shutil
from flask import Blueprint, render_template, request, jsonify, Response, current_app, session
from src.common import login_required
from src.common.storage import upload_file
# --- [수정] execute_query 임포트 ---
from src.common import execute_query
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

        # YOLOv11 분석
        results = model.predict(frame, conf=0.25, verbose=False)
        annotated_frame = results[0].plot()

        # JPEG 인코딩
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if not ret: continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    cap.release()
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


# 단일 프레임/이미지 탐지
@model_bp.route('/detect', methods=['POST'])
@login_required
def detect_objects():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    temp_path = os.path.join('static/temp', 'temp_frame.jpg')
    os.makedirs('static/temp', exist_ok=True)
    file.save(temp_path)

    try:
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
            'detections': detections
        })
    except Exception as e:
        print(f"Error during detection: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# 결과 저장 및 Cloudinary 업로드 (최종 수정 완료)
@model_bp.route('/save_result', methods=['POST'])
@login_required
def save_result():
    file = request.files.get('merged_image')
    original_filename = request.form.get('original_filename', '')

    # 1. 숫자 데이터 변환 (안전하게 처리)
    try:
        boar_count = int(request.form.get('boar_count', 0))
        water_deer_count = int(request.form.get('water_deer_count', 0))
        racoon_count = int(request.form.get('racoon_count', 0))
    except (ValueError, TypeError):
        boar_count = water_deer_count = racoon_count = 0

    # 2. 유저 ID 추출 (90001 확인됨)
    user_id = session.get('user_id')
    print(f"--- [DEBUG] 현재 세션 user_id: {user_id} ---")

    if not file:
        return jsonify({"success": False, "message": "데이터가 없습니다."}), 400

    local_path = None
    try:
        # 경로 설정 및 폴더 생성
        save_dir = os.path.join(current_app.root_path, 'static', 'results')
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs('static/temp', exist_ok=True)

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        is_video = any(original_filename.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv'])

        if is_video:
            temp_input = os.path.join('static', 'temp', f"temp_{original_filename}")
            file.save(temp_input)
            # YOLO 분석 및 저장
            model.predict(source=temp_input, save=True, project=save_dir, name=now_str, conf=0.25)
            yolo_output_dir = os.path.join(save_dir, now_str)
            files_in_yolo_dir = os.listdir(yolo_output_dir) if os.path.exists(yolo_output_dir) else []

            filename = f"detection_{now_str}.mp4"
            local_path = os.path.join(save_dir, filename)

            if files_in_yolo_dir:
                yolo_actual_file = files_in_yolo_dir[0]
                yolo_actual_path = os.path.join(yolo_output_dir, yolo_actual_file)
                shutil.move(yolo_actual_path, local_path)
                shutil.rmtree(yolo_output_dir)
            else:
                raise FileNotFoundError(f"YOLO가 결과 영상을 생성하지 못했습니다.")
            if os.path.exists(temp_input): os.remove(temp_input)
        else:
            # 이미지 저장
            filename = f"detection_{now_str}.jpg"
            local_path = os.path.join(save_dir, filename)
            file.save(local_path)

        # 3. Cloudinary 업로드 및 URL 획득 (여기가 핵심!)
        result_url = None
        if local_path and os.path.exists(local_path):
            with open(local_path, 'rb') as f:
                # Cloudinary 업로드 함수 호출
                result_url = upload_file(f, folder="results")
                print(f"--- [DEBUG] Cloudinary URL: {result_url} ---")

        # 4. DB 저장
        if result_url:
            if user_id is None:
                return jsonify({"success": False, "message": "로그인 정보가 없습니다."}), 401

            try:
                # 이제 user 테이블이 없으므로 members를 참조하거나 제약조건이 풀린 상태여야 함
                sql = """
                INSERT INTO ai_analysis 
                (user_id, filename, boar_count, water_deer_count, racoon_count, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """
                execute_query(sql, (user_id, result_url, boar_count, water_deer_count, racoon_count))

                # 성공 시 URL을 반드시 프론트엔드로 보내줌
                return jsonify({
                    "success": True,
                    "url": result_url,
                    "message": "Cloudinary 업로드 및 DB 저장 성공!"
                })

            except Exception as db_err:
                print(f"--- [DB ERROR] {db_err} ---")
                return jsonify({
                    "success": False,
                    "message": f"DB 저장 실패: {str(db_err)}",
                    "url": result_url  # DB는 실패해도 URL은 일단 보내줌
                }), 500

        return jsonify({"success": False, "message": "파일 업로드 실패"}), 500

    except Exception as e:
        print(f"--- [SYSTEM ERROR] {e} ---")
        return jsonify({"success": False, "message": str(e)}), 500
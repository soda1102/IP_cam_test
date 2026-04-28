from dotenv import load_dotenv
load_dotenv()

# 기본 모듈
import os
import sys
import io
import cv2
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.stdout.reconfigure(line_buffering=True)
# 라이브러리
from flask_caching import Cache
from flask import Flask, render_template, Response
from flask_socketio import SocketIO
# FIXME: backend. 제거
from src.service.ai_stream_service import AiStreamService
from src.service.WebCamService import WebCamService
from src.service.cctv_service import CctvService # 상단에 추가

RTSP_URL = os.getenv('RTSP_URL', 'rtsp://admin:Mbc320!!@192.168.0.38:554/stream1')
_webcam_started = False

# 공통 모듈
# FIXME: backend. 제거
from src.common import init_app, log_system

# 서비스 모듈
# FIXME: backend. 제거
from src.controller import (
    auth_bp,
    board_bp,
    faq_bp,
    introduce_bp,
    mypage_bp,
    profile_bp,
    tip_bp,
    model_bp,
    admin_bp,
)
# FIXME end

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
camera = cv2.VideoCapture(0, cv2.CAP_V4L2)

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')

# Cache 설정
cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app)
init_app(app)
# CSRF 보호 활성화 (이걸 해야 write.html의 csrf_token()이 작동함)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
_stream_started = False

# 메인 페이지 라우트
@app.route('/')
def index():
    log_system('VISIT','INFO','PAGE_VIEW','/')
    return render_template('main.html')

@app.route('/swagger-index.html')
def swagger():
    return render_template('api_docs.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@socketio.on('connect')
def handle_connect():
    print("[DEBUG] 클라이언트 연결됨!")  # ← 추가
    global _stream_started
    if not _stream_started:
        _stream_started = True
        print("[DEBUG] 백그라운드 태스크 시작!")  # ← 추가
        socketio.start_background_task(
            AiStreamService.run_rtsp_stream, socketio, RTSP_URL
        )

@socketio.on('disconnect')
def handle_disconnect():
    global _stream_started
    _stream_started = False

@socketio.on('set_detection_target')
def handle_target(data):
    AiStreamService.set_target(data.get('target', ''))

@socketio.on('start_webcam')
def handle_webcam():
    global _webcam_started
    print("[DEBUG] 웹캠 시작 요청!", flush=True)
    if not _webcam_started:
        _webcam_started = True
        socketio.start_background_task(
            WebCamService.run_webcam_stream, socketio, 1
        )

@socketio.on('stop_webcam')
def handle_stop_webcam():
    """브라우저에서 웹캠 중지 버튼을 눌렀을 때 호출됨"""
    print("[DEBUG] 웹캠 분석 중지 요청 수신", flush=True)
    # 이미지 전송 방식에서는 서버가 직접 정지시킬 장치가 없으므로 
    # 아무것도 하지 않고 로직을 마칩니다.
    return True

@app.route('/api/its/cctv')
def get_its_cctv():
    # 복잡한 로직은 Service에서 처리하고, 여기선 호출만!
    return CctvService.get_its_cctv_data()


def gen_frames():
    # 카메라가 열리지 않았을 경우를 대비해 여기서 다시 한번 체크할 수 있습니다.
    if not camera.isOpened():
        print("[ERROR] 카메라 장치를 열 수 없습니다. /dev/video 확인 필요")
        return

    while True:
        success, frame = camera.read()
        if not success:
            print("[DEBUG] 프레임을 읽을 수 없습니다.")
            break
        else:
            # 리사이징 (성능 최적화 - 생략 가능)
            # frame = cv2.resize(frame, (640, 480))
            
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@socketio.on('webcam_frame_transmit')
def handle_webcam_transmit(data):
    image_base64 = data.get('image')
    target = data.get('target', '')
    
    # WebCamService에서 추론 실행
    result = WebCamService.predict_frame(image_base64, target)
    
    if result:
        # 결과를 다시 'webcam_result'라는 이름으로 클라이언트에 전송
        socketio.emit('webcam_result', {
            'image': result['image'],
            'detected': result['detected']
        })
# Blueprint 등록
# FIXME : app.py에 등록할 때 항상 url_prefix를 붙여서 넣기, 반드시 이 부분만 수정해주세요
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(mypage_bp, url_prefix='/mypage')
app.register_blueprint(introduce_bp, url_prefix='/introduce')
app.register_blueprint(board_bp, url_prefix='/board')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(faq_bp, url_prefix='/faq')
app.register_blueprint(tip_bp, url_prefix='/tip')
app.register_blueprint(model_bp, url_prefix='/model')
app.register_blueprint(profile_bp, url_prefix='/profile')
# FIXME end



if __name__ == '__main__':
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.getenv('FLASK_APP_PORT', 1210)),
        debug=False
    )
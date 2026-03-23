"""
야생동물 Detection 테스트 스크립트
모델: YOLO (best.pt)
입력: water_deer_test.mp4
"""

from ultralytics import YOLO
import cv2
import os

# ===================== 경로 설정 =====================
MODEL_PATH = "best.pt"
VIDEO_PATH = "boar_1.mp4"
OUTPUT_PATH = "boar_result_1.mp4"
# ====================================================

# 신뢰도 임계값 (0~1, 낮출수록 더 많이 검출)
CONFIDENCE = 0.25


def run_detection():
    # 모델 로드
    print(f"[1/3] 모델 로드 중: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
    print(f"      클래스 목록: {model.names}")

    # 영상 정보 확인
    cap = cv2.VideoCapture(VIDEO_PATH)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    print(f"[2/3] 영상 정보: {w}x{h}, {fps:.1f}fps, 총 {total_frames}프레임")

    # Detection 실행
    print(f"[3/3] Detection 시작 (conf={CONFIDENCE}) ...")
    results = model.predict(
        source=VIDEO_PATH,
        save=True,              # 결과 영상 저장
        conf=CONFIDENCE,
        project="vastai",
        name="result",
        exist_ok=True,
        stream=True,            # 메모리 절약
        verbose=False,
    )

    # 프레임별 통계
    total_detections = 0
    frame_idx = 0

    for result in results:
        n = len(result.boxes) if result.boxes else 0
        total_detections += n
        frame_idx += 1
        if frame_idx % 30 == 0:
            print(f"   프레임 {frame_idx}/{total_frames} | 이번 프레임 검출: {n}개")

    print("\n========== 결과 요약 ==========")
    print(f"총 처리 프레임 : {frame_idx}")
    print(f"총 검출 횟수   : {total_detections}")
    print(f"프레임당 평균  : {total_detections / max(frame_idx, 1):.2f}개")
    print(f"결과 저장 위치 : vastai/result/")
    print("================================\n")


if __name__ == "__main__":
    # 파일 존재 확인
    for path in [MODEL_PATH, VIDEO_PATH]:
        if not os.path.exists(path):
            print(f"[오류] 파일을 찾을 수 없습니다: {path}")
            print("       스크립트와 같은 위치에서 실행했는지 확인하세요.")
            exit(1)

    run_detection()
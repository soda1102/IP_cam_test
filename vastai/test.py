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
# 사진(.jpg, .png) 또는 영상(.mp4, .avi) 경로를 자유롭게 넣으세요
INPUT_PATH = "water_deer_test.jpg"  # <-- 여기에 파일명만 바꾸면 됨
CONFIDENCE = 0.25


# ====================================================

def run_detection():
    # 1. 파일 존재 확인
    if not os.path.exists(INPUT_PATH):
        print(f"[오류] 파일을 찾을 수 없습니다: {INPUT_PATH}")
        return

    # 2. 모델 로드
    print(f"[1/2] 모델 로드 중: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)

    # 3. 입력 파일 종류 확인 (사진인지 영상인지)
    is_image = INPUT_PATH.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))
    print(f"      탐지 대상: {'[사진]' if is_image else '[영상]'}")

    # 4. Detection 실행
    print(f"[2/2] Detection 시작 (conf={CONFIDENCE}) ...")

    # 영상이면 stream=True로 메모리 절약, 사진이면 일반 리스트로 받음
    results = model.predict(
        source=INPUT_PATH,
        save=True,
        conf=CONFIDENCE,
        project="vastai",
        name="test_result",
        exist_ok=True,
        stream=not is_image,  # 영상일 때만 스트리밍 모드
        verbose=False
    )

    # 5. 결과 출력 (사진/영상 별도 처리)
    if is_image:
        # 사진은 결과가 딱 하나임
        result = list(results)[0]
        print("\n========== [사진 결과] ==========")
        print(f"검출된 객체 수: {len(result.boxes)}개")
        for box in result.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            print(f" - {model.names[cls]}: {conf:.2%}")
    else:
        # 영상은 루프 돌면서 요약
        total_detections = 0
        frame_idx = 0
        for r in results:
            total_detections += len(r.boxes)
            frame_idx += 1
            if frame_idx % 30 == 0:
                print(f"   프레임 {frame_idx} 처리 중...")

        print("\n========== [영상 요약] ==========")
        print(f"총 처리 프레임 : {frame_idx}")
        print(f"총 검출 횟수   : {total_detections}")

    print(f"결과 저장 위치 : vastai/test_result/")
    print("================================\n")


if __name__ == "__main__":
    if not os.path.exists(MODEL_PATH):
        print(f"[오류] 모델 파일을 찾을 수 없습니다: {MODEL_PATH}")
    else:
        run_detection()
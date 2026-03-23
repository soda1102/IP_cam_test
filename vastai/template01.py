# 1. 필요한 패키지 설치
# !pip install ultralytics roboflow matplotlib pandas

# =============================================
# ⬇️ 조원마다 여기 MODEL_NAME 만 바꾸면 됨!
MODEL_NAME = "yolo11n"  # n / s / m / l / x
# =============================================

# 고정 파라미터 (모든 조원 동일)
EPOCHS    = 100
BATCH     = 16
IMGSZ     = 640
OPTIMIZER = "SGD"

import os
import time
import yaml
import urllib.request
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from ultralytics import YOLO
from roboflow import Roboflow

# =============================================
# 2. HuggingFace에서 pretrained 모델 다운로드
# =============================================
model_file = f"{MODEL_NAME}.pt"
url = f"https://huggingface.co/Ultralytics/YOLO11/resolve/main/{model_file}?download=true"

if not os.path.exists(model_file):
    print(f"{model_file} 다운로드 중...")
    urllib.request.urlretrieve(url, model_file)
    print("다운로드 완료!")
else:
    print(f"{model_file} 이미 존재함, 스킵")

# =============================================
# 3. Roboflow에서 데이터셋 불러오기
# =============================================
rf = Roboflow(api_key="여기에_API_KEY_입력")
project = rf.workspace("워크스페이스_이름").project("프로젝트_이름")
version = project.version(1)
dataset = version.download("yolov8")

# data.yaml 없을 경우 자동 생성
yaml_path = f"{dataset.location}/data.yaml"
if not os.path.exists(yaml_path):
    print("data.yaml 없음 → 자동 생성")
    yaml_content = {
        'path': dataset.location,
        'train': 'train/images',
        'val': 'valid/images',
        'test': 'test/images',
        'nc': 3,  # ← 클래스 수 맞게 수정
        'names': ['클래스1', '클래스2', '클래스3']  # ← 클래스명 맞게 수정
    }
    with open(yaml_path, 'w') as f:
        yaml.dump(yaml_content, f, allow_unicode=True)
    print(f"data.yaml 생성 완료: {yaml_path}")

# =============================================
# 4. 학습 (시간 측정 포함)
# =============================================
model = YOLO(model_file)

print(f"\n🚀 {MODEL_NAME} 학습 시작...")
start_time = time.time()

model.train(
    data=yaml_path,
    epochs=EPOCHS,
    batch=BATCH,
    imgsz=IMGSZ,
    optimizer=OPTIMIZER,
    name=f"result_{MODEL_NAME}",
    device=0,
    pretrained=True
)

end_time = time.time()
train_time = end_time - start_time
train_time_str = f"{int(train_time // 3600)}h {int((train_time % 3600) // 60)}m {int(train_time % 60)}s"
print(f"\n⏱ 학습 시간: {train_time_str}")

# =============================================
# 5. 검증 및 최종 성능 요약 출력
# =============================================
result_dir = f"runs/detect/result_{MODEL_NAME}"
val_results = model.val()

map50    = float(val_results.box.map50)
map5095  = float(val_results.box.map)
precision = float(val_results.box.p.mean())
recall    = float(val_results.box.r.mean())

print("\n" + "="*50)
print(f"📊 최종 성능 요약 - {MODEL_NAME}")
print("="*50)
print(f"  mAP@50       : {map50:.4f}")
print(f"  mAP@50-95    : {map5095:.4f}")
print(f"  Precision    : {precision:.4f}")
print(f"  Recall       : {recall:.4f}")
print(f"  학습 시간     : {train_time_str}")
print("="*50)

# =============================================
# 6. 결과 CSV에 저장 (조원 결과 누적)
# =============================================
summary_csv = "all_results.csv"
new_row = pd.DataFrame([{
    "model":     MODEL_NAME,
    "mAP50":     round(map50, 4),
    "mAP50-95":  round(map5095, 4),
    "precision": round(precision, 4),
    "recall":    round(recall, 4),
    "train_time": train_time_str
}])

if os.path.exists(summary_csv):
    existing = pd.read_csv(summary_csv)
    # 같은 모델 결과는 덮어쓰기
    existing = existing[existing["model"] != MODEL_NAME]
    combined = pd.concat([existing, new_row], ignore_index=True)
else:
    combined = new_row

combined.to_csv(summary_csv, index=False)
print(f"\n✅ 결과 저장 완료: {summary_csv}")

# =============================================
# 7. 학습 그래프 출력 (Loss / Accuracy)
# =============================================
csv_path = f"{result_dir}/results.csv"
df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()

fig, axes = plt.subplots(2, 3, figsize=(16, 10))
fig.suptitle(f"YOLOv11 학습 결과 - {MODEL_NAME}", fontsize=16, fontweight='bold')

axes[0, 0].plot(df['epoch'], df['train/box_loss'], label='Train', color='blue')
axes[0, 0].plot(df['epoch'], df['val/box_loss'],   label='Val',   color='orange')
axes[0, 0].set_title('Box Loss')
axes[0, 0].set_xlabel('Epoch')
axes[0, 0].legend()
axes[0, 0].grid(True)

axes[0, 1].plot(df['epoch'], df['train/cls_loss'], label='Train', color='blue')
axes[0, 1].plot(df['epoch'], df['val/cls_loss'],   label='Val',   color='orange')
axes[0, 1].set_title('Class Loss')
axes[0, 1].set_xlabel('Epoch')
axes[0, 1].legend()
axes[0, 1].grid(True)

axes[0, 2].plot(df['epoch'], df['train/dfl_loss'], label='Train', color='blue')
axes[0, 2].plot(df['epoch'], df['val/dfl_loss'],   label='Val',   color='orange')
axes[0, 2].set_title('DFL Loss')
axes[0, 2].set_xlabel('Epoch')
axes[0, 2].legend()
axes[0, 2].grid(True)

axes[1, 0].plot(df['epoch'], df['metrics/precision(B)'], label='Precision', color='green')
axes[1, 0].plot(df['epoch'], df['metrics/recall(B)'],    label='Recall',    color='red')
axes[1, 0].set_title('Precision & Recall')
axes[1, 0].set_xlabel('Epoch')
axes[1, 0].legend()
axes[1, 0].grid(True)

axes[1, 1].plot(df['epoch'], df['metrics/mAP50(B)'],    label='mAP@50',    color='purple')
axes[1, 1].plot(df['epoch'], df['metrics/mAP50-95(B)'], label='mAP@50-95', color='brown')
axes[1, 1].set_title('mAP (Accuracy)')
axes[1, 1].set_xlabel('Epoch')
axes[1, 1].legend()
axes[1, 1].grid(True)

axes[1, 2].plot(df['epoch'], df['train/box_loss'] + df['train/cls_loss'] + df['train/dfl_loss'], label='Train Total', color='blue')
axes[1, 2].plot(df['epoch'], df['val/box_loss']   + df['val/cls_loss']   + df['val/dfl_loss'],   label='Val Total',   color='orange')
axes[1, 2].set_title('Total Loss')
axes[1, 2].set_xlabel('Epoch')
axes[1, 2].legend()
axes[1, 2].grid(True)

plt.tight_layout()
graph_path = f"{result_dir}/training_graph_{MODEL_NAME}.png"
plt.savefig(graph_path, dpi=150, bbox_inches='tight')
plt.show()
print(f"✅ 학습 그래프 저장: {graph_path}")

# =============================================
# 8. Confusion Matrix 출력
# =============================================
model.val(plots=True)  # confusion_matrix.png 자동 생성
cm_path = f"{result_dir}/confusion_matrix.png"
if os.path.exists(cm_path):
    img = plt.imread(cm_path)
    plt.figure(figsize=(10, 8))
    plt.imshow(img)
    plt.axis('off')
    plt.title(f'Confusion Matrix - {MODEL_NAME}')
    plt.tight_layout()
    plt.show()
    print(f"✅ Confusion Matrix 저장: {cm_path}")

# =============================================
# 9. 추론 테스트 (val 이미지로 샘플 확인)
# =============================================
best_model = YOLO(f"{result_dir}/weights/best.pt")

# val 이미지 중 최대 5장 추론
val_img_dir = f"{dataset.location}/valid/images"
sample_imgs = [
    os.path.join(val_img_dir, f)
    for f in os.listdir(val_img_dir)
    if f.endswith(('.jpg', '.jpeg', '.png'))
][:5]

print(f"\n🔍 추론 테스트 ({len(sample_imgs)}장)...")
infer_results = best_model.predict(source=sample_imgs, save=True, conf=0.25)

fig, axes = plt.subplots(1, len(sample_imgs), figsize=(4 * len(sample_imgs), 4))
if len(sample_imgs) == 1:
    axes = [axes]

for ax, r in zip(axes, infer_results):
    ax.imshow(r.plot()[:, :, ::-1])
    ax.axis('off')

fig.suptitle(f"추론 결과 샘플 - {MODEL_NAME}", fontsize=14, fontweight='bold')
plt.tight_layout()
infer_path = f"{result_dir}/inference_sample_{MODEL_NAME}.png"
plt.savefig(infer_path, dpi=150, bbox_inches='tight')
plt.show()
print(f"✅ 추론 샘플 저장: {infer_path}")

# =============================================
# 10. 조원 결과 비교 그래프 (all_results.csv 기반)
# =============================================
if os.path.exists(summary_csv):
    df_all = pd.read_csv(summary_csv)
    model_order = ["yolo11n", "yolo11s", "yolo11m", "yolo11l", "yolo11x"]
    df_all["model"] = pd.Categorical(df_all["model"], categories=model_order, ordered=True)
    df_all = df_all.sort_values("model")

    if len(df_all) > 1:
        x = range(len(df_all))
        width = 0.2

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar([i - width*1.5 for i in x], df_all["mAP50"],     width, label="mAP@50",     color='purple')
        ax.bar([i - width*0.5 for i in x], df_all["mAP50-95"],  width, label="mAP@50-95",  color='brown')
        ax.bar([i + width*0.5 for i in x], df_all["precision"], width, label="Precision",   color='green')
        ax.bar([i + width*1.5 for i in x], df_all["recall"],    width, label="Recall",      color='red')

        ax.set_xticks(x)
        ax.set_xticklabels(df_all["model"])
        ax.set_ylim(0, 1.1)
        ax.set_title("모델별 성능 비교", fontsize=14, fontweight='bold')
        ax.set_xlabel("Model")
        ax.set_ylabel("Score")
        ax.legend()
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        plt.tight_layout()
        compare_path = "model_comparison.png"
        plt.savefig(compare_path, dpi=150, bbox_inches='tight')
        plt.show()
        print(f"✅ 모델 비교 그래프 저장: {compare_path}")
    else:
        print("ℹ️ 조원 결과가 2개 이상 모이면 비교 그래프가 출력됩니다.")

# =============================================
# 최종 요약
# =============================================
print("\n" + "="*50)
print(f"🎉 전체 완료 - {MODEL_NAME}")
print("="*50)
print(f"  학습 그래프  : {graph_path}")
print(f"  Confusion Matrix: {cm_path}")
print(f"  추론 샘플    : {infer_path}")
print(f"  결과 CSV     : {summary_csv}")
print(f"  best.pt      : {result_dir}/weights/best.pt")
print("="*50)
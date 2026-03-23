# 1. 필요한 패키지 설치
# %pip install ultralytics roboflow matplotlib pandas


# =============================================
# ⬇️ 조원마다 여기 MODEL_NAME 만 바꾸면 됨!
MODEL_NAME = "yolo11l"  # n / s / m / l / x
# =============================================

EPOCHS    = 100
BATCH     = 16
IMGSZ     = 640
OPTIMIZER = "SGD"
BASE      = "MBCAcademy3Team-4"

import os, time, json, shutil, random, yaml, urllib.request
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from ultralytics import YOLO
from roboflow import Roboflow

# 한글 폰트 설정
# !apt-get install -y fonts-nanum > /dev/null 2>&1
font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

# =============================================
# 1. 모델 다운로드
# =============================================
model_file = f"{MODEL_NAME}.pt"
url = f"https://huggingface.co/Ultralytics/YOLO11/resolve/main/{model_file}?download=true"
if not os.path.exists(model_file):
    print(f"{model_file} 다운로드 중...")
    urllib.request.urlretrieve(url, model_file)
    print("완료!")
else:
    print(f"{model_file} 이미 존재, 스킵")

# =============================================
# 2. Roboflow 데이터셋 다운로드
# =============================================
if not os.path.exists(BASE):
    print("Roboflow 데이터셋 다운로드 중...")
    rf = Roboflow(api_key="로보플로우API키")
    project = rf.workspace("워크스페이스ID").project("프로젝트ID")
    version = project.version(4)
    dataset = version.download("coco", location=f"/{BASE}", overwrite=False)
    print(f"✅ 다운로드 완료: {dataset.location}")
else:
    print(f"ℹ️ {BASE} 이미 존재, 다운로드 스킵")

# =============================================
# 3. 데이터셋 준비 (COCO → YOLO 변환 + train/valid 분리)
# =============================================
def setup_dataset(base):
    for split in ['train', 'test']:
        img_dir = f"{base}/{split}/images"
        lbl_dir = f"{base}/{split}/labels"
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(lbl_dir, exist_ok=True)
        moved = 0
        for f in os.listdir(f"{base}/{split}"):
            if f.endswith(('.jpg', '.jpeg', '.png')):
                shutil.move(f"{base}/{split}/{f}", f"{img_dir}/{f}")
                moved += 1
        if moved > 0:
            print(f"✅ {split} 이미지 {moved}장 이동 완료")
        else:
            print(f"ℹ️ {split} 이미지 이미 이동됨, 스킵")

    def coco_to_yolo(json_path, label_dir):
        if not os.path.exists(json_path):
            print(f"⚠️ {json_path} 없음, 스킵")
            return
        with open(json_path) as f:
            data = json.load(f)
        categories = {
            cat['id']: idx for idx, cat in enumerate(
                [c for c in data['categories'] if c['supercategory'] != 'none']
            )
        }
        images = {img['id']: img for img in data['images']}
        labels = {}
        for ann in data['annotations']:
            img_info = images[ann['image_id']]
            img_w, img_h = img_info['width'], img_info['height']
            x, y, w, h = ann['bbox']
            cx = (x + w/2) / img_w
            cy = (y + h/2) / img_h
            nw = w / img_w
            nh = h / img_h
            cls_idx = categories.get(ann['category_id'])
            if cls_idx is None:
                continue
            fname = os.path.splitext(img_info['file_name'])[0] + '.txt'
            labels.setdefault(fname, []).append(
                f"{cls_idx} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}"
            )
        for fname, lines in labels.items():
            with open(f"{label_dir}/{fname}", 'w') as f:
                f.write('\n'.join(lines))
        print(f"✅ {label_dir} 라벨 {len(labels)}개 변환 완료")

    coco_to_yolo(f"{base}/train/_annotations.coco.json", f"{base}/train/labels")
    coco_to_yolo(f"{base}/test/_annotations.coco.json",  f"{base}/test/labels")

    valid_img_dir = f"{base}/valid/images"
    valid_lbl_dir = f"{base}/valid/labels"
    if os.path.exists(valid_img_dir) and len(os.listdir(valid_img_dir)) > 0:
        print("ℹ️ valid 이미 존재, 스킵")
    else:
        os.makedirs(valid_img_dir, exist_ok=True)
        os.makedirs(valid_lbl_dir, exist_ok=True)
        imgs = [f for f in os.listdir(f"{base}/train/images")
                if f.endswith(('.jpg', '.jpeg', '.png'))]
        random.seed(42)
        random.shuffle(imgs)
        val_count = int(len(imgs) * 0.2)
        for img in imgs[:val_count]:
            shutil.move(f"{base}/train/images/{img}", f"{valid_img_dir}/{img}")
            lbl = img.rsplit('.', 1)[0] + '.txt'
            lbl_src = f"{base}/train/labels/{lbl}"
            if os.path.exists(lbl_src):
                shutil.move(lbl_src, f"{valid_lbl_dir}/{lbl}")
        print(f"✅ train: {len(imgs)-val_count}장 / valid: {val_count}장")

    yaml_content = {
        'path':  f'/{base}',
        'train': 'train/images',
        'val':   'valid/images',
        'test':  'test/images',
        'nc': 5,
        'names': ['boar', 'chipmunk', 'hare', 'heron', 'water_deer']
    }
    with open(f"{base}/data.yaml", 'w') as f:
        yaml.dump(yaml_content, f)
    print("✅ data.yaml 생성 완료 (nc=5)")

setup_dataset(BASE)
yaml_path = f"{BASE}/data.yaml"

with open(yaml_path) as f:
    print("\n📄 data.yaml 내용:")
    print(f.read())

# =============================================
# 4. 학습
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
    pretrained=True,
    exist_ok=True,
    plots=True,
    save=True,
)

end_time = time.time()
train_time = end_time - start_time
train_time_str = f"{int(train_time//3600)}h {int((train_time%3600)//60)}m {int(train_time%60)}s"
print(f"\n⏱ 학습 시간: {train_time_str}")

# =============================================
# 5. 검증 및 성능 요약
# =============================================
result_dir = f"runs/detect/result_{MODEL_NAME}"
val_results = model.val()

map50     = float(val_results.box.map50)
map5095   = float(val_results.box.map)
precision = float(val_results.box.p.mean())
recall    = float(val_results.box.r.mean())

print("\n" + "="*50)
print(f"📊 최종 성능 요약 - {MODEL_NAME}")
print("="*50)
print(f"  mAP@50    : {map50:.4f}")
print(f"  mAP@50-95 : {map5095:.4f}")
print(f"  Precision : {precision:.4f}")
print(f"  Recall    : {recall:.4f}")
print(f"  학습 시간  : {train_time_str}")
print("="*50)

# =============================================
# 6. 결과 CSV 저장
# =============================================
summary_csv = "all_results.csv"
new_row = pd.DataFrame([{
    "model":      MODEL_NAME,
    "mAP50":      round(map50, 4),
    "mAP50-95":   round(map5095, 4),
    "precision":  round(precision, 4),
    "recall":     round(recall, 4),
    "train_time": train_time_str
}])
if os.path.exists(summary_csv):
    existing = pd.read_csv(summary_csv)
    existing = existing[existing["model"] != MODEL_NAME]
    combined = pd.concat([existing, new_row], ignore_index=True)
else:
    combined = new_row
combined.to_csv(summary_csv, index=False)
print(f"✅ 결과 저장: {summary_csv}")

# =============================================
# 7. 학습 그래프
# =============================================
csv_path = f"{result_dir}/results.csv"
df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()

fig, axes = plt.subplots(2, 3, figsize=(16, 10))
fig.suptitle(f"YOLOv11 Training Result - {MODEL_NAME}", fontsize=16, fontweight='bold')

axes[0,0].plot(df['epoch'], df['train/box_loss'], label='Train', color='blue')
axes[0,0].plot(df['epoch'], df['val/box_loss'],   label='Val',   color='orange')
axes[0,0].set_title('Box Loss'); axes[0,0].set_xlabel('Epoch')
axes[0,0].legend(); axes[0,0].grid(True)

axes[0,1].plot(df['epoch'], df['train/cls_loss'], label='Train', color='blue')
axes[0,1].plot(df['epoch'], df['val/cls_loss'],   label='Val',   color='orange')
axes[0,1].set_title('Class Loss'); axes[0,1].set_xlabel('Epoch')
axes[0,1].legend(); axes[0,1].grid(True)

axes[0,2].plot(df['epoch'], df['train/dfl_loss'], label='Train', color='blue')
axes[0,2].plot(df['epoch'], df['val/dfl_loss'],   label='Val',   color='orange')
axes[0,2].set_title('DFL Loss'); axes[0,2].set_xlabel('Epoch')
axes[0,2].legend(); axes[0,2].grid(True)

axes[1,0].plot(df['epoch'], df['metrics/precision(B)'], label='Precision', color='green')
axes[1,0].plot(df['epoch'], df['metrics/recall(B)'],    label='Recall',    color='red')
axes[1,0].set_title('Precision & Recall'); axes[1,0].set_xlabel('Epoch')
axes[1,0].legend(); axes[1,0].grid(True)

axes[1,1].plot(df['epoch'], df['metrics/mAP50(B)'],    label='mAP@50',    color='purple')
axes[1,1].plot(df['epoch'], df['metrics/mAP50-95(B)'], label='mAP@50-95', color='brown')
axes[1,1].set_title('mAP (Accuracy)'); axes[1,1].set_xlabel('Epoch')
axes[1,1].legend(); axes[1,1].grid(True)

axes[1,2].plot(df['epoch'], df['train/box_loss']+df['train/cls_loss']+df['train/dfl_loss'], label='Train Total', color='blue')
axes[1,2].plot(df['epoch'], df['val/box_loss']+df['val/cls_loss']+df['val/dfl_loss'],       label='Val Total',   color='orange')
axes[1,2].set_title('Total Loss'); axes[1,2].set_xlabel('Epoch')
axes[1,2].legend(); axes[1,2].grid(True)

plt.tight_layout()
plt.savefig(f"{result_dir}/training_graph_{MODEL_NAME}.png", dpi=150, bbox_inches='tight')
plt.show()
print("✅ 학습 그래프 저장 완료")

# =============================================
# 8. Confusion Matrix + 기타 그래프
# =============================================
for fname in ['confusion_matrix_normalized.png', 'confusion_matrix.png',
              'BoxPR_curve.png', 'BoxF1_curve.png', 'BoxP_curve.png', 'BoxR_curve.png']:
    fpath = f"{result_dir}/{fname}"
    if os.path.exists(fpath):
        img = plt.imread(fpath)
        plt.figure(figsize=(10, 7))
        plt.imshow(img)
        plt.axis('off')
        plt.title(f'{fname.replace(".png","")} - {MODEL_NAME}')
        plt.tight_layout()
        plt.show()

# =============================================
# 9. 추론 테스트
# =============================================
best_model = YOLO(f"{result_dir}/weights/best.pt")
val_img_dir = f"{BASE}/valid/images"
sample_imgs = [
    os.path.join(val_img_dir, f)
    for f in os.listdir(val_img_dir)
    if f.endswith(('.jpg', '.jpeg', '.png'))
][:5]

print(f"\n🔍 추론 테스트 ({len(sample_imgs)}장)...")
infer_results = best_model.predict(source=sample_imgs, save=True, conf=0.25)

fig, axes = plt.subplots(1, len(sample_imgs), figsize=(4*len(sample_imgs), 4))
if len(sample_imgs) == 1:
    axes = [axes]
for ax, r in zip(axes, infer_results):
    ax.imshow(r.plot()[:, :, ::-1])
    ax.axis('off')

fig.suptitle(f"Inference Sample - {MODEL_NAME}", fontsize=14, fontweight='bold')
plt.tight_layout()
infer_path = f"{result_dir}/inference_sample_{MODEL_NAME}.png"
plt.savefig(infer_path, dpi=150, bbox_inches='tight')
plt.show()
print(f"✅ 추론 샘플 저장: {infer_path}")

# =============================================
# 10. 조원 비교 그래프
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
        ax.bar([i-width*1.5 for i in x], df_all["mAP50"],     width, label="mAP@50",     color='purple')
        ax.bar([i-width*0.5 for i in x], df_all["mAP50-95"],  width, label="mAP@50-95",  color='brown')
        ax.bar([i+width*0.5 for i in x], df_all["precision"], width, label="Precision",   color='green')
        ax.bar([i+width*1.5 for i in x], df_all["recall"],    width, label="Recall",      color='red')
        ax.set_xticks(x); ax.set_xticklabels(df_all["model"])
        ax.set_ylim(0, 1.1)
        ax.set_title("Model Performance Comparison", fontsize=14, fontweight='bold')
        ax.set_xlabel("Model"); ax.set_ylabel("Score")
        ax.legend(); ax.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig("model_comparison.png", dpi=150, bbox_inches='tight')
        plt.show()
        print("✅ 모델 비교 그래프 저장 완료")
    else:
        print("ℹ️ 조원 결과 2개 이상 모이면 비교 그래프 출력됩니다.")

# =============================================
# 최종 요약
# =============================================
print("\n" + "="*50)
print(f"🎉 전체 완료 - {MODEL_NAME}")
print("="*50)
print(f"  best.pt  : {result_dir}/weights/best.pt")
print(f"  결과 CSV : {summary_csv}")
print("="*50)
// ════════════════════════════════════════
// DOM 요소
// ════════════════════════════════════════
const fileInput        = document.getElementById('videoFile');
const startBtn         = document.getElementById('startBtn');
const statusText       = document.getElementById('statusText');
const progressBar      = document.getElementById('analysisProgress');
const videoStream      = document.getElementById('videoStream');
const videoPlayer      = document.getElementById('videoPlayer');
const videoThumbnail   = document.getElementById('videoThumbnail');
const analyzingOverlay = document.getElementById('analyzingOverlay');
const overlayCanvas    = document.getElementById('overlayCanvas');
const drawCtx          = overlayCanvas.getContext('2d');

let lastResult    = null;
let currentFile   = null;
let progressTimer = null;

// ════════════════════════════════════════
// 썸네일 생성
// ════════════════════════════════════════
function generateVideoThumbnail(file) {
    return new Promise(resolve => {
        const url      = URL.createObjectURL(file);
        const tmpVideo = document.createElement('video');
        tmpVideo.muted   = true;
        tmpVideo.preload = 'auto';
        tmpVideo.src     = url;

        tmpVideo.addEventListener('loadeddata', () => {
            tmpVideo.currentTime = 0.5;
        });

        tmpVideo.addEventListener('seeked', () => {
            const canvas  = document.createElement('canvas');
            canvas.width  = tmpVideo.videoWidth  || 640;
            canvas.height = tmpVideo.videoHeight || 360;
            canvas.getContext('2d').drawImage(tmpVideo, 0, 0, canvas.width, canvas.height);
            URL.revokeObjectURL(url);
            resolve(canvas.toDataURL('image/jpeg', 0.8));
        });

        setTimeout(() => {
            URL.revokeObjectURL(url);
            resolve('');
        }, 3000);

        tmpVideo.load();
    });
}

// ════════════════════════════════════════
// 파일 선택
// ════════════════════════════════════════
fileInput.onchange = async function () {
    if (!this.files?.length) return;
    currentFile = this.files[0];

    const isVideo = currentFile.type.startsWith('video/');

    startBtn.classList.replace('btn-outline-secondary', 'btn-teal');
    startBtn.disabled = false;
    document.getElementById('resultArea').style.display    = 'none';
    document.getElementById('placeholderUI').style.display = 'none';
    analyzingOverlay.style.display = 'none';
    drawCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

    statusText.innerText = '준비 완료: ' + currentFile.name;
    setProgress(0, false);

    // 모든 미디어 초기화
    videoStream.style.display    = 'none';
    videoPlayer.style.display    = 'none';
    videoThumbnail.style.display = 'none';

    if (isVideo) {
        statusText.innerText = '썸네일 생성 중...';
        const thumbURL = await generateVideoThumbnail(currentFile);
        if (thumbURL) {
            videoThumbnail.src           = thumbURL;
            videoThumbnail.style.display = 'block';
        } else {
            document.getElementById('placeholderUI').style.display = 'block';
        }
        statusText.innerText = '준비 완료: ' + currentFile.name;
    } else {
        videoStream.src           = URL.createObjectURL(currentFile);
        videoStream.style.display = 'block';
    }
};

// ════════════════════════════════════════
// 분석 시작
// ════════════════════════════════════════
document.getElementById('uploadForm').onsubmit = async function (e) {
    e.preventDefault();
    if (!currentFile) return;

    startBtn.disabled = true;
    document.getElementById('resultArea').style.display = 'none';
    setProgress(0, false);

    if (currentFile.type.startsWith('video/')) {
        await handleVideo();
    } else {
        await handleImage();
    }
};

// ════════════════════════════════════════
// 이미지 처리
// ════════════════════════════════════════
async function handleImage() {
    statusText.innerText = '이미지 분석 중...';
    setProgress(30, true);

    const tempCanvas  = document.createElement('canvas');
    tempCanvas.width  = videoStream.naturalWidth  || 640;
    tempCanvas.height = videoStream.naturalHeight || 480;
    tempCanvas.getContext('2d').drawImage(videoStream, 0, 0);

    // 1. 탐지 먼저
    let boar = 0, deer = 0, racoon = 0;
    const blob1 = await new Promise(resolve =>
        tempCanvas.toBlob(resolve, 'image/jpeg', 0.9)
    );
    try {
        const detectFd = new FormData();
        detectFd.append('file', blob1, currentFile.name);
        const detectRes  = await fetch('/model/detect', { method: 'POST', body: detectFd });
        const detectData = await detectRes.json();
        if (detectData.success) {
            boar   = detectData.counts[0] || 0;
            deer   = detectData.counts[1] || 0;
            racoon = detectData.counts[2] || 0;
            drawBoundingBoxes(detectData.detections);
        }
    } catch (err) {
        console.error('탐지 오류:', err);
    }

    setProgress(60, true);
    statusText.innerText = '분석 결과 저장 중...';

    // 2. counts 확보 후 저장
    const blob2 = await new Promise(resolve =>
        tempCanvas.toBlob(resolve, 'image/jpeg', 0.9)
    );
    const formData = new FormData();
    formData.append('file',              blob2, currentFile.name);
    formData.append('original_filename', currentFile.name);
    formData.append('boar_count',        boar);
    formData.append('water_deer_count',  deer);
    formData.append('racoon_count',      racoon);

    try {
        const res  = await fetch('/model/detect_and_save', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            setProgress(100, false);
            statusText.innerText = '✅ 분석 및 저장 완료!';
            showSavedLink(data.url, false);
        } else {
            statusText.innerText = '❌ 오류: ' + (data.message || '저장 실패');
            setProgress(0, false);
        }
    } catch (err) {
        console.error(err);
        statusText.innerText = '❌ 서버 통신 오류';
        setProgress(0, false);
    } finally {
        startBtn.disabled = false;
    }
}

// ════════════════════════════════════════
// 영상 처리
// ════════════════════════════════════════
async function handleVideo() {
    videoThumbnail.style.display   = 'block';
    videoPlayer.style.display      = 'none';
    analyzingOverlay.style.display = 'flex';

    statusText.innerText = '영상 분석 중... 잠시만 기다려 주세요.';
    animateProgress(0, 90, 60000);

    const formData = new FormData();
    formData.append('file',              currentFile, currentFile.name);
    formData.append('original_filename', currentFile.name);
    formData.append('boar_count',        0);
    formData.append('water_deer_count',  0);
    formData.append('racoon_count',      0);

    try {
        const res  = await fetch('/model/analyze_and_save_video', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        analyzingOverlay.style.display = 'none';
        setProgress(100, false);

        if (data.success && data.url) {
            statusText.innerText = '✅ 분석 완료! 결과 영상을 재생합니다.';

            // Cloudinary URL에 mp4 변환 파라미터 추가
            let playUrl = data.url;
            if (playUrl.includes('cloudinary.com') && playUrl.includes('/upload/')) {
                playUrl = playUrl.replace('/upload/', '/upload/f_mp4,vc_auto/');
            }

            videoThumbnail.style.display = 'none';
            videoPlayer.style.display    = 'block';
            videoPlayer.innerHTML        = '';

            const source = document.createElement('source');
            source.src   = playUrl;
            source.type  = 'video/mp4';
            videoPlayer.appendChild(source);
            videoPlayer.load();

            videoPlayer.addEventListener('canplay', function onCanPlay() {
                videoPlayer.removeEventListener('canplay', onCanPlay);
                videoPlayer.play().catch(err => {
                    console.warn('자동재생 차단:', err);
                });
            });

            videoPlayer.addEventListener('error', function onError() {
                videoPlayer.removeEventListener('error', onError);
                console.error('영상 재생 오류 — URL:', playUrl);
                statusText.innerText = '✅ 저장 완료! 아래 링크에서 확인하세요.';
            });

            showSavedLink(playUrl, true);
        } else {
            statusText.innerText = '❌ 오류: ' + (data.message || '저장 실패');
            videoThumbnail.style.display = 'block';
        }
    } catch (err) {
        console.error(err);
        statusText.innerText = '❌ 서버 통신 오류';
        analyzingOverlay.style.display = 'none';
        setProgress(0, false);
    } finally {
        startBtn.disabled = false;
    }
}

// ════════════════════════════════════════
// 바운딩박스 (이미지용)
// ════════════════════════════════════════
function drawBoundingBoxes(detections) {
    const media = videoStream;
    if (!media.clientWidth) return;

    const mW = media.clientWidth,  mH = media.clientHeight;
    const nW  = media.naturalWidth  || mW;
    const nH  = media.naturalHeight || mH;
    const ratio          = nW / nH;
    const containerRatio = mW / mH;

    let dW, dH;
    if (ratio > containerRatio) { dW = mW; dH = mW / ratio; }
    else                        { dH = mH; dW = mH * ratio; }

    overlayCanvas.width  = dW;
    overlayCanvas.height = dH;
    overlayCanvas.style.left = media.offsetLeft + (mW - dW) / 2 + 'px';
    overlayCanvas.style.top  = media.offsetTop  + (mH - dH) / 2 + 'px';

    drawCtx.clearRect(0, 0, dW, dH);
    detections.forEach(det => {
        if (!det.bbox || parseFloat(det.conf) < 0.4) return;
        const [x1, y1, x2, y2] = det.bbox;
        const sx = x1 * dW, sy = y1 * dH;
        const bw = (x2 - x1) * dW, bh = (y2 - y1) * dH;

        drawCtx.strokeStyle = '#007BFF';
        drawCtx.lineWidth   = 3;
        drawCtx.strokeRect(sx, sy, bw, bh);

        const label    = `${det.label} ${det.conf}`;
        const labelBgH = 20;
        const labelY   = sy - labelBgH < 0 ? sy : sy - labelBgH;
        const textW    = drawCtx.measureText(label).width + 10;

        drawCtx.fillStyle = '#007BFF';
        drawCtx.fillRect(sx, labelY, textW, labelBgH);
        drawCtx.fillStyle = 'white';
        drawCtx.font      = 'bold 14px Pretendard';
        drawCtx.fillText(label, sx + 5, labelY + 15);
    });
}

window.addEventListener('resize', () => {
    if (lastResult) drawBoundingBoxes(lastResult);
});

// ════════════════════════════════════════
// 프로그레스바
// ════════════════════════════════════════
function setProgress(pct, animated) {
    if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
    progressBar.style.transition = 'width 0.3s ease-in-out';
    progressBar.style.width      = pct + '%';
    if (animated) progressBar.classList.add('progress-bar-animated');
    else          progressBar.classList.remove('progress-bar-animated');
}

function animateProgress(from, to, durationMs) {
    if (progressTimer) clearInterval(progressTimer);
    const steps    = 100;
    const interval = durationMs / steps;
    const step     = (to - from) / steps;
    let current    = from;

    progressBar.style.width = from + '%';
    progressBar.classList.add('progress-bar-animated');

    progressTimer = setInterval(() => {
        current += step;
        if (current >= to) {
            current = to;
            clearInterval(progressTimer);
            progressTimer = null;
        }
        progressBar.style.width = current + '%';
    }, interval);
}

// ════════════════════════════════════════
// 저장 완료 링크
// ════════════════════════════════════════
function showSavedLink(url, isVideo) {
    const ext  = isVideo ? '.mp4' : '.jpg';
    const name = `result_${currentFile?.name || 'analysis'}${ext}`;

    const resultArea = document.getElementById('resultArea');
    const savedLink  = document.getElementById('savedLink');

    savedLink.href     = url;
    savedLink.download = name;
    resultArea.style.display = 'block';
}
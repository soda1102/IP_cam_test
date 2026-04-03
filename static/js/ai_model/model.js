let totalCounts = [0, 0, 0];
const labels = ['멧돼지', '고라니', '너구리'];
let statChart = null;

function initChart() {
    const ctx = document.getElementById('statChart').getContext('2d');
    if (statChart !== null) {
        statChart.destroy();
    }
    statChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{ label: '누적 탐지 수', data: totalCounts, backgroundColor: '#20828A', borderRadius: 5 }]
        },
        options: {
            responsive: true,
            animation: { duration: 500 },
            scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
        }
    });
}

initChart();

const fileInput = document.getElementById('videoFile');
const startBtn = document.getElementById('startBtn');
const playBtn = document.getElementById('playBtn');
const playIcon = document.getElementById('playIcon');
const statusText = document.getElementById('statusText');
const progressBar = document.getElementById('analysisProgress');
const videoStream = document.getElementById('videoStream');
const videoPlayer = document.getElementById('videoPlayer');
const overlayCanvas = document.getElementById('overlayCanvas');
const drawCtx = overlayCanvas.getContext('2d');
const saveCloudBtn = document.getElementById('saveCloudBtn');

let analysisLoop = null;
let lastResult = null;
let isAnalysisActive = false;
let currentFile = null;
let isProcessing = false; // [추가] 현재 분석이 진행 중인지 확인하는 플래그

fileInput.onchange = function() {
    if(this.files && this.files.length > 0) {
        currentFile = this.files[0];
        stopAnalysis();
        resetData();
        const fileURL = URL.createObjectURL(currentFile);
        const isVideo = currentFile.type.startsWith('video/');

        startBtn.classList.replace('btn-outline-secondary', 'btn-teal');
        startBtn.disabled = false;
        if(saveCloudBtn) saveCloudBtn.disabled = true;

        statusText.innerText = "준비 완료: " + currentFile.name;
        progressBar.style.width = "0%";
        progressBar.classList.add('progress-bar-animated');
        document.getElementById('placeholderUI').style.display = 'none';

        if (isVideo) {
            videoStream.style.display = 'none';
            videoPlayer.style.display = 'block';
            videoPlayer.src = fileURL;
            videoPlayer.load();
            playBtn.style.display = 'block';
            playIcon.className = 'bi bi-play-circle-fill';
        } else {
            videoPlayer.style.display = 'none';
            videoStream.style.display = 'block';
            videoStream.src = fileURL;
            playBtn.style.display = 'none';
        }
        drawCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    }
};

function resetData() {
    totalCounts = [0, 0, 0];
    initChart();
    document.getElementById('detectionList').innerHTML = '<p class="text-muted small mb-0">분석을 시작하면 목록이 표시됩니다.</p>';
}

function toggleVideo() {
    if (videoPlayer.paused) {
        videoPlayer.play();
        playIcon.className = 'bi bi-pause-circle-fill';
        playBtn.style.display = 'block';
        setTimeout(() => { if (!videoPlayer.paused) playBtn.style.display = 'none'; }, 500);
        if (isAnalysisActive) startAnalysis();
    } else {
        videoPlayer.pause();
        playIcon.className = 'bi bi-play-circle-fill';
        playBtn.style.display = 'block';
        if (analysisLoop) { clearInterval(analysisLoop); analysisLoop = null; }
    }
}

playBtn.onclick = toggleVideo;
videoPlayer.onclick = toggleVideo;

function stopAnalysis() {
    if (analysisLoop) clearInterval(analysisLoop);
    analysisLoop = null;
    isAnalysisActive = false;
}

function startAnalysis() {
    if (analysisLoop) return;
    isAnalysisActive = true;

    // [추가] 분석 시작 시 영상 속도를 0.5배속으로 늦춤 (지연 현상 보정용)
    if (videoPlayer) {
        videoPlayer.playbackRate = 0.8;
    }

    analysisLoop = setInterval(() => {
        if (!videoPlayer.paused && !videoPlayer.ended && isAnalysisActive && !isProcessing) {
            analyzeFrame(videoPlayer);
        }
    }, 500);
}

// [추가] 분석이 완전히 끝났을 때 속도를 다시 1.0으로 복구하는 부분
videoPlayer.onended = () => {
    videoPlayer.playbackRate = 1.0; // 속도 복구
    if (isAnalysisActive) {
        stopAnalysis();
        progressBar.style.transition = 'width 0.3s ease-in-out';
        progressBar.style.width = "100%";
        statusText.innerText = "분석 완료!";
        progressBar.classList.remove('progress-bar-animated');
        if(saveCloudBtn) saveCloudBtn.disabled = false;
    } else {
        playBtn.style.display = 'block';
        playIcon.className = 'bi bi-play-circle-fill';
    }
};

document.getElementById('uploadForm').onsubmit = async function(e) {
    e.preventDefault();
    const file = currentFile;
    if (!file) return;

    resetData();
    isAnalysisActive = true;
    if(saveCloudBtn) saveCloudBtn.disabled = true;

    progressBar.style.transition = 'none';
    progressBar.style.width = "0%";

    if (file.type.startsWith('video/')) {
        videoPlayer.pause();
        videoPlayer.currentTime = 0;
    }

    setTimeout(async () => {
        progressBar.style.transition = 'width 2.0s ease-out';
        progressBar.style.width = "85%";
        progressBar.classList.add('progress-bar-animated');
        statusText.innerText = "분석 진행 중...";

        if (file.type.startsWith('video/')) {
            playBtn.style.display = 'none';
            videoPlayer.play();
            startAnalysis();
        } else {
            await analyzeFrame(videoStream);
            progressBar.style.transition = 'width 0.3s ease-in-out';
            progressBar.style.width = "100%";
            statusText.innerText = "분석 완료!";
            progressBar.classList.remove('progress-bar-animated');
            if(saveCloudBtn) saveCloudBtn.disabled = false;
        }
    }, 10);
};

videoPlayer.onended = () => {
    if (isAnalysisActive) {
        stopAnalysis();
        progressBar.style.transition = 'width 0.3s ease-in-out';
        progressBar.style.width = "100%";
        statusText.innerText = "분석 완료!";
        progressBar.classList.remove('progress-bar-animated');
        if(saveCloudBtn) saveCloudBtn.disabled = false;
    } else {
        playBtn.style.display = 'block';
        playIcon.className = 'bi bi-play-circle-fill';
    }
};

function analyzeFrame(mediaElement) {
    return new Promise((resolve) => {
        isProcessing = true;
        const tempCanvas = document.createElement('canvas');

        // [수정] 640px도 무겁습니다. CPU 환경이면 320px까지 줄여보세요.
        const scale = Math.min(1, 320 / Math.max(mediaElement.videoWidth || mediaElement.naturalWidth, 1));

        tempCanvas.width = (mediaElement.videoWidth || mediaElement.naturalWidth) * scale;
        tempCanvas.height = (mediaElement.videoHeight || mediaElement.naturalHeight) * scale;

        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.drawImage(mediaElement, 0, 0, tempCanvas.width, tempCanvas.height);

        tempCanvas.toBlob(async (blob) => {
            const formData = new FormData();
            formData.append('file', blob, 'frame.jpg');
            try {
                const response = await fetch('/model/detect', { method: 'POST', body: formData });
                const result = await response.json();
                if (result.success) {
                    lastResult = result.detections;
                    accumulateData(result);
                    drawBoundingBoxes(result.detections); // 좌표는 비율(xyxyn)이므로 작게 보내도 박스 위치는 맞습니다.
                }
            } catch (err) { console.error(err); }
            finally {
                isProcessing = false;
                resolve();
            }
        }, 'image/jpeg', 0.4); // 압축률도 더 낮춤
    });
}

function accumulateData(result) {
    result.counts.forEach((count, idx) => { totalCounts[idx] += count; });
    if (statChart) {
        statChart.data.datasets[0].data = totalCounts;
        statChart.update();
    }
    const validDetections = result.detections.filter(d => parseFloat(d.conf) > 0.4);
    if (validDetections.length > 0) {
        const listContainer = document.getElementById('detectionList');
        if (listContainer.querySelector('p.text-muted')) listContainer.innerHTML = '';
        validDetections.forEach(d => {
            const item = document.createElement('div');
            item.className = "d-flex justify-content-between border-bottom py-1 small";
            item.innerHTML = `<span class="text-primary fw-bold">${d.label}</span><span class="text-muted">${d.conf} (탐지됨)</span>`;
            listContainer.insertBefore(item, listContainer.firstChild);
        });
    }
}

function drawBoundingBoxes(detections) {
    const media = videoStream.style.display === 'block' ? videoStream : videoPlayer;
    if (!media.clientWidth) return;

    const mediaWidth = media.clientWidth;
    const mediaHeight = media.clientHeight;
    const nativeWidth = media.tagName === 'VIDEO' ? media.videoWidth : media.naturalWidth;
    const nativeHeight = media.tagName === 'VIDEO' ? media.videoHeight : media.naturalHeight;
    const mediaRatio = nativeWidth / nativeHeight;
    const containerRatio = mediaWidth / mediaHeight;

    let displayWidth, displayHeight;
    if (mediaRatio > containerRatio) {
        displayWidth = mediaWidth;
        displayHeight = mediaWidth / mediaRatio;
    } else {
        displayHeight = mediaHeight;
        displayWidth = mediaHeight * mediaRatio;
    }

    overlayCanvas.width = displayWidth;
    overlayCanvas.height = displayHeight;
    overlayCanvas.style.left = media.offsetLeft + (mediaWidth - displayWidth) / 2 + 'px';
    overlayCanvas.style.top = media.offsetTop + (mediaHeight - displayHeight) / 2 + 'px';

    drawCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    detections.forEach(det => {
        if (!det.bbox || parseFloat(det.conf) < 0.4) return;
        const [x1, y1, x2, y2] = det.bbox;
        const startX = x1 * displayWidth;
        const startY = y1 * displayHeight;
        const width = (x2 - x1) * displayWidth;
        const height = (y2 - y1) * displayHeight;

        drawCtx.strokeStyle = "#007BFF";
        drawCtx.lineWidth = 3;
        drawCtx.strokeRect(startX, startY, width, height);
        drawCtx.fillStyle = "#007BFF";
        drawCtx.font = "bold 14px Pretendard";
        const label = `${det.label} ${det.conf}`;
        const textWidth = drawCtx.measureText(label).width;
        const labelBgWidth = textWidth + 10;
        const labelBgHeight = 20;
        const labelY = startY - labelBgHeight < 0 ? startY : startY - labelBgHeight;
        drawCtx.fillRect(startX, labelY, labelBgWidth, labelBgHeight);
        drawCtx.fillStyle = "white";
        drawCtx.fillText(label, startX + 5, labelY + 15);
    });
}

window.addEventListener('resize', () => { if (lastResult) drawBoundingBoxes(lastResult); });

if(saveCloudBtn) {
    saveCloudBtn.onclick = async function() {
        if(!currentFile) return;

        let customName = prompt("저장할 분석 결과의 이름을 입력해주세요:", currentFile.name);
        if (customName === null) return;
        if (customName.trim() === "") customName = currentFile.name;

        const isVideo = currentFile.type.startsWith('video/');
        const formData = new FormData();
        formData.append('original_filename', customName);
        formData.append('boar_count', totalCounts[0]);
        formData.append('water_deer_count', totalCounts[1]);
        formData.append('racoon_count', totalCounts[2]);

        if (isVideo) {
            formData.append('merged_image', currentFile);
            statusText.innerText = "전체 영상 분석 및 저장 중... 잠시만 기다려 주세요.";
        } else {
            const media = videoStream;
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = media.naturalWidth;
            tempCanvas.height = media.naturalHeight;
            const ctx = tempCanvas.getContext('2d');
            ctx.drawImage(media, 0, 0, tempCanvas.width, tempCanvas.height);
            ctx.drawImage(overlayCanvas, 0, 0, tempCanvas.width, tempCanvas.height);

            const blob = await new Promise(resolve => tempCanvas.toBlob(resolve, 'image/jpeg', 0.9));
            formData.append('merged_image', blob, 'result.jpg');
            statusText.innerText = "결과 이미지 저장 중...";
        }

        const originalBtnText = saveCloudBtn.innerHTML;
        saveCloudBtn.disabled = true;
        saveCloudBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>처리 중...';

        try {
            const response = await fetch("/model/save_result", {
                method: 'POST',
                body: formData
            });
            const resData = await response.json();

            if (resData.success && resData.url) {
                alert("성공적으로 저장되었습니다!");
                const link = document.createElement('a');
                link.href = resData.url;
                link.target = '_blank';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                statusText.innerText = "저장 완료! URL: " + resData.url;
            } else {
                alert("저장 실패: " + (resData.message || "URL을 받아오지 못했습니다."));
            }
        } catch (err) {
            console.error(err);
            alert("서버 통신 오류가 발생했습니다.");
        } finally {
            saveCloudBtn.disabled = false;
            saveCloudBtn.innerHTML = originalBtnText;
        }
    };
}
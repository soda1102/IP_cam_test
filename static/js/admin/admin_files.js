function openMediaModal(url, filename) {
    const isVideo = url.match(/\.(mp4|mov|avi|webm|mkv)$/i);
    const content = document.getElementById('media-content');
    if (isVideo) {
        // 클라우디너리 URL이면 f_mp4 변환 파라미터 추가
        let playUrl = url;
        if (url.includes('cloudinary.com') && url.includes('/upload/')) {
            playUrl = url.replace('/upload/', '/upload/f_mp4,vc_auto/');
        }
        content.innerHTML = `
            <video controls style="max-width:100%;max-height:70vh;border-radius:8px;">
                <source src="${playUrl}" type="video/mp4">
                브라우저가 동영상을 지원하지 않습니다.
            </video>`;
    } else {
        content.innerHTML = `
            <img src="${url}" style="max-width:100%;max-height:70vh;border-radius:8px;object-fit:contain;" alt="분석 이미지">`;
    }
    document.getElementById('mediaModal').classList.add('open');
}

function closeMediaModal() {
    document.getElementById('media-content').innerHTML = '';
    document.getElementById('mediaModal').classList.remove('open');
}
async function hideFile(fileId) {
    if (!confirm('이 파일을 숨기겠습니까?')) return;
    const res = await fetch(`/admin/files/${fileId}/toggle`, { method: 'POST' });
    if (res.ok) { showToast('✅ 처리되었습니다.'); location.reload(); }
    else showToast('❌ 처리 실패', 'error');
}

async function restoreFile(fileId) {
    if (!confirm('이 파일을 복구하겠습니까?')) return;
    const res = await fetch(`/admin/files/${fileId}/toggle`, { method: 'POST' });
    if (res.ok) { showToast('✅ 복구되었습니다.'); location.reload(); }
    else showToast('❌ 처리 실패', 'error');
}
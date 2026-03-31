/* ===== 게시글 상세 ===== */
async function openBoardDetail(id) {
    const res  = await fetch(`/admin/board/detail/${id}`);
    const data = await res.json();
    document.getElementById('detail_title').textContent      = data.title;
    document.getElementById('detail_author').textContent     = data.author || '탈퇴회원';
    document.getElementById('detail_created_at').textContent = data.created_at;
    document.getElementById('detail_visits').textContent     = data.visits;
    document.getElementById('detail_content').innerHTML      = data.content || '(내용 없음)';
    const wrap = document.getElementById('detail_reports_wrap');
    if (data.reports && data.reports.length > 0) {
        document.getElementById('detail_reports').innerHTML =
            data.reports.map((r, i) => `<div>${i+1}. ${r || '(사유 없음)'}</div>`).join('');
        wrap.style.display = '';
    } else {
        wrap.style.display = 'none';
    }
    document.getElementById('boardDetailModal').classList.add('open');
}
function closeBoardDetail() {
    document.getElementById('boardDetailModal').classList.remove('open');
}

/* ===== 게시글 액션 ===== */
async function boardAction(url) {
    const res = await fetch(url, { method: 'POST' });
    if (res.ok) { showToast('✅ 처리되었습니다.'); location.reload(); }
    else showToast('❌ 처리 실패', 'error');
}
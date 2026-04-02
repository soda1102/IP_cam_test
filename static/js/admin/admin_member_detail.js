/* ===== 게시글 숨김/복구 ===== */
async function hideBoard(memberId, boardId) {
    if (!confirm('이 게시글을 숨기겠습니까?')) return;
    const res = await fetch(`/admin/members/${memberId}/board/${boardId}/delete`, { method: 'POST' });
    if (res.ok) { showToast('✅ 처리되었습니다.'); location.reload(); }
    else showToast('❌ 처리 실패', 'error');
}
async function restoreBoard(memberId, boardId) {
    if (!confirm('이 게시글을 복구하겠습니까?')) return;
    const res = await fetch(`/admin/members/${memberId}/board/${boardId}/delete`, { method: 'POST' });
    if (res.ok) { showToast('✅ 복구되었습니다.'); location.reload(); }
    else showToast('❌ 처리 실패', 'error');
}

/* ===== 댓글 숨김/복구 ===== */
async function hideComment(memberId, commentId) {
    if (!confirm('이 댓글을 숨기겠습니까?')) return;
    const res = await fetch(`/admin/members/${memberId}/comment/${commentId}/delete`, { method: 'POST' });
    if (res.ok) { showToast('✅ 처리되었습니다.'); location.reload(); }
    else showToast('❌ 처리 실패', 'error');
}
async function restoreComment(memberId, commentId) {
    if (!confirm('이 댓글을 복구하겠습니까?')) return;
    const res = await fetch(`/admin/members/${memberId}/comment/${commentId}/delete`, { method: 'POST' });
    if (res.ok) { showToast('✅ 복구되었습니다.'); location.reload(); }
    else showToast('❌ 처리 실패', 'error');
}

/* ===== 휴지통 복구 ===== */
async function restoreTrash(memberId, boardId) {
    if (!confirm('이 게시글을 복구하겠습니까?')) return;
    const res = await fetch(`/admin/members/${memberId}/trash/${boardId}/restore`, { method: 'POST' });
    if (res.ok) { showToast('✅ 복구되었습니다.'); location.reload(); }
    else showToast('❌ 처리 실패', 'error');
}
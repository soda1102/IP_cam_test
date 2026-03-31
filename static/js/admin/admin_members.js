/* ===== 모달 ===== */
function openAddMemberModal()  { document.getElementById('addMemberModal').classList.add('open'); }
function closeAddMemberModal() { document.getElementById('addMemberModal').classList.remove('open'); }

function openEditMemberModal(id, name, nickname, role, active, birthdate) {
    document.getElementById('editMemberForm').action = `/admin/member/update/${id}`;
    document.getElementById('edit_name').value      = name;
    document.getElementById('edit_nickname').value  = nickname;
    document.getElementById('edit_password').value  = '';
    document.getElementById('edit_role').value      = role;
    document.getElementById('edit_active').value    = String(active);
    document.getElementById('edit_birthdate').value = birthdate;
    document.getElementById('editMemberModal').classList.add('open');
}
function closeEditMemberModal() { document.getElementById('editMemberModal').classList.remove('open'); }

function openToggleConfirm(id, name) {
    document.getElementById('toggleForm').action = `/admin/member/delete/${id}`;
    document.getElementById('toggle-confirm-desc').innerHTML =
        `<strong>${name}</strong> 회원을 변경하시겠습니까?<br>신중한 선택 바랍니다.`;
    document.getElementById('toggleConfirmModal').classList.add('open');
}
function closeToggleConfirm() { document.getElementById('toggleConfirmModal').classList.remove('open'); }

/* ===== AJAX 폼 제출 ===== */
document.getElementById('addMemberForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const res = await fetch(this.action, { method:'POST', body: new FormData(this) });
    if (res.ok) { closeAddMemberModal(); showToast('✅ 회원이 추가되었습니다.'); location.reload(); }
    else showToast('❌ 추가 실패', 'error');
});
document.getElementById('editMemberForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const res = await fetch(this.action, { method:'POST', body: new FormData(this) });
    if (res.ok) { closeEditMemberModal(); showToast('✅ 수정되었습니다.'); location.reload(); }
    else showToast('❌ 수정 실패', 'error');
});
document.getElementById('toggleForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const res = await fetch(this.action, { method:'POST', body: new FormData(this) });
    if (res.ok) { closeToggleConfirm(); showToast('✅ 변경되었습니다.'); location.reload(); }
    else showToast('❌ 변경 실패', 'error');
});
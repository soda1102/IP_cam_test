/* ===== 모달 ===== */
function openAddMemberModal()  { document.getElementById('addMemberModal').classList.add('open'); }
function closeAddMemberModal() { document.getElementById('addMemberModal').classList.remove('open'); }

function openEditMemberModal(id, name, nickname, role, active, birthdate) {
    document.getElementById('editMemberForm').action = `/admin/member/update/${id}`;
    document.getElementById('edit_name').value      = name;
    document.getElementById('edit_nickname').value  = nickname;
    document.getElementById('edit_password').value  = '';
    document.getElementById('edit_active').value    = String(active);
    document.getElementById('edit_birthdate').value = birthdate;

    const roleSelect   = document.getElementById('edit_role');
    const roleHidden   = document.getElementById('edit_role_hidden');
    const activeSelect = document.getElementById('edit_active');
    const currentRole  = document.getElementById('current_user_role').value;

    if (currentRole === 'manager') {
        roleHidden.value    = role;
        roleHidden.disabled = false;
    } else if (role === 'admin') {
        if (roleSelect) roleSelect.setAttribute('disabled', true);
        roleHidden.value    = role;
        roleHidden.disabled = false;
    } else {
        if (roleSelect) {
            roleSelect.value = role;
            roleSelect.removeAttribute('disabled');
        }
        roleHidden.disabled = true;
    }

    if (role === 'admin') {
        activeSelect.setAttribute('disabled', true);
        activeSelect.title = '최고 관리자의 활성 상태는 변경할 수 없습니다.';
    } else {
        activeSelect.removeAttribute('disabled');
        activeSelect.title = '';
    }

    document.getElementById('editMemberModal').classList.add('open');
}
function closeEditMemberModal() { document.getElementById('editMemberModal').classList.remove('open'); }

function openToggleConfirm(id, name, role) {
    // admin 회원은 활성여부 변경 불가
    if (role === 'admin') {
        showToast('❌ 최고 관리자의 활성 상태는 변경할 수 없습니다.', 'error');
        return;
    }
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
    if (res.status === 403) {
        showToast('❌ 권한이 없습니다.', 'error');
        return;
    }
    if (res.ok) { closeEditMemberModal(); showToast('✅ 수정되었습니다.'); location.reload(); }
    else showToast('❌ 수정 실패', 'error');
});

document.getElementById('toggleForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const res = await fetch(this.action, { method:'POST', body: new FormData(this) });
    if (res.status === 403) {
        showToast('❌ 권한이 없습니다.', 'error');
        return;
    }
    if (res.ok) { closeToggleConfirm(); showToast('✅ 변경되었습니다.'); location.reload(); }
    else showToast('❌ 변경 실패', 'error');
});
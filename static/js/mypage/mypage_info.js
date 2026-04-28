function clickInput() {
    // 연필 아이콘 클릭 시 숨겨진 input 태그를 클릭함
    document.getElementById('hiddenInput').click();
}

function submitProfile() {
    const fileInput = document.getElementById('hiddenInput');
    if (fileInput.files && fileInput.files[0]) {
        // 파일을 선택하는 순간 바로 form을 서버로 전송
        document.getElementById('profileForm').submit();
    }
}

// 메뉴 열기/닫기
function toggleEditMenu(event) {
    event.stopPropagation(); // 부모 클릭 이벤트 전파 방지
    const menu = document.getElementById('editMenu');
    menu.style.display = (menu.style.display === 'none') ? 'block' : 'none';
}

// 메뉴 바깥 클릭 시 닫기
document.addEventListener('click', function() {
    document.getElementById('editMenu').style.display = 'none';
});

function clickInput() {
    document.getElementById('hiddenInput').click();
}

function submitProfile() {
    const fileInput = document.getElementById('hiddenInput');
    if (fileInput.files && fileInput.files[0]) {
        document.getElementById('profileForm').submit();
    }
}

// 삭제 확인 및 전송
function deleteProfile() {
    if (confirm("프로필 사진을 삭제하고 기본 이미지로 변경하시겠습니까?")) {
        document.getElementById('deleteForm').submit();
    }
}

function confirmDelete() {
    if (confirm("정말로 탈퇴하시겠습니까?\n모든 활동 내역이 삭제되며 복구할 수 없습니다.")) {
        // 탈퇴 처리를 위한 서버 경로로 이동
        location.href = "/mypage/delete_account";
    }
}
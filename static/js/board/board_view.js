// 1. 좋아요 기능
function toggleLike(boardId) {
    fetch(`/board/like/${boardId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            updateReactionUI('like', data.is_liked, data.like_count);
            if (data.is_liked && data.dislike_count !== undefined) {
                updateReactionUI('dislike', false, data.dislike_count);
            }
        } else {
            alert(data.message);
        }
    });
}

// 2. 싫어요 기능
function toggleDislike(boardId) {
    fetch(`/board/dislike/${boardId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            updateReactionUI('dislike', data.is_disliked, data.dislike_count);
            if (data.is_disliked && data.like_count !== undefined) {
                updateReactionUI('like', false, data.like_count);
            }
        } else {
            alert(data.message);
        }
    });
}

function updateReactionUI(type, isActive, count) {
    const btn = document.getElementById(`${type}-btn`);
    const icon = document.getElementById(`${type}-icon`);
    const countSpan = document.getElementById(`${type}-count`);
    if (countSpan) countSpan.innerText = count;
    if (isActive) {
        btn.classList.add('active');
        icon.className = (type === 'like') ? 'bi bi-heart-fill' : 'bi bi-hand-thumbs-down-fill';
    } else {
        btn.classList.remove('active');
        icon.className = (type === 'like') ? 'bi bi-heart' : 'bi bi-hand-thumbs-down';
    }
}

// 3. 댓글 및 답글 (여기가 형이 썼던 로직 핵심!)
const MAX_REPLY_COUNT = 5;

function toggleReplyForm(commentId, nickname, replyCount = 0) {
    if (replyCount >= MAX_REPLY_COUNT) {
        alert(`답글은 최대 ${MAX_REPLY_COUNT}개까지만 달 수 있습니다.`);
        return;
    }

    const form = document.getElementById(`reply-form-${commentId}`);
    const input = document.getElementById(`reply-input-${commentId}`);
    form.classList.toggle('d-none');

    if (!form.classList.contains('d-none')) {
        input.value = `@${nickname} `;
        input.focus();
    }
}

function submitComment(parentId) {
    const content = parentId
        ? document.getElementById(`reply-input-${parentId}`).value
        : document.getElementById('comment-content').value;

    if (!content.trim()) {
        alert("내용을 입력해주세요.");
        return;
    }

    fetch(`/board/comment/${CURRENT_BOARD_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: content, parent_id: parentId })
    })
    .then(res => {
        if (res.status === 401) { alert("로그인이 필요한 서비스입니다."); return; }
        return res.json();
    })
    .then(data => {
        if (data && data.success) { location.reload(); }
        else if (data) { alert(data.message); }
    });
}

// 댓글 페이지네이션
const COMMENTS_PER_PAGE = 5;

document.addEventListener('DOMContentLoaded', function () {
    initCommentPagination();
});

function initCommentPagination() {
    const commentList = document.getElementById('comment-list');
    const allComments = Array.from(commentList.children);
    const totalPages = Math.ceil(allComments.length / COMMENTS_PER_PAGE);

    if (totalPages <= 1) return;

    showCommentPage(1, allComments);
    renderCommentPagination(1, totalPages, allComments);
}

function showCommentPage(page, allComments) {
    const start = (page - 1) * COMMENTS_PER_PAGE;
    const end = start + COMMENTS_PER_PAGE;

    allComments.forEach((el, idx) => {
        el.style.display = (idx >= start && idx < end) ? '' : 'none';
    });
}

function renderCommentPagination(currentPage, totalPages, allComments) {
    const pagination = document.getElementById('comment-pagination');
    pagination.innerHTML = '';

    // 이전 버튼
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link border-0 shadow-sm mx-1" href="#">&laquo;</a>`;
    prevLi.addEventListener('click', (e) => {
        e.preventDefault();
        if (currentPage > 1) {
            showCommentPage(currentPage - 1, allComments);
            renderCommentPagination(currentPage - 1, totalPages, allComments);
        }
    });
    pagination.appendChild(prevLi);

    // 페이지 번호
    for (let p = 1; p <= totalPages; p++) {
        const li = document.createElement('li');
        li.className = `page-item ${p === currentPage ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link border-0 shadow-sm mx-1" href="#">${p}</a>`;
        li.addEventListener('click', (e) => {
            e.preventDefault();
            showCommentPage(p, allComments);
            renderCommentPagination(p, totalPages, allComments);
        });
        pagination.appendChild(li);
    }

    // 다음 버튼
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link border-0 shadow-sm mx-1" href="#">&raquo;</a>`;
    nextLi.addEventListener('click', (e) => {
        e.preventDefault();
        if (currentPage < totalPages) {
            showCommentPage(currentPage + 1, allComments);
            renderCommentPagination(currentPage + 1, totalPages, allComments);
        }
    });
    pagination.appendChild(nextLi);
}

// 4. [✅ 복구] 스크랩 기능 (형의 커스텀 CSS .btn-scrap-custom 대응)
function toggleScrap(boardId) {
    fetch(`/board/view/scrap/${boardId}`, { method: 'POST' })
    .then(res => {
        if (res.status === 401) { alert("로그인이 필요한 서비스입니다."); return; }
        return res.json();
    })
    .then(data => {
        if (!data) return;
        if (data.success) {
            alert(data.message);
            const btn = document.getElementById('scrap-btn');
            const icon = btn.querySelector('i');

            // 형이 만든 .active 클래스를 줬다 뺐다 해서 색상을 바꿈
            if (data.is_scrapped) {
                btn.classList.add('active');
                icon.className = 'bi bi-bookmark-fill me-1';
            } else {
                btn.classList.remove('active');
                icon.className = 'bi bi-bookmark me-1';
            }
        } else {
            alert(data.message);
        }
    });
}

// 1. 수정창 열기 (기존 내용 숨기고 입력창 보이기)
function showEditForm(id) {
    const content = document.getElementById(`comment-text-${id}`).innerText;
    document.getElementById(`comment-body-${id}`).classList.add('d-none');
    document.getElementById(`edit-form-${id}`).classList.remove('d-none');
    document.getElementById(`edit-input-${id}`).value = content;
}

// 2. 수정창 닫기 (취소 버튼)
function hideEditForm(id) {
    document.getElementById(`comment-body-${id}`).classList.remove('d-none');
    document.getElementById(`edit-form-${id}`).classList.add('d-none');
}

// 3. 수정 완료 처리 (서버 전송 + 알림창)
function submitEdit(id) {
    const newContent = document.getElementById(`edit-input-${id}`).value;

    if (!newContent.trim()) {
        alert("내용을 입력해주세요.");
        return;
    }

    fetch(`/board/comment/edit/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newContent })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("수정 완료!"); // 요청하신 알림창
            location.reload();
        } else {
            alert(data.message || "수정 실패");
        }
    })
    .catch(err => alert("서버 통신 오류가 발생했습니다."));
}

// 4. 삭제 처리 (알림창)
function deleteComment(id) {
    if (!confirm("정말 삭제하시겠습니까?")) return;

    fetch(`/board/comment/delete/${id}`, {
        method: 'POST'
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("삭제 완료!"); // 요청하신 알림창
            location.reload();
        } else {
            alert(data.message || "삭제 실패");
        }
    });
}

// 신고 모달 열기 (중복 실행 방지 버전)
let reportModalInstance = null; // 인스턴스를 전역으로 관리

function openReportModal(type, targetId) {
document.getElementById('report-type').value = type;
document.getElementById('report-target-id').value = targetId;

const label = document.getElementById('reportModalLabel');
if (type === 'board') {
    label.innerHTML = '<i class="bi bi-alarm me-2"></i>게시글 신고하기';
} else {
    label.innerHTML = '<i class="bi bi-alarm me-2"></i>댓글 신고하기';
}

// 모달 인스턴스가 없으면 새로 만들고, 있으면 있는 걸 띄움
if (!reportModalInstance) {
    reportModalInstance = new bootstrap.Modal(document.getElementById('reportModal'));
}
reportModalInstance.show();
}

// 신고 제출 함수
function submitReport() {
const type = document.getElementById('report-type').value;
const targetId = document.getElementById('report-target-id').value;
const reason = document.getElementById('report-reason-select').value;
const detail = document.getElementById('report-detail').value;

if (!reason) {
    alert("신고 사유를 선택해주세요.");
    return;
}

fetch('/board/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        type: type,
        target_id: targetId,
        reason: reason,
        detail: detail
    })
})
.then(res => res.json())
.then(data => {
    alert(data.message);
    if (data.success) {
        // 성공 시 모달을 완전히 닫고 새로고침
        if(reportModalInstance) reportModalInstance.hide();
        location.reload();
    }
})
.catch(err => {
    console.error("신고 에러:", err);
    alert("신고 처리 중 오류가 발생했습니다.");
});
}
function toggleFollow(userId) {
    fetch(`/profile/follow/${userId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            // 깔끔하게 페이지를 새로고침해서 통계 숫자까지 한 번에 업데이트!
            location.reload();
        } else {
            alert(data.message);
        }
    });
}

function toggleBlock(userId) {
    if (!confirm(document.getElementById('block-btn').innerText + "하시겠습니까?")) return;

    fetch(`/profile/block/${userId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            // 차단하면 팔로우 숫자가 바뀔 수 있으니 새로고침이 가장 깔끔함
            location.reload();
        } else {
            alert(data.message);
        }
    });
}
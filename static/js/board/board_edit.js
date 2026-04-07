$(document).ready(function() {
    const $summernote = $('#summernote');

    // Summernote 초기화
    $summernote.summernote({
        placeholder: '글씨 색상, 배경색, 크기 등을 자유롭게 변경하여 글을 작성해 보세요!',
        height: 450,
        lang: 'ko-KR',
        toolbar: [
            ['fontname', ['fontname']],
            ['fontsize', ['fontsize']],
            ['style', ['bold', 'italic', 'underline', 'strikethrough', 'clear']],
            ['color', ['forecolor', 'backcolor']],
            ['para', ['ul', 'ol', 'paragraph']],
            ['insert', ['link', 'picture', 'video', 'hr']],
            ['view', ['fullscreen', 'codeview', 'help']]
        ],
        fontNames: ['맑은 고딕', '궁서', '굴림체', '굴림', '돋움체', '바탕체', 'Arial', 'Arial Black', 'Comic Sans MS', 'Courier New'],
        fontNamesIgnoreCheck: ['맑은 고딕', '궁서', '굴림체', '굴림', '돋움체', '바탕체'],
        fontSizes: ['8', '9', '10', '11', '12', '14', '16', '18', '20', '22', '24', '28', '30', '36', '50', '72'],
        callbacks: {
            onImageUpload: function(files) {
                for (let i = 0; i < files.length; i++) {
                    uploadImage(files[i]);
                }
            }
        }
    });

    // 기존 내용 불러오기
    const existing = $summernote.val();
    if (existing) {
        $summernote.summernote('code', existing);
    }

    function uploadImage(file) {
        const formData = new FormData();
        formData.append("file", file);
        fetch('/board/upload/image', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.url) $summernote.summernote('insertImage', data.url);
        })
        .catch(err => alert("이미지 업로드에 실패했습니다."));
    }
});

function confirmEdit() {
    alert("수정이 완료되었습니다!");
    return true;
}
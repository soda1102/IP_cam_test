
    $(document).ready(function() {
        const $summernote = $('#summernote');
        const $titleInput = $('#postTitle');
        const $submitBtn = $('#submitBtn');

        // 1. Summernote 초기화 (형이 원하는 꾸미기 기능 풀세트)
        $summernote.summernote({
            placeholder: '글씨 색상, 배경색, 크기 등을 자유롭게 변경하여 글을 작성해 보세요!',
            height: 450,
            lang: 'ko-KR',
            // 툴바에 글자색(forecolor), 배경색(backcolor), 글자크기(fontsize) 명시
            toolbar: [
                ['fontname', ['fontname']],
                ['fontsize', ['fontsize']],
                ['style', ['bold', 'italic', 'underline', 'strikethrough', 'clear']],
                ['color', ['forecolor', 'backcolor']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['insert', ['link', 'picture', 'video', 'hr']],
                ['view', ['fullscreen', 'codeview', 'help']]
            ],
            // 폰트 목록 및 크기 설정
            fontNames: ['맑은 고딕', '궁서', '굴림체', '굴림', '돋움체', '바탕체', 'Arial', 'Arial Black', 'Comic Sans MS', 'Courier New'],
            fontNamesIgnoreCheck: ['맑은 고딕', '궁서', '굴림체', '굴림', '돋움체', '바탕체'],
            fontSizes: ['8', '9', '10', '11', '12', '14', '16', '18', '20', '22', '24', '28', '30', '36', '50', '72'],

            callbacks: {
                onChange: function(contents, $editable) {
                    checkFormValidity();
                },
                onImageUpload: function(files) {
                    for (let i = 0; i < files.length; i++) {
                        uploadImage(files[i]);
                    }
                }
            }
        });

        // 제목 및 본문 입력 체크 (등록 버튼 활성화/비활성화)
        function checkFormValidity() {
            const titleValue = $titleInput.val().trim();
            const isEmpty = $summernote.summernote('isEmpty');
            $submitBtn.prop('disabled', !(titleValue.length > 0 && !isEmpty));
        }

        $titleInput.on('input', checkFormValidity);

        // 이미지 업로드 서버 통신 (기존 로직 유지)
        function uploadImage(file) {
            const formData = new FormData();
            formData.append("file", file);
            fetch('/board/upload/image', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if(data.url) $summernote.summernote('insertImage', data.url);
            })
            .catch(err => alert("이미지 업로드에 실패했습니다."));
        }
    });
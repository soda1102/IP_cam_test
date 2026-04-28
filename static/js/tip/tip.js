document.addEventListener('DOMContentLoaded', function() {
    const posterBox = document.querySelector('.poster-box');
    if (posterBox) {
        posterBox.addEventListener('click', function() {
            window.open('/static/img/poster.png', '_blank');
        });
    }
});

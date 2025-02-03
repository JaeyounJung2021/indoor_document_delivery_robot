document.addEventListener("DOMContentLoaded", function() {
    var flashMessages = document.querySelector('.flash-messages');
    if (flashMessages) {
        flashMessages.style.display = 'block';  // 메시지 표시
        setTimeout(function() {
            flashMessages.style.opacity = '0';  // 애니메이션 적용
            setTimeout(function() {
                flashMessages.style.display = 'none';  // 1초 후 숨기기
            }, 1000); // fade-out 애니메이션 시간
        }, 5000);  // 5초 후에 사라짐
    }
});

// 모달 열기
function openModal() {
    document.getElementById("robotModal").style.display = "block";
}

// 모달 닫기
function closeModal() {
    document.getElementById("robotModal").style.display = "none";
}

// 바깥 클릭 시 모달 닫기
window.onclick = function(event) {
    var modal = document.getElementById("robotModal");
    if (event.target === modal) {
        modal.style.display = "none";
    }
}

// 바깥 클릭 시 모달 닫기
window.onclick = function(event) {
    var modal = document.getElementById("robotModal");
    var locationModal = document.getElementById("locationModal");
    if (event.target === modal || event.target === locationModal) {
        modal.style.display = "none";
        locationModal.style.display = "none";
    }
}

// 로봇 호출 팝업 열기
function openModal() {
    document.getElementById("robotModal").style.display = "flex";
}

// 로봇 위치 조회 팝업 열기
function openLocationModal() {
    document.getElementById("locationModal").style.display = "flex";
    startPathUpdating(); // 로봇 위치 조회 팝업이 열리면 경로 업데이트 시작
}

// 팝업 닫기
function closeModal() {
    document.getElementById("robotModal").style.display = "none";
}

function closeLocationModal() {
    document.getElementById("locationModal").style.display = "none";
    stopPathUpdating(); // 팝업이 닫히면 경로 업데이트 중지
}

// Canvas 초기화 (로봇 경로 그리기)
var canvas = document.getElementById("robotCanvas");
var ctx = canvas.getContext("2d");
var pathHistory = [];  // 경로 히스토리 저장

// 경로 업데이트 함수
function updatePath(message) {
    ctx.clearRect(0, 0, canvas.width, canvas.height); // 캔버스를 지워서 이전 경로 지우기

    // 현재 경로 그리기
    ctx.beginPath();
    ctx.moveTo(message.poses[0].pose.position.x * 50, message.poses[0].pose.position.y * 50); // 시작점

    // 경로 히스토리 그리기
    pathHistory.forEach(function(pathPoint) {
        ctx.lineTo(pathPoint.x * 50, pathPoint.y * 50);
    });

    ctx.strokeStyle = "blue";
    ctx.lineWidth = 2;
    ctx.stroke();

    // 새 경로 추가 (pathHistory에 추가)
    pathHistory.push({
        x: message.poses[0].pose.position.x,
        y: message.poses[0].pose.position.y
    });

    // 오래된 경로 데이터 삭제 (최대 5개 경로까지만 유지)
    if (pathHistory.length > 5) {
        pathHistory.shift(); // 오래된 경로 지우기
    }
}

// 경로 업데이트를 주기적으로 실행 (예: 1초마다)
var updateInterval;
function startPathUpdating() {
    updateInterval = setInterval(function() {
        var message = {
            poses: [{
                pose: {
                    position: {
                        x: Math.random() * 5,  // 임의로 x 좌표 생성
                        y: Math.random() * 5   // 임의로 y 좌표 생성
                    }
                }
            }]
        };
        updatePath(message); // 경로 업데이트
    }, 1000);  // 1초마다 경로 업데이트
}

// 경로 업데이트를 멈추는 함수
function stopPathUpdating() {
    clearInterval(updateInterval);  // setInterval을 멈추어 경로 업데이트 중지
}

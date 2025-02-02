//웹소켓 등록록
var socket = io("http://localhost:5000");
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
    startPathUpdating();  // 로봇 위치 조회 팝업이 열리면 경로 업데이트 시작
}

// 팝업 닫기
function closeModal() {
    document.getElementById("robotModal").style.display = "none";
}

function closeLocationModal() {
    document.getElementById("locationModal").style.display = "none";
    stopPathUpdating();  // 팝업이 닫히면 경로 업데이트 중지
}

// 캔버스 설정
var canvas = document.getElementById("robotCanvas");
var ctx = canvas.getContext("2d");

// 맵 이미지 로드
var mapImage = new Image();
mapImage.src = '/static/images/map.png';  // 로컬 이미지 경로 (웹 서버의 정적 파일 경로)

// 로봇 경로 히스토리
var pathHistory = [];

// ROS WebSocket 서버 연결
var ros = new ROSLIB.Ros({
    url: 'ws://<ROS_SERVER_IP>:9090'  // ROS WebSocket 서버 주소
});

// 위치 데이터를 받을 토픽 설정
var listener = new ROSLIB.Topic({
    ros: ros,
    name: '/amcl_pose',  // ROS 토픽 이름
    messageType: 'geometry_msgs/PoseWithCovarianceStamped'  // 메시지 타입
});

// 위치 데이터 구독
listener.subscribe(function(message) {
    updatePath(message);  // 로봇 위치 데이터로 경로 업데이트
});

// 경로 업데이트 함수
function updatePath(message) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);  // 이전 경로 지우기

    // 맵을 다시 그리기 (경로가 그려지기 전에 매번 맵을 그리기)
    ctx.drawImage(mapImage, 0, 0, canvas.width, canvas.height);

    // 현재 경로 그리기
    ctx.beginPath();
    ctx.moveTo(message.pose.position.x * 50, message.pose.position.y * 50);  // 시작점

    // 경로 그리기
    pathHistory.forEach(function(pathPoint) {
        ctx.lineTo(pathPoint.x * 50, pathPoint.y * 50);
    });

    ctx.strokeStyle = "blue";
    ctx.lineWidth = 2;
    ctx.stroke();

    // 새 경로 추가 (pathHistory에 추가)
    pathHistory.push({
        x: message.pose.position.x,
        y: message.pose.position.y
    });

    // 오래된 경로 삭제 (최대 5개 경로까지만 유지)
    if (pathHistory.length > 5) {
        pathHistory.shift();
    }
}

//수령인, 호출인 웹푸시 알림 구현 부분(웹 푸쉬 알림)

//사용자에게 알림권한 요청
if (Notification.permission === "granted") {
    // 알림을 보낼 준비가 된 경우
    console.log("알림 권한이 승인되었습니다.");
} else {
    Notification.requestPermission().then(function(permission) {
        if (permission === "granted") {
            console.log("알림 권한이 승인되었습니다.");
        } else {
            console.log("알림 권한이 거부되었습니다.");
        }
    });
}

//Service Workder 등록 (웹푸시)
if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./service-worker.js").then(registration => {
        console.log("✅ Service Worker 등록 성공:", registration);
    }).catch(error => {
        console.log("❌ Service Worker 등록 실패:", error);
    });
}

// 웹 푸시 알림 처리
socket.on("web_push", function(data) {
    if ("serviceWorker" in navigator && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({
            title: data.title,
            message: data.message
        });
    } else {
        console.log("❌ Service Worker가 활성화되지 않았습니다.");
    }
});
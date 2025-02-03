//웹소켓 등록록
var socket = io("https://192.168.0.3:5000",{transports:['websocket'],withCredentials:true});
console.log("JS시작!!!!!!!!!!!!!!")
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

// 회원가입 팝업 열기
function openRegisterModal() {
    document.getElementById("registerModal").style.display = "flex";
}

// 팝업 닫기
function closeModal() {
    document.getElementById("robotModal").style.display = "none";
}

function closeLocationModal() {
    document.getElementById("locationModal").style.display = "none";
    stopPathUpdating();  // 팝업이 닫히면 경로 업데이트 중지
}

function closeRegisterModal() {
    document.getElementById("registerModal").style.display = "none";
}

/* 아 시발 진짜 아래 구현도 안된코드 실행 하다가 DOM 로드 안되서 서비스 워커 실행 안된거였네 시발 진짜 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!11
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
*/
//수령인, 호출인 웹푸시 알림 구현 부분(웹 푸쉬 알림)


// 버튼 클릭 시 알림 권한 요청, 브라우저따라 무조건 사용자랑 상호작용이 있어야만 권한허용 할 수 있는 경우가 있어서....
document.getElementById("requestPermissionButton").addEventListener('click', function() {
    Notification.requestPermission().then(function(permission) {
        console.log(permission); // 알림 권한 요청 상태 출력
        if (permission === "granted") {
            console.log("알림 권한이 승인되었습니다.");
        } else {
            console.log("알림 권한이 거부되었습니다.");
        }
    });
});


// 웹 푸시 알림 처리 (Notification API 사용)
socket.on("web_push", function(data) {
    if (Notification.permission === "granted") {
        // 알림을 표시
        new Notification(data.title, {
            body: data.message,
            icon: "/static/images/icon.png",  // 아이콘 (필요 시 추가)
            vibrate: [200, 100, 200],  // 진동 효과 (필요 시 추가)
        });
        console.log("웹 푸시 알림을 표시했습니다:", data);
    } else {
        console.log("알림 권한이 거부되어 알림을 표시할 수 없습니다.");
    }
});
//웹소켓 등록록
var socket = io("https://172.20.10.14:5000",{transports:['websocket'],withCredentials:true});
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

//로봇 위치 정보 그리기(ROSBridge + )
document.addEventListener("DOMContentLoaded", function () {
    var ros = new ROSLIB.Ros({
        url: 'ws://localhost:9090' // ROSBridge 웹소켓 주소
    });

    ros.on('connection', function () {
        console.log('✅ Connected to ROSBridge WebSocket');
    });

    ros.on('error', function (error) {
        console.error('❌ Error connecting to ROS:', error);
    });

    ros.on('close', function () {
        console.log('🔌 Disconnected from ROS');
    });

    var canvas = document.getElementById("robotCanvas");
    var ctx = canvas.getContext("2d"); //canvas에 2d 그림 그리는 객체

    var robotPath = []; // 로봇 이동 경로 저장
    var goalPosition = null; // 목표 위치 저장
    var scale = 50; // 좌표를 캔버스 크기로 변환하는 스케일 조정

    // 🟢 로봇 위치(odom) 구독
    var odomListener = new ROSLIB.Topic({
        ros: ros,
        name: '/odom',
        messageType: 'nav_msgs/Odometry'
    });

    odomListener.subscribe(function (message) {
        var x = message.pose.pose.position.x * scale + canvas.width / 2;
        var y = -message.pose.pose.position.y * scale + canvas.height / 2; // Y 좌표 반전(HTML5 canvas는 아래로 증가)

        robotPath.push({ x, y });

        if (robotPath.length > 100) {
            robotPath.shift(); // 너무 많은 점을 저장하지 않도록 제한
        }

        drawCanvas();
    });

    // 🟢 목표 위치(goal) 구독
    var goalListener = new ROSLIB.Topic({
        ros: ros,
        name: '/move_base_simple/goal',
        messageType: 'geometry_msgs/PoseStamped'
    });

    goalListener.subscribe(function (message) {
        var x = message.pose.position.x * scale + canvas.width / 2;
        var y = -message.pose.position.y * scale + canvas.height / 2;

        goalPosition = { x, y };
        drawCanvas();
    });

    function drawCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height); //내부 정보를 다 지움. BUT 밑에서 계속 그려주니까 사실상 애니메이션처럼 계속 그려주는거임.

        // 🔴 목표 위치 그리기 (빨간색 원)
        if (goalPosition) {
            ctx.fillStyle = "red";
            ctx.beginPath(); //이전에 그렸던 그림에서 벗어나서 새로운 그림 그리기
            ctx.arc(goalPosition.x, goalPosition.y, 5, 0, 2 * Math.PI);
            ctx.fill(); //fill로 채우고 있기 때문에 stroke 필요없음.
        }

        // 🟢 로봇 경로 그리기 (녹색 선)
        ctx.strokeStyle = "green";
        ctx.lineWidth = 2;
        ctx.beginPath(); //이전에 그렸던 그림에서 벗어나서 새로운 그림 그리기
        for (var i = 0; i < robotPath.length; i++) {
            var pos = robotPath[i];
            if (i === 0) {
                ctx.moveTo(pos.x, pos.y); //처음 i===0일때는 펜을 들어서 시작지점으로 펜을 이동
            } else {
                ctx.lineTo(pos.x, pos.y); // 현재 좌표에서 넣어준 인자의 좌표로 선을 그려주는 부분. 그리기 + 펜좌표도 옮겨줌.
            }
        }
        ctx.stroke(); //line to 는 경로 정의만 해두고. 실제 HTML 캔버스에 그려주는놈은 얘임.

        // 🔵 로봇 현재 위치 표시 (파란색 원)
        if (robotPath.length > 0) {
            var lastPos = robotPath[robotPath.length - 1];
            ctx.fillStyle = "blue";
            ctx.beginPath();
            ctx.arc(lastPos.x, lastPos.y, 5, 0, 2 * Math.PI);
            ctx.fill(); // fill 로 채우고 있기때문에 stroke 필요없음.
        }
    }
});

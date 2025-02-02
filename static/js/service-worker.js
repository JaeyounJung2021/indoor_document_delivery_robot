self.addEventListener("message", function (event) {
    if (event.data && event.data.title && event.data.message) {
        self.registration.showNotification(event.data.title, {
            body: event.data.message,
            icon: "/static/images/icon.png",  // 알림 아이콘 (선택 사항)
            vibrate: [200, 100, 200],  // 진동 효과 (선택 사항)
            tag: "robot-notification",
            actions: [
                { action: "open", title: "확인" }
            ]
        });
    }
});

// 알림 클릭 시 특정 페이지로 이동
self.addEventListener("notificationclick", function (event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow("/dashboard")  // 알림 클릭 시 특정 페이지 열기
    );
});

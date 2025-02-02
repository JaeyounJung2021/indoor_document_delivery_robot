# -*- coding: utf-8 -*-
#!/usr/bin/env python

import sys
import rospy
from std_msgs.msg import String
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QMessageBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSlot

# 이미지 파일 경로 (경로 확인 필수)
IMG_PATH = "/home/sdj/Desktop/indoor_document_delivery_robot/static/img/robot.jpg"

class ArrivedScreen(QWidget):
    """ 도착 시 사용자 역할(caller/recipient)에 따라 UI 표시 """

    def __init__(self):
        super(ArrivedScreen, self).__init__()
        self.role = None  # 초기값: 역할 미확정
        self.drawer_num = "1"  # 기본값 (MCU 연동 시 업데이트 가능)
        self.initUI()
        
        rospy.init_node('arrived_gui_node', anonymous=True)
        rospy.Subscriber('/human_to_meet', String, self.update_role)  # 역할 수신
        self.pub = rospy.Publisher('/is_interacting_with_human_done', String, queue_size=10)

    def initUI(self):
        """ 역할(caller/recipient) 감지 전 기본 UI """
        self.setWindowTitle("배송 인터페이스")
        self.setStyleSheet("background-color: #f3f3f3;")
        self.showFullScreen()  # 전체 화면 적용

        self.layout = QVBoxLayout()

        # 이미지 영역
        self.image_label = QLabel(self)
        pixmap = QPixmap(IMG_PATH)
        if pixmap.isNull():
            print("⚠️ Image not found! Using placeholder.")
            pixmap = QPixmap(400, 400)
            pixmap.fill(Qt.gray)  # 기본 배경색
        self.image_label.setPixmap(pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.image_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.image_label)

        # 기본 안내문
        self.instruction_label = QLabel("🔄 로봇이 사용자 정보를 확인 중...")
        self.instruction_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #007BFF;")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.instruction_label)

        self.setLayout(self.layout)

    def update_role(self, msg):
        """ `/human_to_meet` 토픽을 구독하여 역할 설정 (ROS 콜백 -> UI 변경) """
        received_data = msg.data.strip()  # 예: "user1,caller" 또는 "user1,recipient"
        user_id, role = received_data.split(",")  # user_id="user1", role="caller" or "recipient"

        rospy.loginfo(f"Received role: {role}")
        self.role = role.strip()

        # 메인 스레드에서 UI 업데이트 실행
        QTimer.singleShot(0, self.refresh_ui)

    @pyqtSlot()
    def refresh_ui(self):
        """ 역할에 따라 UI 업데이트 """
        for i in reversed(range(self.layout.count())):  # 기존 위젯 삭제
            self.layout.itemAt(i).widget().setParent(None)

        # 이미지 유지
        self.layout.addWidget(self.image_label)

        if self.role == "caller":
            self.setup_caller_ui()
        elif self.role == "recipient":
            self.setup_recipient_ui()

    def setup_caller_ui(self):
        """ 📦 Caller UI 설정 (적재) """
        instruction_text = f"📦 **서랍 {self.drawer_num}번에 적재해 주세요.**"
        self.instruction_label = QLabel(instruction_text)
        self.instruction_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #007BFF;")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.instruction_label)

        self.complete_btn = QPushButton("✅ **완료**", self)
        self.complete_btn.clicked.connect(self.show_popup)
        self.layout.addWidget(self.complete_btn)

    def setup_recipient_ui(self):
        """ 📥 Recipient UI 설정 (픽업) """
        instruction_text = f"📥 **서랍 {self.drawer_num}번에서 픽업해 주세요.**"
        self.instruction_label = QLabel(instruction_text)
        self.instruction_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #007BFF;")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.instruction_label)

        self.pickup_btn = QPushButton("📤 **픽업**", self)
        self.pickup_btn.clicked.connect(self.show_popup)
        self.layout.addWidget(self.pickup_btn)

    def show_popup(self):
        """ ✅ 팝업 표시 & ROS 메시지 전송 """
        QMessageBox.information(self, "✅ 완료", "작업이 완료되었습니다.")
        self.pub.publish("done")
        self.close()

    def closeEvent(self, event):
        """ GUI 종료 시 ROS 노드도 종료 """
        rospy.signal_shutdown("GUI closed")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    screen = ArrivedScreen()
    screen.show()
    sys.exit(app.exec_())

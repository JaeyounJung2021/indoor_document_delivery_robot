# -*- coding: utf-8 -*-
#!/usr/bin/env python

import os
import sys
import sqlite3
import rospy
from std_msgs.msg import String
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QLineEdit, QPushButton,
    QMessageBox, QStackedWidget
)

# 현재 실행 중인 스크립트(`qt_gui_path.py`)의 디렉토리를 가져옴
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 실행 파일이 있는 폴더 기준으로 'data/company.db' 경로를 설정
DB_PATH = os.path.join(BASE_DIR, "data", "company.db")
print(f"[DEBUG] 데이터베이스 경로: {DB_PATH}")  # 경로가 올바른지 확인

class SelectMethodScreen(QWidget):
    """ Screen 1: Select RFID or Login """
    def __init__(self, stacked_widget):
        super(SelectMethodScreen, self).__init__()
        self.stacked_widget = stacked_widget  # Reference to switch screens
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.info_label = QLabel("Select Authentication Method:")
        layout.addWidget(self.info_label)

        self.rfid_btn = QPushButton("Use RFID", self)
        self.rfid_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        layout.addWidget(self.rfid_btn)

        self.login_btn = QPushButton("Login with ID/Password", self)
        self.login_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

class RFIDScreen(QWidget):
    """ Screen 2-1: RFID Authentication """
    def __init__(self, stacked_widget):
        super(RFIDScreen, self).__init__()
        self.stacked_widget = stacked_widget
        self.rfid_id = None  # Store RFID ID
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.info_label = QLabel("Tap RFID Tag...")
        layout.addWidget(self.info_label)

        self.rfid_btn = QPushButton("Simulate RFID Scan", self)
        self.rfid_btn.clicked.connect(self.simulate_rfid_scan)
        layout.addWidget(self.rfid_btn)

        self.setLayout(layout)

    def simulate_rfid_scan(self):
        """ Simulate RFID scan """
        self.rfid_id = "user1"  # Simulated ID (replace with real RFID input)
        QMessageBox.information(self, "RFID Success", f"RFID Tagged: {self.rfid_id}")
        self.stacked_widget.rfid_user = self.rfid_id  # Store globally
        self.stacked_widget.setCurrentIndex(3)  # Go to verification screen

class LoginScreen(QWidget):
    """ Screen 2-2: User ID & Password Authentication """
    def __init__(self, stacked_widget):
        super(LoginScreen, self).__init__()
        self.stacked_widget = stacked_widget
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.info_label = QLabel("Enter ID & Password:")
        layout.addWidget(self.info_label)

        self.id_input = QLineEdit(self)
        self.id_input.setPlaceholderText("User ID")
        layout.addWidget(self.id_input)

        self.pw_input = QLineEdit(self)
        self.pw_input.setPlaceholderText("Password")
        self.pw_input.setEchoMode(QLineEdit.Password)  # Hide password
        layout.addWidget(self.pw_input)

        self.login_btn = QPushButton("Login", self)
        self.login_btn.clicked.connect(self.verify_login)
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

    def verify_login(self):
        """ Check ID & Password, then move to verification screen """
        user_id = self.id_input.text().strip()
        password = self.pw_input.text().strip()

        if self.authenticate_user(user_id, password):
            QMessageBox.information(self, "Login Success", "Authentication Complete!")
            self.stacked_widget.rfid_user = user_id  # Store globally
            self.stacked_widget.setCurrentIndex(3)  # Move to verification
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid ID or Password.")

    def authenticate_user(self, user_id, password):
        """ Validate ID & Password in SQLite Database """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM employees WHERE id=? AND password=?", (user_id, password))
        user = cursor.fetchone()

        conn.close()
        return user is not None  # Return True if user exists

class VerificationScreen(QWidget):
    """ Screen 3: Wait for Robot & Verify ID via ROS """
    def __init__(self, stacked_widget):
        super(VerificationScreen, self).__init__()
        self.stacked_widget = stacked_widget
        self.initUI()
        rospy.init_node('auth_verification_node', anonymous=True)
        rospy.Subscriber('/human_to_meet', String, self.check_user_auth)

    def initUI(self):
        layout = QVBoxLayout()
        self.info_label = QLabel("Waiting for Robot...")
        layout.addWidget(self.info_label)
        self.setLayout(layout)

    def check_user_auth(self, msg):
        """ Check if the user ID from ROS matches the authenticated user """
        received_data = msg.data.strip()  # Example: "user1,caller"
        user_id, _ = received_data.split(",")  # Extract "user1"

        if self.stacked_widget.rfid_user and self.stacked_widget.rfid_user == user_id:
            rospy.loginfo("User Verified! Moving to Arrival Screen.")
            self.run_arrived_gui()
        else:
            QMessageBox.warning(self, "Verification Failed", "Unauthorized Access!")

    def run_arrived_gui(self):
        """ Run qt_gui_arrived.py """
        import subprocess
        subprocess.Popen(["python3", "qt_gui_arrived.py"])  # Execute arrival screen
        self.close()  # Close current GUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    stacked_widget = QStackedWidget()
    stacked_widget.rfid_user = None  # Store authenticated user globally

    # Adding screens
    stacked_widget.addWidget(SelectMethodScreen(stacked_widget))  # Screen 1
    stacked_widget.addWidget(RFIDScreen(stacked_widget))  # Screen 2-1
    stacked_widget.addWidget(LoginScreen(stacked_widget))  # Screen 2-2
    stacked_widget.addWidget(VerificationScreen(stacked_widget))  # Screen 3

    stacked_widget.setCurrentIndex(0)  # Start with Selection Screen
    stacked_widget.showFullScreen()

    sys.exit(app.exec_())

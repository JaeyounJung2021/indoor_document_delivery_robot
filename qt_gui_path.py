import os
import sys
import sqlite3
import rospy
from std_msgs.msg import String
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QLineEdit, QPushButton,
    QMessageBox, QStackedWidget
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal

# 📌 **전역 변수 (ROS 토픽으로 받은 사용자 정보 저장)**
received_user_id = None
received_role = None

# 현재 실행 중인 스크립트(`qt_gui_path.py`)의 디렉토리를 가져옴
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 실행 파일이 있는 폴더 기준으로 'data/company.db' 경로를 설정
DB_PATH = os.path.join(BASE_DIR, "data", "company.db")
print(f"[DEBUG] 데이터베이스 경로: {DB_PATH}")  # 경로가 올바른지 확인

# 🌐 **ROS Subscriber - /human_to_meet 토픽 구독**
def human_to_meet_callback(msg):
    """ human_to_meet 토픽을 수신하고 전역 변수에 저장 """
    global received_user_id, received_role
    rospy.loginfo("씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발씨발발")
    received_data = msg.data.strip()  # 예: "user1,caller"
    if "," in received_data:
        received_user_id, received_role,_,_ = received_data.split(",")
        rospy.loginfo(f"📡 수신된 사용자: {received_user_id}, 역할: {received_role}")
    else:
        rospy.logwarn("⚠️ 잘못된 데이터 형식: " + received_data)

class SelectMethodScreen(QWidget):
    """ Screen 1: RFID or Login 선택 화면 """

    def __init__(self, stacked_widget):
        super(SelectMethodScreen, self).__init__()
        self.stacked_widget = stacked_widget
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.info_label = QLabel("🔑 인증 방법을 선택하세요:")
        layout.addWidget(self.info_label)

        self.rfid_btn = QPushButton("🛂 RFID 사용", self)
        self.rfid_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        layout.addWidget(self.rfid_btn)

        self.login_btn = QPushButton("🔐 ID / Password 로그인", self)
        self.login_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

        """ 일정 시간이 지난 후 팝업 표시 (UI 렌더링 완료 후 실행) """
        QTimer.singleShot(100, self.show_arrival_popup)  # 100ms(0.1초) 후 실행
        
    def show_arrival_popup(self):
        """ arrived of start popup massage transmit """
        QMessageBox.information(self, "✅ 도착", "로봇이 도착했습니다!")


#qt와 비동기적으로 ROS콜백 실행
class ROSSubscriberThread(QThread):
    """ROS 구독자를 실행하는 별도의 스레드"""
    auth_result_received = pyqtSignal(str)

    def run(self):
        rospy.init_node('rfid_auth_subscriber', anonymous=True)
        rospy.Subscriber('/rfid_auth_result', String, self.callback)
        rospy.spin()

    def callback(self, msg):
        """RFID 인증 결과 처리"""
        self.auth_result_received.emit(msg.data)  # 받은 메시지를 Qt GUI로 전달


class RFIDScreen(QWidget):
    """ Screen 2-1: RFID 인증 화면 """

    def __init__(self, stacked_widget):
        super(RFIDScreen, self).__init__()
        self.stacked_widget = stacked_widget
        self.initUI()
        
        rfid_auth_request_pub.publish("RequestArrived") #ESP8266으로 RFID인증요청 토픽 전송 #추후에 esp8266 두개 컨트롤 되도록 하는 로직 추가 필요.

        # ROS Subscriber 시작
        self.subscriber_thread = ROSSubscriberThread()
        self.subscriber_thread.auth_result_received.connect(self.handle_auth_result)  # 인증 결과 처리 시그널 연결
        self.subscriber_thread.start()

    def initUI(self):
        layout = QVBoxLayout()
        self.info_label = QLabel("🛂 RFID 태그를 스캔하세요.")
        layout.addWidget(self.info_label)
        self.setLayout(layout)

    def handle_auth_result(self, result):
        """RFID 인증 결과를 받아 화면을 변경"""
        if result == "succeeded":
            self.stacked_widget.setCurrentIndex(3)  # 인증 성공 시 화면 3으로 전환
        else:
            QMessageBox.warning(self, "❌ 인증 실패", "RFID ID가 일치하지 않습니다.")
            self.stacked_widget.setCurrentIndex(1)  # 인증 실패 시 이전 화면으로


class LoginScreen(QWidget):
    """ Screen 2-2: ID & Password 로그인 화면 """

    def __init__(self, stacked_widget):
        super(LoginScreen, self).__init__()
        self.stacked_widget = stacked_widget
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.info_label = QLabel("👤 ID와 비밀번호를 입력하세요.")
        layout.addWidget(self.info_label)

        self.id_input = QLineEdit(self)
        self.id_input.setPlaceholderText("User ID")
        layout.addWidget(self.id_input)

        self.pw_input = QLineEdit(self)
        self.pw_input.setPlaceholderText("Password")
        self.pw_input.setEchoMode(QLineEdit.Password)  # 비밀번호 숨김
        layout.addWidget(self.pw_input)

        self.login_btn = QPushButton("🔑 로그인", self)
        self.login_btn.clicked.connect(self.verify_login)
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

    def verify_login(self):
        """ ID & Password 확인 후 `/human_to_meet` ID와 비교 """
        user_id = self.id_input.text().strip()
        password = self.pw_input.text().strip()

        #check login information
        if self.authenticate_user(user_id, password):
            QMessageBox.information(self, "Login Success", "Authentication Complete!")
            if received_user_id and user_id == received_user_id:
                QMessageBox.information(self, "✅ 인증 성공", "사용자 인증이 완료되었습니다!")
                gui_login_result_pub.publish("succeeded")
                self.stacked_widget.authenticated_user = user_id
                self.stacked_widget.setCurrentIndex(3)  # ArrivedScreen으로 이동
            else:
                gui_login_result_pub.publish("failed")
                QMessageBox.warning(self, "❌ 인증 실패", "ID가 일치하지 않습니다.")
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

class ArrivedScreen(QWidget):
    """ 📦 Arrived 화면: caller / recipient 역할 확인 후 UI 표시 """

    def __init__(self, stacked_widget):
        super(ArrivedScreen, self).__init__()
        self.stacked_widget = stacked_widget
        self.initUI()
        self.check_role_timer = QTimer(self)
        self.check_role_timer.timeout.connect(self.update_role)
        self.check_role_timer.start(1000)  # 1000ms마다 역할 확인

    def initUI(self):
        self.layout = QVBoxLayout()
        self.instruction_label = QLabel("🔄 역할 확인 중...")
        self.layout.addWidget(self.instruction_label)
        self.setLayout(self.layout)

    def update_role(self):
        global received_role
        """ `received_role`을 기반으로 UI 업데이트 """
        if received_role == "caller":
            self.setup_caller_ui()
            self.check_role_timer.stop()  # 역할이 확인되면 타이머 중지
        elif received_role == "recipient":
            self.setup_recipient_ui()
            self.check_role_timer.stop()  # 역할이 확인되면 타이머 중지
        else:
            QTimer.singleShot(1000, lambda: QMessageBox.warning(self, "❌ 오류", "역할 정보가 없습니다."))
            rospy.loginfo(f"errrrrrrrrror!!!!!!!!!!!!!!!!!!!!!!!시발 당장 이석권 불러 치명적인 페이탈 에러야")
            self.check_role_timer.stop()

    def setup_caller_ui(self):
        """ 📦 Caller UI 설정 """
        self.instruction_label.setText("📦 서랍에 문서를 적재하세요.")
        self.complete_btn = QPushButton("✅ 완료", self)
        self.complete_btn.clicked.connect(self.show_popup)
        self.layout.addWidget(self.complete_btn)

    def setup_recipient_ui(self):
        """ 📥 Recipient UI 설정 """
        self.instruction_label.setText("📥 서랍에서 문서를 꺼내세요.")
        self.pickup_btn = QPushButton("📤 픽업", self)
        self.pickup_btn.clicked.connect(self.show_popup)
        self.layout.addWidget(self.pickup_btn)

    def show_popup(self):
        """ ✅ 작업 완료 메시지 """
        QTimer.singleShot(100, lambda: QMessageBox.information(self, "✅ 완료", "작업이 완료되었습니다."))
        QTimer.singleShot(10, lambda: is_interacting_with_human_done_pub.publish("done"))
        self.close()


if __name__ == "__main__":
    # ROS 초기화
    rospy.init_node('human_to_meet_listener', anonymous=True)
    
    app = QApplication(sys.argv)
    stacked_widget = QStackedWidget()
    stacked_widget.authenticated_user = None  # 인증된 사용자 저장

    is_interacting_with_human_done_pub = rospy.Publisher('/is_interacting_with_human', String, queue_size = 10)
    rfid_auth_request_pub = rospy.Publisher('/rfid_auth_request', String, queue_size = 10)
    gui_login_result_pub = rospy.Publisher('/gui_login_result', String, queue_size = 10)
    human_to_meet_sub = rospy.Subscriber('/human_to_meet', String, human_to_meet_callback)
    

    stacked_widget.addWidget(SelectMethodScreen(stacked_widget))  # Screen 1
    stacked_widget.addWidget(RFIDScreen(stacked_widget))  # Screen 2-1
    stacked_widget.addWidget(LoginScreen(stacked_widget))  # Screen 2-2
    stacked_widget.addWidget(ArrivedScreen(stacked_widget))  # Screen 3

    stacked_widget.setCurrentIndex(0)  # 첫 화면
    stacked_widget.showFullScreen()

    sys.exit(app.exec_())

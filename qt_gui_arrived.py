# -*- coding: utf-8 -*-
#!/usr/bin/env python
import sys
import os
import rospy
from std_msgs.msg import String
from PyQt4.QtGui import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QPixmap, QSpacerItem, QSizePolicy

class MyApp(QWidget):
    def __init__(self):
        super(MyApp, self).__init__()
        self.initUI()
        rospy.init_node('gui_node', anonymous=True)
        self.temp1_pub = rospy.Publisher('pickup', String, queue_size=10)
        self.temp2_pub = rospy.Publisher('delivery', String, queue_size=10)

    def initUI(self):
        # 이미지 경로 설정 (상대 경로로 관리)
        image_path = os.path.join(os.path.dirname(__file__), 'static', 'img', 'kawaii.jpg')
        pixmap = QPixmap(image_path)

        # 이미지 크기 조정
        pixmap = pixmap.scaled(300, 300, aspectRatioMode=True)

        # QLabel에 이미지 설정
        image_label = QLabel(self)
        image_label.setPixmap(pixmap)

        # 버튼 생성
        btn1 = QPushButton('물품수령', self)
        btn1.clicked.connect(self.publish_temp1)
        
        btn2 = QPushButton('물품인도', self)
        btn2.clicked.connect(self.publish_temp2)

        # 레이아웃 설정
        hbox = QHBoxLayout()
        hbox.addWidget(image_label)
        
        vbox = QVBoxLayout()
        vbox.addWidget(btn1)
        vbox.addWidget(btn2)

        # 레이아웃 간격 추가
        vbox.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        hbox.addLayout(vbox)
        self.setLayout(hbox)

        self.setWindowTitle('물품운반로봇 인터페이스')
        self.setGeometry(100, 100, 800, 600)
        self.show()

    def publish_temp1(self):
        rospy.loginfo('물품수령 버튼 클릭됨')
        self.temp1_pub.publish('물품수령')

    def publish_temp2(self):
        rospy.loginfo('물품인도 버튼 클릭됨')
        self.temp2_pub.publish('물품인도')

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        ex = MyApp()
        sys.exit(app.exec_())
    except Exception as e:
        rospy.logerr("Qt application could not start: %s", str(e))

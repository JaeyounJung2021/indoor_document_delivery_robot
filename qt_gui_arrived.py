# -*- coding: utf-8 -*-
#!/usr/bin/env python
import sys
import os
import rospy
from std_msgs.msg import String
from PyQt4.QtGui import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QPixmap, QSpacerItem, QSizePolicy, QFont
from PyQt4.QtCore import Qt

class MyApp(QWidget):
    def __init__(self):
        super(MyApp, self).__init__()
        self.initUI()
        rospy.init_node('gui_node', anonymous=True)
        self.pickup_pub = rospy.Publisher('pickup', String, queue_size=10)
        self.delivery_pub = rospy.Publisher('delivery', String, queue_size=10)

    def initUI(self):
        self.setStyleSheet("""
            background-color: #f3f3f3;
            
            QLabel {
                color: #333;
                font-size: 2.5em;
                font-weight: bold;
                margin-bottom: 30px;
            }

            QPushButton {
                background-color: #007BFF;
                color: white;
                font-size: 1.5em;
                padding: 12px;
                border-radius: 10px;
                border: none;
                margin: 10px 0;
            }

            QPushButton:hover {
                background-color: #0056b3;
            }

            QPushButton:pressed {
                background-color: #003f7f;
            }
        """)
        # Set image path (using relative path)
        image_path = os.path.join(os.path.dirname(__file__), 'static', 'img', 'kawaii.jpg')
        pixmap = QPixmap(image_path)
        # Resize image, 300 x 300
        pixmap = pixmap.scaled(300, 300, aspectRatioMode=Qt.KeepAspectRatio) 

        # Set image to QLabel
        image_label = QLabel(self)
        image_label.setPixmap(pixmap)

        # Create buttons
        btn1 = QPushButton('Pickup', self)
        btn1.clicked.connect(self.publish_pickup)
        
        btn2 = QPushButton('Delivery', self)
        btn2.clicked.connect(self.publish_delivery)

        # Layout setup, QHBoxLayout은 좌 -> 우 레이블 배치.
        hbox = QHBoxLayout()
        hbox.addWidget(image_label)
        
        #Layout setup, QVBoxLayout은 위 -> 아래 레이블 배치.
        vbox = QVBoxLayout()
        vbox.addWidget(btn1)
        vbox.addWidget(btn2)

        vbox.setAlignment(Qt.AlignVCenter)  # 버튼을 수직 중앙 정렬
        
        hbox.addLayout(vbox)
        self.setLayout(hbox)

        self.setWindowTitle('Cargo Transport Robot Interface')
        self.showFullScreen()  # 전체화면 적용
        self.show()

    def publish_pickup(self):
        rospy.loginfo('Pickup button clicked')
        self.pickup_pub.publish('Pickup')

    def publish_delivery(self):
        rospy.loginfo('Delivery button clicked')
        self.delivery_pub.publish('Delivery')

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        app.setFont(QFont("Arial", 12))  # Set font to a common English font
        ex = MyApp()
        sys.exit(app.exec_())
    except Exception as e:
        rospy.logerr("Qt application could not start: %s", str(e))

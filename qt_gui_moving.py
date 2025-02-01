# -*- coding: utf-8 -*-
#!/usr/bin/env python
import sys
import math
from PyQt4.QtCore import Qt, QTimer
from PyQt4.QtGui import QApplication, QWidget, QLabel, QVBoxLayout, QFont, QPixmap, QTransform, QPainter, QBrush, QColor

class RobotCallingWindow(QWidget):
    def __init__(self):
        super(RobotCallingWindow, self).__init__()
        self.rotationAngle = 0  # Initialize rotation angle
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Calling Robot...')
        self.setStyleSheet('background-color: #f3f3f3;')
        self.showFullScreen()  # 전체 화면으로 설정
        layout = QVBoxLayout()

        # Title
        title = QLabel('The robot is being called...')
        title.setStyleSheet('color: #007BFF; font-size: 2.5em; margin-bottom: 20px;')
        layout.addWidget(title, alignment=Qt.AlignCenter)

        # Subtext
        subtext = QLabel('Please wait a moment.')
        subtext.setStyleSheet('color: #555; font-size: 1.3em; margin-bottom: 40px;')
        layout.addWidget(subtext, alignment=Qt.AlignCenter)

        # Spinner (Loading Animation)
        self.spinner = QLabel(self)
        self.spinner.setFixedSize(70, 70)
        layout.addWidget(self.spinner, alignment=Qt.AlignCenter)

        self.createSpinnerImage()

        # Animation Timer
        self.animation = QTimer(self)
        self.animation.timeout.connect(self.rotateSpinner)
        self.animation.start(50)  # 50ms마다 업데이트 (약 20FPS)

        # Status Text
        status_text = QLabel('The robot is moving to your location.')
        status_text.setStyleSheet('color: #333; font-size: 1em;')
        layout.addWidget(status_text, alignment=Qt.AlignCenter)

        # Set layout
        self.setLayout(layout)

    def createSpinnerImage(self):
        """ 여러 개의 원을 원형으로 배치한 로딩 애니메이션 이미지 생성 """
        self.original_pixmap = QPixmap(70, 70)
        self.original_pixmap.fill(Qt.transparent)

        painter = QPainter(self.original_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        brush = QBrush(QColor("#007BFF"))
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)

        center_x, center_y = 35, 35  # 중심 좌표
        radius = 20  # 원이 배치될 반지름
        dot_size = 8  # 점 크기

        for i in range(8):  # 8개의 점을 원형으로 배치
            angle = math.radians(i * 45)  # 360도를 8개로 나눠 배치
            x = center_x + math.cos(angle) * radius - dot_size / 2
            y = center_y + math.sin(angle) * radius - dot_size / 2
            painter.drawEllipse(int(x), int(y), dot_size, dot_size)

        painter.end()
        self.spinner.setPixmap(self.original_pixmap)

    def rotateSpinner(self):
        """ 원형으로 배치된 점들이 회전하는 애니메이션 """
        self.rotationAngle = (self.rotationAngle + 30) % 360  # 회전 속도 조절
        transform = QTransform()
        transform.translate(35, 35)  # 중심으로 이동
        transform.rotate(self.rotationAngle)
        transform.translate(-35, -35)  # 다시 원래 위치로 이동

        rotated_pixmap = self.original_pixmap.transformed(transform, Qt.SmoothTransformation)
        self.spinner.setPixmap(rotated_pixmap)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 12))
    ex = RobotCallingWindow()
    ex.show()
    sys.exit(app.exec_())

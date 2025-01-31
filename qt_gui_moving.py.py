#!/usr/bin/env python
import sys
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QFrame, QSpacerItem, QSizePolicy

class RobotCallingWindow(QWidget):
    def __init__(self):
        super(RobotCallingWindow, self).__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('로봇 호출 중...')
        self.setFixedSize(400, 300)
        self.setStyleSheet('background-color: #f3f3f3;')

        layout = QVBoxLayout()

        # Title
        title = QLabel('로봇이 호출되고 있습니다...')
        title.setStyleSheet('color: #007BFF; font-size: 2.5em; margin-bottom: 20px;')
        layout.addWidget(title, alignment=Qt.AlignCenter)

        # Subtext
        subtext = QLabel('잠시만 기다려 주세요.')
        subtext.setStyleSheet('color: #555; font-size: 1.3em; margin-bottom: 40px;')
        layout.addWidget(subtext, alignment=Qt.AlignCenter)

        # Spinner (Circular loading)
        spinner = QFrame(self)
        spinner.setStyleSheet('''
            border: 6px solid rgba(0, 0, 0, 0.1);
            border-top: 6px solid #007BFF;
            border-radius: 50%;
            width: 70px;
            height: 70px;
            margin-bottom: 20px;
        ''')
        layout.addWidget(spinner, alignment=Qt.AlignCenter)

        # Animation of Spinner
        self.animation = QTimer(self)
        self.animation.timeout.connect(self.rotateSpinner)
        self.animation.start(16)

        # Status Text
        status_text = QLabel('로봇이 사용자 위치로 이동 중입니다.')
        status_text.setStyleSheet('color: #333; font-size: 1em;')
        layout.addWidget(status_text, alignment=Qt.AlignCenter)

        # Set layout
        self.setLayout(layout)

    def rotateSpinner(self):
        angle = (self.rotationAngle + 6) % 360  # Incrementing the rotation angle
        self.rotationAngle = angle
        self.spinner.setStyleSheet(f'border: 6px solid rgba(0, 0, 0, 0.1);'
                                   f'border-top: 6px solid #007BFF;'
                                   f'border-radius: 50%;'
                                   f'width: 70px; height: 70px; margin-bottom: 20px;'
                                   f'transform: rotate({angle}deg);')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = RobotCallingWindow()
    ex.show()
    sys.exit(app.exec_())

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
        self.setFixedSize(400, 300)
        self.setStyleSheet('background-color: #f3f3f3;')
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
        self.original_pixmap = QPixmap(70, 70)  # Create an empty pixmap
        self.original_pixmap.fill(Qt.transparent)  # Create a transparent image

        # Draw circular loading spinner
        painter = QPainter(self.original_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        brush = QBrush(QColor("#007BFF"))
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(10, 10, 50, 50)  # Draw a circle
        painter.end()

        self.spinner.setPixmap(self.original_pixmap)
        self.spinner.setFixedSize(70, 70)
        layout.addWidget(self.spinner, alignment=Qt.AlignCenter)

        # Animation Timer
        self.animation = QTimer(self)
        self.animation.timeout.connect(self.rotateSpinner)
        self.animation.start(16)

        # Status Text
        status_text = QLabel('The robot is moving to your location.')
        status_text.setStyleSheet('color: #333; font-size: 1em;')
        layout.addWidget(status_text, alignment=Qt.AlignCenter)

        # Set layout
        self.setLayout(layout)

    def rotateSpinner(self):
        self.rotationAngle = (self.rotationAngle + 6) % 360  # Increment angle
        transform = QTransform()
        transform.rotate(self.rotationAngle)

        rotated_pixmap = self.original_pixmap.transformed(transform, Qt.SmoothTransformation)
        self.spinner.setPixmap(rotated_pixmap)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 12))
    ex = RobotCallingWindow()
    ex.show()
    sys.exit(app.exec_())


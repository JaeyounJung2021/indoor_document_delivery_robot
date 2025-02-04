# -*- coding: utf-8 -*-
#!/usr/bin/env python

'''토픽값에 따라 QT를 제어하는 코드'''
import rospy
import subprocess  # 외부(여기서는 QT) 프로그램을 실행하고, 출력 및 에러를 처리.
from actionlib_msgs.msg import GoalStatusArray, GoalStatus

# Qt GUI 실행 여부를 추적하는 변수
gui_process1 = None
gui_process2 = None

def status_callback(msg):
    global gui_process1, gui_process2

    if not msg.status_list:
        return
    
    last_status = msg.status_list[-1].status
    
    if last_status == 3:  # SUCCEEDED
        rospy.loginfo("Goal reached successfully!")
        gui_process2 = subprocess.Popen(["python3", "qt_gui_path.py"])
        if gui_process1:  # gui_process1이 실행 중이라면 종료
            gui_process1.terminate()
            gui_process1 = None
    elif last_status == 1:  # ACTIVE
        rospy.loginfo("Navigation in progress...")
        gui_process1 = subprocess.Popen(["python3", "qt_gui_moving.py"])  # PyQt5는 python3으로 실행
        if gui_process2:  # gui_process2가 실행 중이라면 종료
            gui_process2.terminate()
            gui_process2 = None
    else:
        rospy.loginfo(f"Current status: {last_status}")

def main():
    rospy.init_node('move_base_status_listener', anonymous=True)
    rospy.Subscriber("/move_base/status", GoalStatusArray, status_callback)
    rospy.spin()

if __name__ == '__main__':
    main()

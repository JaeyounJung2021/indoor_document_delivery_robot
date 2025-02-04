# -*- coding: utf-8 -*-
#!/usr/bin/env python

'''토픽값에 따라 QT를 제어하는 코드'''
import rospy
import subprocess  # 외부(여기서는 QT) 프로그램을 실행하고, 출력 및 에러를 처리.
from actionlib_msgs.msg import GoalStatusArray

# Qt GUI 실행 여부를 추적하는 변수
gui_process1 = None
gui_process2 = None
is_gui1_running = False
is_gui2_running = False

def status_callback(msg):
    global gui_process1, gui_process2, is_gui1_running, is_gui2_running

    if not msg.status_list:
        return
    
    last_status = msg.status_list[-1].status

    if last_status == 3:  # SUCCEEDED
        rospy.loginfo("Goal reached successfully!")
        rospy.loginfo(f"is_gui2_running : {is_gui2_running}")
        if not is_gui2_running:
            if gui_process1:  # 기존의 gui_process1 종료
                gui_process1.terminate()
                gui_process1 = None
                is_gui1_running = False

            gui_process2 = subprocess.Popen(["python3", "qt_gui_path.py"])
            is_gui2_running = True
    elif last_status == 1:  # ACTIVE
        rospy.loginfo("Navigation in progress...")
        if not is_gui1_running:
            if gui_process2:  # 기존의 gui_process2 종료
                gui_process2.terminate()
                gui_process2 = None
                is_gui2_running = False

            gui_process1 = subprocess.Popen(["python3", "qt_gui_moving.py"])  # PyQt5는 python3으로 실행
            is_gui1_running = True
    else:
        rospy.loginfo(f"Current status: {last_status}")

def main():
    rospy.init_node('qt_gui_node', anonymous=True)
    rospy.Subscriber("/move_base/status", GoalStatusArray, status_callback)
    rospy.spin()

if __name__ == '__main__':
    main()
# -*- coding: utf-8 -*-
#!/usr/bin/env python

'''토픽값에 따라 QT를 제어하는 코드'''
import rospy
import subprocess  # 외부(여기서는 QT) 프로그램을 실행하고, 출력 및 에러를 처리.
from actionlib_msgs.msg import GoalStatusArray, GoalStatus

# Qt GUI 실행 여부를 추적하는 변수
gui_process1 = None
gui_process2 = None

def moving_status_callback(msg):
    global gui_process1, gui_process2
    if msg.status_list:  # 상태 리스트가 비어있지 않을때만 처리
        status = msg.status_list[0].status
        if status == 1:  # /move_base/status == 1 이면 이동중
            if gui_process1 is None:
                rospy.loginfo("로봇 이동중일때의 qt GUI 실행")
                gui_process1 = subprocess.Popen(["python3", "qt_gui_moving.py"])  # PyQt5는 python3으로 실행
                if gui_process2:  # gui_process2가 실행 중이라면 종료
                    gui_process2.terminate()
                    gui_process2 = None
        elif status == 3:  # /move_base/status == 3 이면 목적지 도착
            if gui_process2 is None:
                rospy.loginfo("로봇 목적지 도착상태일때의 qt GUI 실행")
                gui_process2 = subprocess.Popen(["python3", "qt_gui_path.py"])
                if gui_process1:  # gui_process1이 실행 중이라면 종료
                    gui_process1.terminate()
                    gui_process1 = None

#키 입력으로 qt테스트 하기 위한 코드(추후 삭제)
def test_gui_execution():
    while True:
        user_input = input("1: 이동중, 3: 목적지 도착, q: 종료: ")
        if user_input == "1":
            rospy.loginfo("테스트: 이동중 상태로 설정")
            moving_status_callback(GoalStatusArray(status_list=[GoalStatus(status=1)]))
        elif user_input == "3":
            rospy.loginfo("테스트: 목적지 도착 상태로 설정")
            moving_status_callback(GoalStatusArray(status_list=[GoalStatus(status=3)]))
        elif user_input == "q":
            rospy.loginfo("테스트 종료")
            break

def main():
    rospy.init_node('qt_gui_node', anonymous=True)
    rospy.Subscriber('/move_base/result', GoalStatusArray, moving_status_callback)
    # 테스트 모드에서는 토픽을 구독하는 대신 키 입력으로 테스트(추후 삭제)
    test_gui_execution()
    rospy.spin()

if __name__ == "__main__":
    main()

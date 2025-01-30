#!/usr/bin/env python3
import rospy
import os
import time
import webbrowser
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from actionlib_msgs.msg import GoalStatusArray

class Delivery:
    """배송 정보를 관리하는 클래스"""
    def __init__(self, caller_name, caller_dept, caller_coord, caller_id,
                 recipient_name, recipient_dept, recipient_coord, recipient_id):
        self.caller_name = caller_name
        self.caller_dept = caller_dept
        self.caller_coord = caller_coord  # (x, y) 좌표
        self.caller_id = caller_id

        self.recipient_name = recipient_name
        self.recipient_dept = recipient_dept
        self.recipient_coord = recipient_coord  # (x, y) 좌표
        self.recipient_id = recipient_id


class DeliveryRobot:
    def __init__(self):
        rospy.init_node("delivery_robot", anonymous=True)

        # 로봇 이동 퍼블리셔
        self.pub_goal = rospy.Publisher("/move_base_simple_goal", PoseStamped, queue_size=10)
        
        # ESP8266 제어 퍼블리셔
        self.esp_command_pub = rospy.Publisher("/esp8266_command", String, queue_size=10)

        # 호출 요청을 받을 서브스크라이버
        self.call_sub = rospy.Subscriber("/call_request", String, self.call_request_callback)
        
        # 목표 도착 상태를 구독
        self.status_sub = rospy.Subscriber("/move_base/status", GoalStatusArray, self.callback)

        # 배송 객체
        self.delivery1 = None
        self.delivery2 = None

        self.current_goal = PoseStamped()
        rospy.loginfo("Delivery robot initialized and waiting for calls.")

    def call_request_callback(self, msg):
        """배송 요청을 받아서 객체를 생성"""
        data = msg.data.split(",")  
        if len(data) != 8:
            rospy.logwarn("Invalid delivery info format. Expected 8 values.")
            return

        caller_name, caller_dept, caller_x, caller_y, caller_id, recipient_name, recipient_dept, recipient_x, recipient_y = data
        caller_coord = (float(caller_x), float(caller_y))
        recipient_coord = (float(recipient_x), float(recipient_y))

        if self.delivery1 is None:
            self.delivery1 = Delivery(caller_name, caller_dept, caller_coord, caller_id,
                                    recipient_name, recipient_dept, recipient_coord, caller_id)
            rospy.loginfo(f"Delivery1 created: {caller_name} → {recipient_name}")
        elif self.delivery2 is None:
            self.delivery2 = Delivery(caller_name, caller_dept, caller_coord, caller_id,
                                    recipient_name, recipient_dept, recipient_coord, caller_id)
            rospy.loginfo(f"Delivery2 created: {caller_name} → {recipient_name}")


    def move_command(self, pos_x, pos_y, ori_z=0.0, ori_w=1.0):
        """좌표값을 받아 로봇 이동 명령을 퍼블리쉬"""
        goal = PoseStamped()
        goal.header.stamp = rospy.Time.now()
        goal.header.frame_id = 'map'
        goal.pose.position.x = pos_x
        goal.pose.position.y = pos_y
        goal.pose.orientation.z = ori_z
        goal.pose.orientation.w = ori_w
        
        self.pub_goal.publish(goal)
        self.current_goal = goal
        rospy.loginfo(f"Moving to ({pos_x}, {pos_y})...")

    def callback(self, status):
        """로봇 도착 시 ESP8266 제어"""
        if status.status_list and status.status_list[-1].status == 3:  # 도착 상태
            rospy.loginfo("Robot has reached the destination.")
            webbrowser.open('http://localhost:5000/')
            self.esp_command_pub.publish("Arrival")  # ESP8266 제어 명령 전송
        else:
            rospy.loginfo("Arrival failed or still moving.")

    def process_deliveries(self):
        """배송을 처리하는 메인 함수"""
        while not rospy.is_shutdown():
            if self.delivery1 or self.delivery2:
                rospy.loginfo("Processing deliveries...")
                
                if self.delivery1:
                    rospy.loginfo("Delivering from Caller 1 to Recipient 1...")
                    self.move_command(*self.delivery1.caller_coord)
                    rospy.sleep(5)
                    self.move_command(*self.delivery1.recipient_coord)
                    rospy.sleep(5)
                
                if self.delivery2:
                    rospy.loginfo("Delivering from Caller 2 to Recipient 2...")
                    self.move_command(*self.delivery2.caller_coord)
                    rospy.sleep(5)
                    self.move_command(*self.delivery2.recipient_coord)
                    rospy.sleep(5)
                
                rospy.loginfo("All deliveries completed. Resetting system...")
                self.delivery1 = None
                self.delivery2 = None

            rospy.sleep(1)

    def exit(self): 
        """시스템 종료"""
        os.system("rosnode kill /rosout") 
        time.sleep(1) 
        os.system("shutdown now") 

    def exit_process(self): 
        """ROS 노드 종료"""
        os.system("rosnode kill /amcl") 
        os.system("rosnode kill /base_link_to_laser4")
        os.system("rosnode kill /map_server")
        os.system("rosnode kill /md_robot_node")
        os.system("rosnode kill /move_base") 
        os.system("rosnode kill /robot_state_publisher") 
        os.system("rosnode kill /rviz")
        os.system("rosnode kill /turtlebot3_core") 
        os.system("rosnode kill /turtlebot3_diagnostics") 
        os.system("rosnode kill /ydlidar_lidar_publisher")

    def run(self):
        """노드 실행"""
        self.process_deliveries()
        rospy.spin()

if __name__ == "__main__":
    robot = DeliveryRobot()
    robot.run()
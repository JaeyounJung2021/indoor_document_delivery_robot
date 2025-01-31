#!/usr/bin/env python3
import rospy
import os
import time
import webbrowser
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from std_msgs.msg import String
from actionlib_msgs.msg import GoalStatusArray
from itertools import permutations
import math

class Delivery:
    """배송 정보를 관리하는 클래스"""
    def __init__(self, caller_name, caller_dept, caller_coord, caller_id,
                 recipient_name, recipient_dept, recipient_coord, recipient_id):
        self.caller_name = caller_name
        self.caller_dept = caller_dept
        self.caller_coord = caller_coord  # (x, y, ori_z, ori_w)
        self.caller_id = caller_id

        self.recipient_name = recipient_name
        self.recipient_dept = recipient_dept
        self.recipient_coord = recipient_coord  # (x, y, ori_z, ori_w)
        self.recipient_id = recipient_id

class DeliveryRobot:

    def __init__(self):
        rospy.init_node("delivery_robot", anonymous=True)
        self.pub_goal = rospy.Publisher("/move_base_simple_goal", PoseStamped, queue_size=10)
        self.esp_command_pub = rospy.Publisher("/esp8266_command", String, queue_size=10)
        self.call_sub = rospy.Subscriber("/call_request", String, self.call_request_callback)
        self.status_sub = rospy.Subscriber("/move_base/status", GoalStatusArray, self.callback)
        self.amcl_pose_sub = rospy.Subscriber("/amcl_pose", PoseWithCovarianceStamped, self.amcl_pose_callback)  # AMCL 위치 구독
        self.deliveries = []  # 최대 2개까지 관리
        self.current_goal = PoseStamped()
        self.current_position = (0, 0)  # 로봇의 실제 위치 초기화
        rospy.loginfo("Delivery robot initialized and waiting for calls.")
    
    def amcl_pose_callback(self, msg):
        """AMCL로부터 로봇의 현재 위치를 업데이트하는 콜백"""
        # AMCL에서 받는 위치 정보는 PoseWithCovarianceStamped 객체로, 위치와 회전 정보를 포함함
        position = msg.pose.pose.position
        orientation = msg.pose.pose.orientation
        self.current_position = (position.x, position.y, orientation.z, orientation.w)
        rospy.loginfo(f"Updated current position: {self.current_position}")

    def call_request_callback(self, msg):
        rospy.loginfo("call_request_callback is called")
        data = msg.data.split(",")  
        if len(data) != 14:
            rospy.logwarn("Invalid delivery info format. Expected 14 values.")
            return
        
        caller_name, caller_dept, caller_x, caller_y, caller_ori_z, caller_ori_w, caller_id, \
        recipient_name, recipient_dept, recipient_x, recipient_y, recipient_ori_z, recipient_ori_w, recipient_id = data

        caller_coord = (float(caller_x), float(caller_y), float(caller_ori_z), float(caller_ori_w))
        recipient_coord = (float(recipient_x), float(recipient_y), float(recipient_ori_z), float(recipient_ori_w))

        if len(self.deliveries) < 2:
            new_delivery = Delivery(caller_name, caller_dept, caller_coord, caller_id,
                                    recipient_name, recipient_dept, recipient_coord, recipient_id)
            self.deliveries.append(new_delivery)
            rospy.loginfo(f"✅ New delivery added: {caller_name} → {recipient_name}")
            
            # Delivery 객체의 모든 정보 출력
            rospy.loginfo("Delivery details:")
            rospy.loginfo(f"Caller Name: {new_delivery.caller_name}")
            rospy.loginfo(f"Caller Department: {new_delivery.caller_dept}")
            rospy.loginfo(f"Caller Coordinates: {new_delivery.caller_coord}")
            rospy.loginfo(f"Caller ID: {new_delivery.caller_id}")
            rospy.loginfo(f"Recipient Name: {new_delivery.recipient_name}")
            rospy.loginfo(f"Recipient Department: {new_delivery.recipient_dept}")
            rospy.loginfo(f"Recipient Coordinates: {new_delivery.recipient_coord}")
            rospy.loginfo(f"Recipient ID: {new_delivery.recipient_id}")

            # delivery 객체 새로 생성될 때 마다 그 자리에서 경로 재계산
            self.recalculate_route()
        else:
            rospy.logwarn("⚠️ Maximum deliveries reached. Cannot accept new request.")

    def recalculate_route(self):
        """현재 위치에서 최적의 배송 순서를 결정"""
        if not self.deliveries:
            return
        
        waypoints = []
        for delivery in self.deliveries:
            waypoints.append((delivery.caller_coord, "caller", delivery))
            waypoints.append((delivery.recipient_coord, "recipient", delivery))
        
        # 일단 min_distance를 매우 크게 초기화
        min_distance = float('inf')
        best_route = []

        # waypoint 리스트를 기반으로 가능한 모든 순열(경우의 수) 생성
        for perm in permutations(waypoints):
            # 각 배달건에 대해 수령자보다 호출자에게 먼저 도달하는 경우의 수만 살리고 나머지 전부 continue 해서 건너뛰기
            if not self.valid_sequence(perm):
                continue
            # """주어진 경로의 총 이동 거리 계산"""
            distance = self.calculate_route_distance(perm)
            # min_distance 보다 작으면 best_route에 대입 
            if distance < min_distance:
                min_distance = distance
                best_route = perm
        
        rospy.loginfo("Optimal route recalculated.")
        # """계산된 최적 경로를 따라 real 이동"""
        self.execute_route(best_route)
    
    def valid_sequence(self, route):
        """호출지를 먼저 방문하는 순서인지 확인"""
        visited = set()
        for coord, point_type, delivery in route:
            if point_type == "recipient" and delivery not in visited:
                return False
            visited.add(delivery)
        return True
    
    def calculate_route_distance(self, route):
        """주어진 경로의 총 이동 거리 계산"""
        total_distance = 0
        current_position = self.current_position  # 로봇의 실제 위치 사용
        
        for coord, _, _ in route:
            # 현재 위치의 x, y 좌표와 route에 담긴 호출자/수령자 좌표의 x, y 좌표 비교해서 유클리드 거리 계산해서 total_distance에 누적
            total_distance += math.dist(current_position[:2], coord[:2])
            # 다음 계산을 위해 current_position을 업데이트
            current_position = coord
        # 계산된 총 이동 거리 반환
        return total_distance
    
    def execute_route(self, route):
        """계산된 최적 경로를 따라 real 이동"""
        for coord, point_type, delivery in route:
            rospy.loginfo(f"Moving to {point_type} location: {coord}")
            self.move_command(*coord)
            rospy.sleep(5)
        
        rospy.loginfo("All deliveries completed. Resetting system...")
        self.deliveries.clear()

    def move_command(self, pos_x, pos_y, ori_z=0.0, ori_w=1.0):
        goal = PoseStamped()
        goal.header.stamp = rospy.Time.now()
        goal.header.frame_id = 'map'
        goal.pose.position.x = pos_x
        goal.pose.position.y = pos_y
        goal.pose.orientation.z = ori_z
        goal.pose.orientation.w = ori_w
        
        self.pub_goal.publish(goal)
        self.current_goal = goal
        rospy.loginfo(f"Moving to ({pos_x}, {pos_y}, {ori_z}, {ori_w})...")
    
    def callback(self, status):
        if status.status_list and status.status_list[-1].status == 3:
            rospy.loginfo("Robot has reached the destination.")
            webbrowser.open('http://localhost:5000/')
            self.esp_command_pub.publish("Arrival")
    
    def run(self):
        rospy.spin()

if __name__ == "__main__":
    robot = DeliveryRobot()
    robot.run()

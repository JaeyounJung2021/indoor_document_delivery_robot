import rospy
import threading
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from std_msgs.msg import String
from actionlib_msgs.msg import GoalStatusArray
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import actionlib
import math
from itertools import permutations



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
        
        self.picked_up = False  # 호출지에서 물건을 실었는지 여부를 저장하는 변수



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
        self.executing_route = False  # 경로 이동 중 여부 플래그
        self.move_base_client = actionlib.SimpleActionClient('/move_base', MoveBaseAction)  # 
        rospy.loginfo("Waiting for Action Server")
        self.move_base_client.wait_for_server()
        rospy.loginfo("Action Server Is Ready")
        rospy.loginfo("Delivery robot initialized and waiting for calls.")
        self.goal_status = None  # 목표 상태를 추적하기 위한 변수
        self.event = threading.Event()  # 이벤트 객체 추가: 행동 완료를 기다리기 위한 신호

    def amcl_pose_callback(self, msg):
        """AMCL로부터 로봇의 현재 위치를 업데이트하는 콜백"""
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
        # 기존 이동을 중단하고 새 경로로 이동
        if self.executing_route:
            rospy.loginfo("Current route is being canceled.")
            self.move_base_client.cancel_all_goals()  # 이동 중인 목표 취소
        
        # 새 경로로 이동
        self.execute_route_in_thread(best_route)
    
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
    
    def execute_route_in_thread(self, route):
        """계산된 최적 경로를 별도의 스레드에서 이동"""
        route_thread = threading.Thread(target=self.execute_route, args=(route,))
        route_thread.start()
    
    def execute_route(self, route):
        """계산된 최적 경로를 따라 real 이동"""
        self.executing_route = True
        for coord, point_type, delivery in route:
            rospy.loginfo(f"Moving to {point_type} location: {coord}")
            self.move_command(*coord)
            
            # 목표 도달을 확인할 때까지 기다림
            self.event.clear()  # 이전 이벤트 초기화
            self.event.wait()   # 이벤트 신호 대기
            
            rospy.sleep(2)  # 잠시 대기 후 다음 목표로 이동
        
        rospy.loginfo("All deliveries completed. Resetting system...")
        self.deliveries.clear()
        self.executing_route = False

    def move_command(self, pos_x, pos_y, ori_z=0.0, ori_w=1.0):
        goal = MoveBaseGoal()
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.header.frame_id = 'map'
        goal.target_pose.pose.position.x = pos_x
        goal.target_pose.pose.position.y = pos_y
        goal.target_pose.pose.orientation.z = ori_z
        goal.target_pose.pose.orientation.w = ori_w
        
        self.move_base_client.send_goal(goal)
        rospy.loginfo(f"Moving to ({pos_x}, {pos_y}, {ori_z}, {ori_w})...")

    def callback(self, status):
        if status.status_list and status.status_list[-1].status == 3:
            rospy.loginfo("Robot has reached the destination.")
            
            # 로봇이 도달했을 때 수행할 행동 정의
            self.perform_action_at_destination()
            
            # 행동이 끝났음을 알리기 위해 이벤트 신호 전송
            self.event.set()  # 이벤트 신호 설정 (완료된 상태)
            self.esp_command_pub.publish("Arrival")
    
    def perform_action_at_destination(self):
        """목적지에 도달했을 때 수행할 행동을 정의"""
        rospy.loginfo("Performing actions at the destination...")
        
        for delivery in self.deliveries:
            #"""목적지(호출자)에 도달했을 때 수행할 행동을 정의"""
            if self.current_position == delivery.caller_coord and not delivery.picked_up:
                rospy.loginfo(f"Picked up the package from {delivery.caller_name}.")
                delivery.picked_up = True
            ##"""목적지(수령자)에 도달했을 때 수행할 행동을 정의"""
            elif self.current_position == delivery.recipient_coord and delivery.picked_up:
                rospy.loginfo(f"Delivered the package to {delivery.recipient_name}.")
                self.deliveries.remove(delivery)
        
        rospy.sleep(2)  # 2초 대기 후 진행
    
    def run(self):
        rospy.spin()

if __name__ == "__main__":
    robot = DeliveryRobot()
    robot.run()

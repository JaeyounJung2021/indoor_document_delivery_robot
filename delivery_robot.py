import rospy
import threading
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from std_msgs.msg import String
from actionlib_msgs.msg import GoalStatusArray
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import actionlib
import math
from itertools import permutations
from typing import List, Tuple, Optional

class Delivery:
    """배송 정보를 관리하는 클래스"""
    def __init__(self, caller_name: str, caller_dept: str, 
                 caller_coord: Tuple[float, float, float, float], caller_id: str,
                 recipient_name: str, recipient_dept: str, 
                 recipient_coord: Tuple[float, float, float, float], recipient_id: str):
        self.caller_name = caller_name
        self.caller_dept = caller_dept
        self.caller_coord = caller_coord
        self.caller_id = caller_id
        self.recipient_name = recipient_name
        self.recipient_dept = recipient_dept
        self.recipient_coord = recipient_coord
        self.recipient_id = recipient_id
        self.picked_up = False
        
    def __str__(self) -> str:
        return f"배송 요청: {self.caller_name}님 → {self.recipient_name}님"

class DeliveryRobot:
    def __init__(self):
        rospy.init_node("delivery_robot", anonymous=True)
        
        # 퍼블리셔 초기화
        self._init_publishers()
        
        # 서브스크라이버 초기화
        self._init_subscribers()
        
        # 상태 관리 변수들
        self.deliveries: List[Delivery] = []
        self.current_goal = PoseStamped()
        self.current_position: Tuple[float, float, float, float] = (0, 0, 0, 0)
        self.executing_route = False
        self.route_thread_flag = False
        self.event = threading.Event()
        
        # 액션 클라이언트 설정
        self._setup_action_client()
        rospy.loginfo("배송 로봇이 초기화되어 호출을 기다리고 있습니다.")

    def _init_publishers(self):
        """퍼블리셔 초기화 메서드"""
        try:
            self.pub_goal = rospy.Publisher("/move_base_simple_goal", PoseStamped, queue_size=10)
            self.esp_command_pub = rospy.Publisher("/esp8266_command", String, queue_size=10)
        except Exception as e:
            rospy.logerr(f"퍼블리셔 초기화 실패: {e}")
            raise

    def _init_subscribers(self):
        """서브스크라이버 초기화 메서드"""
        try:
            self.call_sub = rospy.Subscriber("/call_request", String, 
                                           self.call_request_callback)
            self.status_sub = rospy.Subscriber("/move_base/status", GoalStatusArray, 
                                             self.status_callback)
            self.amcl_pose_sub = rospy.Subscriber("/amcl_pose", 
                                                 PoseWithCovarianceStamped, 
                                                 self.amcl_pose_callback)
            self.is_interacting_sub = rospy.Subscriber("/is_interacting_with_human", 
                                                     String, 
                                                     self.is_interacting_with_human_callback)
        except Exception as e:
            rospy.logerr(f"서브스크라이버 초기화 실패: {e}")
            raise

    def _setup_action_client(self):
        """move_base 액션 클라이언트 초기화"""
        self.move_base_client = actionlib.SimpleActionClient('/move_base', MoveBaseAction)
        if not self.move_base_client.wait_for_server(rospy.Duration(30.0)):
            rospy.logerr("이동 베이스 액션 서버를 사용할 수 없습니다!")
            raise RuntimeError("액션 서버 연결 실패!")
        rospy.loginfo("액션 서버가 준비되었습니다.")

    def amcl_pose_callback(self, msg: PoseWithCovarianceStamped) -> None:
        """AMCL로부터 로봇의 현재 위치를 업데이트"""
        position = msg.pose.pose.position
        orientation = msg.pose.pose.orientation
        self.current_position = (position.x, position.y, orientation.z, orientation.w)
        rospy.logdebug(f"현재 위치가 업데이트되었습니다: {self.current_position}")

    def call_request_callback(self, msg: String) -> None:
        """새로운 배송 요청 처리"""
        try:
            data = msg.data.split(",")
            if len(data) != 14:
                rospy.logerr(f"잘못된 배송 정보 형식입니다. {len(data)}개 값이 전달됨, 14개 필요")
                return

            try:
                caller_coord = tuple(map(float, data[2:6]))
                recipient_coord = tuple(map(float, data[9:13]))
            except ValueError as e:
                rospy.logerr(f"좌표 파싱 실패: {e}")
                return

            if len(self.deliveries) < 2:
                new_delivery = Delivery(
                    data[0], data[1], caller_coord, data[6],
                    data[7], data[8], recipient_coord, data[13]
                )
                self.deliveries.append(new_delivery)
                rospy.loginfo(f"새로운 배송이 추가되었습니다: {new_delivery}")
                
                # 경로 재계산
                self.recalculate_route()
            else:
                rospy.logwarn("최대 배송 수(2개)에 도달했습니다. 요청이 거부되었습니다.")

        except Exception as e:
            rospy.logerr(f"배송 요청 처리 중 오류 발생: {e}")

    def recalculate_route(self):
        """현재 위치에서 최적의 배송 순서를 결정하는 메서드"""
        if not self.deliveries:
            rospy.loginfo("처리할 배송 요청이 없습니다.")
            return
        
        waypoints = []
        for delivery in self.deliveries:
            if not delivery.picked_up:
                waypoints.append((delivery.caller_coord, "호출자", delivery))
            waypoints.append((delivery.recipient_coord, "수령자", delivery))
        
        min_distance = float('inf')
        best_route = []

        for perm in permutations(waypoints):
            if not self._is_valid_sequence(perm):
                continue
                
            total_distance = self._calculate_route_distance(perm)
            if total_distance < min_distance:
                min_distance = total_distance
                best_route = perm
        
        rospy.loginfo(f"최적 경로가 계산되었습니다. 총 거리: {min_distance:.2f}m")
        
        if self.executing_route:
            rospy.loginfo("현재 경로를 취소하고 새로운 경로로 변경합니다.")
            self.move_base_client.cancel_all_goals()
            self.route_thread_flag = True
        
        self.execute_route_in_thread(best_route)

    def _is_valid_sequence(self, route) -> bool:
        """경로의 유효성을 검증"""
        visited_deliveries = set()
        
        for coord, point_type, delivery in route:
            if point_type == "수령자":
                if delivery.picked_up:
                    if delivery not in visited_deliveries:
                        visited_deliveries.add(delivery)
                elif delivery not in visited_deliveries:
                    return False
            elif point_type == "호출자":
                if not delivery.picked_up and delivery not in visited_deliveries:
                    visited_deliveries.add(delivery)
                    
        return True

    def _calculate_route_distance(self, route) -> float:
        """주어진 경로의 총 이동 거리를 계산"""
        total_distance = 0.0
        current_pos = self.current_position
        
        for next_point, _, _ in route:
            distance = math.sqrt(
                (current_pos[0] - next_point[0]) ** 2 + 
                (current_pos[1] - next_point[1]) ** 2
            )
            total_distance += distance
            current_pos = next_point
            
        return total_distance

    def execute_route_in_thread(self, route):
        """최적화된 경로를 별도의 스레드에서 실행"""
        if not route:
            rospy.logwarn("실행할 경로가 없습니다.")
            return
            
        route_thread = threading.Thread(target=self.execute_route, args=(route,))
        route_thread.start()
        rospy.loginfo("경로 실행 스레드가 시작되었습니다.")

    def execute_route(self, route: List[Tuple]) -> None:
        """배송 경로 실행"""
        self.executing_route = True
        try:
            for coord, point_type, delivery in route:
                if self.route_thread_flag:
                    rospy.loginfo("새로운 배송 요청으로 인해 현재 경로가 취소되었습니다")
                    break

                rospy.loginfo(f"{point_type} 위치로 이동 중: {coord}")
                self.move_command(*coord)
                
                self.event.clear()
                if not self.event.wait(timeout=300.0):
                    rospy.logerr("목적지 도착 대기 시간 초과")
                    continue
                
                rospy.sleep(3)
                
        except Exception as e:
            rospy.logerr(f"경로 실행 중 오류 발생: {e}")
        finally:
            self.executing_route = False
            self.route_thread_flag = False

    def move_command(self, pos_x: float, pos_y: float, ori_z: float = 0.0, ori_w: float = 1.0):
        """로봇 이동 명령 전송"""
        goal = MoveBaseGoal()
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.header.frame_id = 'map'
        goal.target_pose.pose.position.x = pos_x
        goal.target_pose.pose.position.y = pos_y
        goal.target_pose.pose.orientation.z = ori_z
        goal.target_pose.pose.orientation.w = ori_w
        
        self.move_base_client.send_goal(goal)
        rospy.loginfo(f"이동 목표가 설정되었습니다: ({pos_x}, {pos_y})")

    def status_callback(self, status: GoalStatusArray) -> None:
        """이동 상태 업데이트 처리"""
        if not status.status_list:
            return
            
        latest_status = status.status_list[-1].status
        if latest_status == 3:  # 성공
            rospy.loginfo("목표 지점에 도달했습니다")
            self.perform_action_at_destination()
        elif latest_status == 4:  # 실패
            rospy.logwarn("목표 도달 실패 - 재시도 중")
            self._handle_goal_aborted()

    def _handle_goal_aborted(self) -> None:
        """실패한 네비게이션 처리"""
        retry_count = getattr(self, '_retry_count', 0)
        if retry_count < 3:
            self._retry_count = retry_count + 1
            rospy.logwarn(f"네비게이션 재시도 중 (시도 {self._retry_count}/3)")
            self.move_command(*self.current_goal.pose.position)
        else:
            rospy.logerr("3회 시도 후 네비게이션 실패")
            self._retry_count = 0
            self.event.set()

    def is_interacting_with_human_callback(self, msg: String) -> None:
        """사용자 상호작용 완료 처리"""
        if msg.data == "done":
            rospy.loginfo("사용자와의 상호작용이 완료되었습니다.")
            self.perform_action_at_destination()
            self.event.set()

    def perform_action_at_destination(self):
        """목적지 도착 시 수행할 작업"""
        for delivery in self.deliveries[:]:  # 복사본으로 순회하여 안전하게 제거
            if self.current_position == delivery.caller_coord and not delivery.picked_up:
                rospy.loginfo(f"{delivery.caller_name}님으로부터 물건을 수령했습니다.")
                delivery.picked_up = True
                
            elif self.current_position == delivery.recipient_coord and delivery.picked_up:
                rospy.loginfo(f"{delivery.recipient_name}님께 물건을 전달했습니다.")
                self.deliveries.remove(delivery)

    def run(self):
        """메인 실행 루프"""
        rospy.spin()

if __name__ == "__main__":
    try:
        robot = DeliveryRobot()
        robot.run()
    except rospy.ROSInterruptException:
        rospy.loginfo("프로그램이 종료되었습니다.")
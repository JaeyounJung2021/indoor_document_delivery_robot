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
from move_base_msgs.msg import MoveBaseActionResult
import actionlib_msgs.msg


class Delivery:
    """배송 정보를 관리하는 클래스"""
    def __init__(self, caller_name: str, caller_dept: str, 
                 caller_coord: Tuple[float, float, float, float], caller_id: str,
                 recipient_name: str, recipient_dept: str, 
                 recipient_coord: Tuple[float, float, float, float], recipient_id: str,
                 caller_rfid_uid: str = "", recipient_rfid_uid: str = ""):
        self.caller_name = caller_name
        self.caller_dept = caller_dept
        self.caller_coord = caller_coord
        self.caller_id = caller_id
        self.recipient_name = recipient_name
        self.recipient_dept = recipient_dept
        self.recipient_coord = recipient_coord
        self.recipient_id = recipient_id
        self.picked_up = False
        self.caller_rfid_uid = caller_rfid_uid
        self.recipient_rfid_uid = recipient_rfid_uid
        
    
    #'->' 는 '타입 힌트'라는 파이썬 문법으로, 이 함수가 반환하는 데이터의 타입이 str임을 알려줌
    #객체 생성될때 자동으로 호출됨
    def __str__(self) -> str:
        return f"배송 요청이 들어왔습니다: {self.caller_name}님 → {self.recipient_name}님"

class DeliveryRobot:
    def __init__(self):
        rospy.init_node("delivery_robot", anonymous=True)
        
        # 퍼블리셔 초기화
        self._init_publishers()
        
        # 서브스크라이버 초기화
        self._init_subscribers()
        
        # 상태 관리 변수들
        # self.deliveries: List[Delivery] = [] 에서 : List[Delivery] 는 타입 힌트임.
        # 리스트안에 요소로 Delivery 객체가 들어가야함을 의미함. 사실은 self.deliveries = [] 임
        # delilvery 객체 담을 리스트
        self.deliveries: List[Delivery] = []
        # 현재 목표지점 담는 변수
        self.current_goal = PoseStamped()
        # 현재 위치 담는 변수
        self.current_position: Tuple[float, float, float, float] = (0, 0, 0, 0)
        # 현재 서브 스레드가 execute_route() 실행중인지 아닌지를 저장하는 플래그 변수
        self.executing_route = False
        # 현재 execute_route() 실행하는 서브 스레드가 죽을 타이밍인지 아닌지에 대한 플래그 변수
        self.route_thread_flag = False
        # 인간과의 상호작용 대기 상태를 나타내는 플래그
        self.waiting_for_interaction = False
        # 대기 중에 들어온 새로운 요청을 표시하는 플래그
        self.has_pending_requests = False
        # 오늘의 배송 완료 건수 (누적) 나타내는 변수
        self.today_delivery = 0
        self.event = threading.Event()
        
        # 액션 클라이언트 설정
        self._setup_action_client()
        rospy.loginfo("배송 로봇이 초기화되어 호출을 기다리고 있습니다.")


    #"""퍼블리셔 초기화 메서드"""
    def _init_publishers(self):
        
        try:
            self.pub_goal = rospy.Publisher("/move_base_simple/goal", PoseStamped, queue_size=10)
            self.esp_command_pub = rospy.Publisher("/esp8266_command", String, queue_size=10)
            self.human_to_meet_pub = rospy.Publisher("/human_to_meet", String, latch = True, queue_size=10)
        except Exception as e:
            rospy.logerr(f"퍼블리셔 초기화 실패: {e}")
            raise
    
    #"""서브스크라이버 초기화 메서드"""
    def _init_subscribers(self):
        try:
            self.call_sub = rospy.Subscriber("/call_request", String, 
                                        self.call_request_callback)
            # Replace status subscriber with result subscriber
            self.move_base_result_sub = rospy.Subscriber("/move_base/result", 
                                                        MoveBaseActionResult, 
                                                        self.result_callback)
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
        # 30초안에 액션 서버와 연결안되면 아래 코드 실행
        if not self.move_base_client.wait_for_server(rospy.Duration(30.0)):
            rospy.logerr("이동 베이스 액션 서버를 사용할 수 없습니다! navigation 관련 노드(move_base,,,map,,,등)의 노드를 실행시켰는지 확인하세요!")
            raise RuntimeError("액션 서버 연결 실패!")
        #액션 서버와 정상 연결시 아래 코드 실행
        rospy.loginfo("액션 서버가 준비되었습니다.")

    #"""AMCL로부터 로봇의 현재 위치를 업데이트"""
    def amcl_pose_callback(self, msg: PoseWithCovarianceStamped) -> None:
        
        position = msg.pose.pose.position
        orientation = msg.pose.pose.orientation
        # 로봇의 amcl 기반 현재 위치 저장하는 변수
        self.current_position = (position.x, position.y, orientation.z, orientation.w)
        rospy.logdebug(f"현재 위치가 업데이트되었습니다: {self.current_position}")

    # /call_request 토픽으로 메시지 올때마다 실행되는 콜백함수
    # 웹에서 배달 요청하는 경우 자동으로 이 콜백 실행됨
    def call_request_callback(self, msg: String) -> None:
        """새로운 배송 요청 처리"""
        rospy.loginfo("새로운 배송 요청이 들어왔고, call_request_callback이 호출되었습니다.")
        try:
            data = msg.data.split(",")
            if len(data) != 16:
                rospy.logerr(f"잘못된 배송 정보 형식입니다. {len(data)}개 값이 전달됨, 16개 필요")
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
                    data[7], data[8], recipient_coord, data[13],
                    data[14], data[15]  # 추가된 RFID UID
                )
                self.deliveries.append(new_delivery)
                rospy.loginfo(f"새로운 배송이 추가되었습니다: {new_delivery}")
                
                # 상호작용 대기 중이 아닐 때만 즉시 경로 계산
                if not self.waiting_for_interaction:
                    self.recalculate_route()
                else:
                    self.has_pending_requests = True
                    rospy.loginfo("현재 로봇이 사용자와 gui의 상호작용이 끝날대까지 대기중입니다. 새로운 최적 경로 계산은 상호작용 완료 후 진행됩니다.")
            else:
                rospy.logwarn("최대 배송 수(2개)에 도달했습니다. 배송 요청이 거부되었습니다.")

        except Exception as e:
            rospy.logerr(f"배송 요청 처리 중 오류 발생: {e}")

    #"""현재 위치에서 최적의 배송 순서를 결정하는 메서드"""
    def recalculate_route(self):
        
         
        if not self.deliveries:
            rospy.loginfo("처리할 배송 요청이 없습니다.")
            return
        
        waypoints = []
        for delivery in self.deliveries:
            # delivery 객체의 picked_up 플래그 변수가 True이면 그 delivery 객체의 수령자의 좌표만 담음. 
            # delivery 객체의 picked_up 플래그 변수가 False 이면 그 delivery 객체의 호출자, 수령자의 좌표 모두 담음.
            if not delivery.picked_up:
                # 좌표, 포인트타입, delivery 객체를 지역 변수인 waypoints에 apped함
                waypoints.append((delivery.caller_coord, "caller", delivery))
            waypoints.append((delivery.recipient_coord, "recipient", delivery))
        
        #최솟값을 구해야 하니까 일단 매우 큰 수로 초기화
        min_distance = float('inf')
        best_route = []

        # 가능한 모든 waypoints 내부 요소의 순서에 대한 경우의수(순열,permutation)에 대해 반복문 돌림
        # perm에는 튜플 형태로 경우의수가 저장됨 ex) (A호출자, B수령자, B호출자, A수령자)
        for perm in permutations(waypoints):
            # 수령자 k가 호출자k보다 앞에 있는 경우의수는 전부 continue 써서 걸러냄
            if not self._is_valid_sequence(perm):
                continue
            # 각 perm에 대해서 이동 해야하는 총 거리 저장 (x,y 좌표로만 계산)
            total_distance = self._calculate_route_distance(perm)
            if total_distance < min_distance:
                min_distance = total_distance
                # 모든 perm에 대해 반복문 다 돌리면 지역변수 best_route에는 총 이동거리가 가장 짧은 perm이 저장됨
                best_route = perm
        
        rospy.loginfo(f"최적 경로가 계산되었습니다. 총 거리: {min_distance:.2f}m")
        
        # 서브스레드가 execute_route()를 지금 실행중이라면 액션 서버와 통신하여 기존의 서브스레드에 의한 goal 취소함
        if self.executing_route:
            rospy.loginfo(f"현재 경로를 취소하고, 재계산된 새로운 최적 경로로 변경합니다.현재 남은 배달 건수: {len(self.deliveries)}")
            ##기존의 목표 좌표 취소
            self.move_base_client.cancel_all_goals()
            #서브스레드가 죽을 타이밍이라고 설정
            self.route_thread_flag = True
            self.event.set()
            rospy.loginfo("서브스레드가 정상 종료될때까지 메인스레드가 대기합니다,,,,,")
            #서브스레드가 죽을때까지 메인스레드가 대기
            self.route_thread.join()
        # 서브스레드 만들어서 서브스레드가 execute_route()실행 하도록함
        self.execute_route_in_thread(best_route)

    #"""경로의 유효성(각 순열에 대해 호출자 k가 수령자 k보다 앞에 있는지)을 검증"""
    def _is_valid_sequence(self, route) -> bool:
        
        visited_deliveries = set()
        
        for coord, point_type, delivery in route:
            if point_type == "recipient":
                if delivery.picked_up:
                    if delivery not in visited_deliveries:
                        visited_deliveries.add(delivery)
                elif delivery not in visited_deliveries:
                    return False
            elif point_type == "caller":
                if not delivery.picked_up and delivery not in visited_deliveries:
                    visited_deliveries.add(delivery)
                    
        return True

    #"""주어진 경로의 총 이동 거리를 계산"""
    def _calculate_route_distance(self, route) -> float:
        
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
            
        # Store the thread as an instance attribute
        self.route_thread = threading.Thread(target=self.execute_route, args=(route,))
        self.route_thread.start()
        

    #route 에는 최적 경로로 판단된  perm이 들어감
    def execute_route(self, route: List[Tuple]) -> None:
        """배송 경로 실행"""
        rospy.loginfo("경로 실행 스레드가 시작되었습니다.")
        self.executing_route = True
        try:
            for coord, point_type, delivery in route:
                if self.route_thread_flag:
                    rospy.loginfo("서브스레드가 죽습니다,,,")
                    break

                rospy.loginfo(f"{point_type} 위치로 이동 중: {coord}")
                self.move_command(*coord)
                
                # 현재 이동 중인 특정 배송 정보 저장
                self.current_delivery = delivery
                self.current_point_type = point_type
                
                if point_type == "caller":
                    self.human_to_meet_pub.publish(f"{delivery.caller_id},{point_type},{delivery.caller_rfid_uid}")
                    rospy.loginfo(f"human_to_meet 토픽으로 {delivery.caller_id},{point_type},{delivery.caller_rfid_uid} 보냈습니다" )
                else:  # recipient
                    self.human_to_meet_pub.publish(f"{delivery.recipient_id},{point_type},{delivery.recipient_rfid_uid}")
                    rospy.loginfo(f"human_to_meet 토픽으로 {delivery.recipient_id},{point_type},{delivery.recipient_rfid_uid} 보냈습니다" )
                
                self.event.clear()
                self.event.wait()
            rospy.loginfo("경로 실행 서브스레드가 죽습니다,,,,,,")
                    
        except Exception as e:
            rospy.logerr(f"경로 실행 중 오류 발생: {e}")
        finally:
            self.executing_route = False
            self.route_thread_flag = False

    def move_command(self, pos_x: float, pos_y: float, ori_z: float = 0.0, ori_w: float = 1.0):
        """로봇 이동 명령 전송 (토픽 기반)"""
        goal = PoseStamped()
        goal.header.stamp = rospy.Time.now()
        goal.header.frame_id = 'map'
        goal.pose.position.x = pos_x
        goal.pose.position.y = pos_y
        goal.pose.orientation.z = ori_z
        goal.pose.orientation.w = ori_w
        
        self.pub_goal.publish(goal)
        rospy.loginfo(f"이동 목표가 설정되었습니다: ({pos_x}, {pos_y})")
        rospy.loginfo("로봇이 이동을 시작합니다,,,")

    # 이 콜백은 도착 정보에대한 로그만 남김
    def result_callback(self, result: MoveBaseActionResult) -> None:
        """이동 결과 처리"""
        if result.status.status == actionlib_msgs.msg.GoalStatus.SUCCEEDED:
            rospy.loginfo("목표 지점 도달 성공")
            self.waiting_for_interaction = True
            self.perform_action_at_destination()
        elif result.status.status in [actionlib_msgs.msg.GoalStatus.ABORTED, 
                                    actionlib_msgs.msg.GoalStatus.REJECTED]:
            rospy.logwarn("목표 도달 실패")
            self._handle_goal_aborted()

    
    def _handle_goal_aborted(self) -> None:
        
        retry_count = getattr(self, '_retry_count', 0)
        if retry_count < 10:
            self._retry_count = retry_count + 1
            rospy.logwarn(f"네비게이션 재시도 중 (시도 {self._retry_count}/10)")
            self.move_command(*self.current_goal.pose.position)
        else:
            rospy.logerr("10회 시도 후 네비게이션 실패,,,,,,관리자에게 연락합니다")
            self._retry_count = 0
            

    def is_interacting_with_human_callback(self, msg: String) -> None:
        """사용자 상호작용 완료 처리"""
        if msg.data == "done" and self.waiting_for_interaction:
            # 현재 이동 중이었던 특정 배송 객체로 처리
            if hasattr(self, 'current_delivery'):
                delivery = self.current_delivery
                
                # 호출자와의 상호작용 (물건 픽업)
                if self.current_point_type == "caller" and not delivery.picked_up:
                    rospy.loginfo(f"{delivery.caller_name}님이 로봇에 물건을 성공적으로 적재하였습니다!")
                    delivery.picked_up = True
                
                # 수령자와의 상호작용 (물건 전달)
                elif self.current_point_type == "recipient" and delivery.picked_up:
                    rospy.loginfo(f"{delivery.recipient_name}님이 로봇에 성공적으로 물건을 수령하였습니다!")
                    rospy.loginfo(f"[ID:{delivery.caller_id}] {delivery.caller_dept}부서의 {delivery.caller_name}님에서 "
                                f"[ID:{delivery.recipient_id}] {delivery.recipient_dept}부서의 {delivery.recipient_name}님으로의 "
                                "배송이 성공적으로 완료되었습니다!")
                    self.deliveries.remove(delivery)
                    self.today_delivery += 1
                    rospy.loginfo(f"오늘의 배송 완료 건수: {self.today_delivery}건")

            # 이후 로직은 기존과 동일
            self.waiting_for_interaction = False
            if self.has_pending_requests:
                rospy.loginfo("대기 중 들어온 요청에 대한 경로를 계산합니다.")
                self.recalculate_route()
                self.has_pending_requests = False
            else:
                self.event.set()
        rospy.loginfo("로봇과 사용자의 대면 상호작용이 끝났습니다!")


    def _is_close(self, pos1, pos2, threshold=2):
        """두 점이 가까운지 확인하는 함수"""
        distance = math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
        return distance < threshold

    def perform_action_at_destination(self):
        """목적지 도착 시 수행할 작업"""
        rospy.loginfo("")
        if hasattr(self, 'current_delivery'):
            delivery = self.current_delivery
            if self.current_point_type == "caller" and not delivery.picked_up:
                rospy.loginfo(f"{delivery.caller_name}님의 위치에 도착했습니다. 호출자의 물건 적재를 대기합니다.")
            
            elif self.current_point_type == "recipient" and delivery.picked_up:
                rospy.loginfo(f"{delivery.recipient_name}님의 위치에 도착했습니다. 수령자의 물건 수령을 대기합니다.")
                


    def run(self):
        """메인 실행 루프"""
        rospy.spin()

if __name__ == "__main__":
    try:
        robot = DeliveryRobot()
        robot.run()
    except rospy.ROSInterruptException:
        rospy.loginfo("프로그램이 종료되었습니다.")
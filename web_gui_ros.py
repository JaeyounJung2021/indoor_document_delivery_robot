#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import rospy
from collections import deque
from std_msgs.msg import Int32, Bool, String
import threading
from geometry_msgs.msg import PoseStamped
from move_base_msgs.msg import MoveBaseActionResult
import logging
import time
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'




# 글로벌 변수로 배달 객체 관리
active_deliveries = deque(maxlen=2)  # 최대 2개의 배달만 처리

# SocketIO 객체 생성
socketio = SocketIO(app)

# DB 연결 함수
def get_db_connection():
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'data', 'company.db'))
    conn.row_factory = sqlite3.Row  # 열 이름을 키로 사용하는 딕셔너리 형태로 반환
    return conn

# 기본 경로
@app.route('/')
def home():
    if 'user_id' in session:  # 사용자가 로그인되어 있으면
        return redirect(url_for('dashboard'))  # 대시보드로 리디렉션
    else:
        return redirect(url_for('login'))  # 로그인 페이지로 리디렉션

# 로그인 라우트
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            # DB에서 사용자 확인
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM employees WHERE id = ? AND password = ?', (username, password)).fetchone()
            conn.close()
        except Exception as e:
            logger.error(f"DB connection error: {e}")
            return 'Database connection error', 500

        if user:
            try:
                # 세션에 사용자 ID 저장
                session['user_id'] = user['id']
                logger.info(f"User logged in: {user['id']}")
                return redirect(url_for('dashboard'))  # 대시보드로 리디렉션
            except KeyError as e:
                logger.error(f"Error accessing user data: {e}")
                return 'Error accessing user data', 500
        else:
            logger.warning("Invalid credentials")
            return 'Invalid credentials', 401  # 잘못된 로그인 정보 처리

    return render_template('login.html')

# 대시보드 라우트
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # 세션이 없으면 로그인 페이지로 리디렉션

    # 세션에서 사용자 정보 가져오기
    user_id = session['user_id']
    conn = get_db_connection()

    # 사용자 정보 가져오기
    user = conn.execute('SELECT * FROM employees WHERE id = ?', (user_id,)).fetchone()

    # user가 존재하는지 확인하고, 존재하면 로그로 모든 데이터 출력
    if user:
        # user 객체 로그에 출력
        logger.info("Fetched user data from DB:")
        for column in user.keys():  # user.keys()로 컬럼 이름을 가져옵니다.
            logger.info(f"{column}: {user[column]}")
    else:
        logger.warning("User not found in the database.")

    conn.close()

    return render_template('dashboard.html', user=user)
import logging

# 로그 설정 (파일에 기록하거나 콘솔에 출력할 수 있음)
logging.basicConfig(level=logging.INFO)  # 콘솔에 로그 출력

@app.route('/recipient_info', methods=['GET', 'POST'])
def recipient_info():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        recipient_name = request.form['recipient_name']
        recipient_dept = request.form['recipient_dept']

        conn = get_db_connection()

        # 입력받은 수령자가 employees 테이블에 존재하는지 확인
        recipient = conn.execute(
            'SELECT id FROM employees WHERE name = ? AND department = ?', 
            (recipient_name, recipient_dept)
        ).fetchone()

        if not recipient:
            conn.close()
            return "Recipient not found in database", 404

        # 수령자 ID
        recipient_id = recipient['id']

        # 수령자 좌표 정보 가져오기
        recipient_coord = conn.execute(
            'SELECT pos_x, pos_y, ori_z, ori_w FROM employee_with_coordinates WHERE name = ? AND department = ?', 
            (recipient_name, recipient_dept)
        ).fetchone()

        if not recipient_coord:
            conn.close()
            return "Recipient coordinates not found", 404

        recipient_coord_str = f"{recipient_coord['pos_x']},{recipient_coord['pos_y']},{recipient_coord['ori_z']},{recipient_coord['ori_w']}"

        # DB에서 호출자 정보 가져오기
        user_id = session['user_id']
        user = conn.execute('SELECT name, department FROM employees WHERE id = ?', (user_id,)).fetchone()

        if not user:
            conn.close()
            return "Caller not found in database", 404

        # 호출자 부서 좌표 가져오기
        caller_dept_info = conn.execute(
            'SELECT pos_x, pos_y, ori_z, ori_w FROM departments WHERE department = ?', 
            (user['department'],)
        ).fetchone()
        conn.close()

        if not caller_dept_info:
            return "Caller department not found", 404

        caller_coord = f"{caller_dept_info['pos_x']},{caller_dept_info['pos_y']},{caller_dept_info['ori_z']},{caller_dept_info['ori_w']}"

        # Delivery 객체 정보 생성
        delivery_info = f"{user['name']},{user['department']},{caller_coord},{user_id},{recipient_name},{recipient_dept},{recipient_coord_str},{recipient_id}"

        # 로그로 delivery_info 출력
        logging.info(f"Delivery Information: {delivery_info}")

        # 배달 요청을 active_deliveries에 추가
        active_deliveries.append(delivery_info)

        # ROS 토픽으로 수령자 정보 발행
        rospy.Publisher("/call_request", String, queue_size=10).publish(delivery_info)
        rospy.loginfo("sent message to /call_request Topic")
        return redirect(url_for('dashboard'))
    
    return render_template('recipient_info.html')

# 주행 노드에서 배달 완료 메시지를 받을 때
@socketio.on('delivery_complete')
def handle_delivery_complete(data):
    delivery_info = data.get('delivery_info')
    if delivery_info in active_deliveries:
        active_deliveries.remove(delivery_info)  # 배달이 끝났으므로 목록에서 제거
        emit('update_status', {'status': 'A delivery has been completed.'})

# 로봇 이동 현황 페이지
@app.route('/delivery_status')
def delivery_status():
    return render_template('delivery_status.html')

# 호출자 도착 알림 페이지
@app.route('/arrival')
def arrival():
    return render_template('arrival.html')

# 수령자 도착 알림 페이지
@app.route('/recipient_arrival')
def recipient_arrival():
    return render_template('recipient_arrival.html')

# 웹소켓을 이용한 실시간 알림 (예: 로봇 도착 알림)
@socketio.on('connect')
def handle_connect():
    print("Client connected.")

@socketio.on('robot_arrived')
def handle_robot_arrival(data):
    emit('robot_arrival', {'status': 'Robot has arrived at the destination.'})

# ROS spin을 위한 별도 스레드 함수
def ros_spin():
    rospy.spin()  # spin을 통해 ROS 메시지 처리 대기

# GUI 관련 작업을 위한 별도 스레드 함수 (예시로 time.sleep을 사용)
def run_gui():
    while True:
        time.sleep(1)
        print("Running GUI thread...")  # GUI 관련 코드로 대체

# Flask 서버 실행을 위한 별도 스레드 함수
def run_flask():
    socketio.run(app, debug=True, use_reloader=False)  # use_reloader=False는 Flask가 중복으로 실행되지 않도록 방지

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # 메인 스레드에서 rospy 노드 초기화
    rospy.init_node('robot_web_server_node', anonymous=True)  # 노드 초기화

    # 로깅 재설정 (ROS 노드가 로깅을 덮어쓰는 문제 해결하기위해)
    logger.handlers = []  # 기존 핸들러 제거
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    

    # 3개의 스레드 생성
    flask_thread = threading.Thread(target=run_flask)
    ros_thread = threading.Thread(target=ros_spin)
    gui_thread = threading.Thread(target=run_gui)

    # 스레드 시작
    logger.info("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!Flask web 서버가 실행됩니다!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!") 
    flask_thread.start()
    ros_thread.start()
    gui_thread.start()

    # 스레드가 종료될 때까지 대기
    flask_thread.join()
    ros_thread.join()
    gui_thread.join()

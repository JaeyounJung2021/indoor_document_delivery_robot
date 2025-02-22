#include <ESP8266WiFi.h>
#include <ros.h>
#include <SPI.h>              // SPI 라이브러리 추가
#include <std_msgs/String.h>
#include <MFRC522.h>
#include <Adafruit_NeoPixel.h>

// 핀 설정
#define NEO_PIXEL_PIN D4
#define LINEAR_IN1 D5
#define LINEAR_IN2 D6
#define RFID_SS_PIN D8
#define RFID_RST_PIN D0

// 상수 정의
#define NEO_PIXEL_COUNT 8
#define RFID_TIMEOUT 10000  // 10초

// 전역 변수
Adafruit_NeoPixel strip(NEO_PIXEL_COUNT, NEO_PIXEL_PIN, NEO_GRB + NEO_KHZ800);
MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);
String currentUID = "";
bool isCallerMode = false;
bool isLocked = true;

// ROS 노드 핸들러
ros::NodeHandle nh;
std_msgs::String rfid_result_msg;
ros::Publisher rfid_result_pub("/rfid_auth_result", &rfid_result_msg);

void humanToMeetCallback(const std_msgs::String& msg) {
    String data = msg.data;
    int firstComma = data.indexOf(',');
    int secondComma = data.indexOf(',', firstComma + 1);
    
    // 형식: "id,point_type,uid"
    String userId = data.substring(0, firstComma);                     // ex: "user1"
    String pointType = data.substring(firstComma + 1, secondComma);   // ex: "caller"
    currentUID = data.substring(secondComma + 1);                     // ex: "1A 1A 1A 1A"
    
    setStripColor(0, 0, 255);  // 이동중에는 LED 파란색으로 설정 

    // 디버깅을 위한 시리얼 출력 (선택사항)
    Serial.println("User ID: " + userId);
    Serial.println("Point Type: " + pointType);
    Serial.println("UID: " + currentUID);
}

void isInteractingCallback(const std_msgs::String& msg) {
    if(String(msg.data) == "done") {
        setStripColor(0, 0, 255);  // LED 파란색으로 설정 
    }
}

void loginResultCallback(const std_msgs::String& msg) {
    if(String(msg.data) == "succeeded") {
        unlockDrawer();
    }
}

void rfidAuthRequestCallback(const std_msgs::String& msg) {
    if(String(msg.data) == "RequestArrived") {
        // RFID 인증 처리 시작
        unsigned long startTime = millis();
        bool authSuccess = false;
        
        // 10초 동안 RFID 태그 읽기 시도
        while(millis() - startTime < RFID_TIMEOUT) {
            if(rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
                String scannedUID = "";
                for(byte i = 0; i < rfid.uid.size; i++) {
                    scannedUID += String(rfid.uid.uidByte[i], HEX);
                }
                
                // UID 일치 여부 확인
                if(scannedUID == currentUID) {
                    rfid_result_msg.data = "succeeded";
                    rfid_result_pub.publish(&rfid_result_msg);
                    authSuccess = true;
                    break;
                }
            }
            delay(100);  // CPU 부하 감소를 위한 짧은 대기
        }
        
        // 10초 동안 인증 실패하거나 불일치한 경우
        if(!authSuccess) {
            rfid_result_msg.data = "failed";
            // 빨간색 표시하기
            setStripColor(255, 0, 0);
            rfid_result_pub.publish(&rfid_result_msg);
        }
    }
}

// ROS 서브스크라이버 설정
ros::Subscriber<std_msgs::String> human_sub("/human_to_meet", humanToMeetCallback);
ros::Subscriber<std_msgs::String> interact_sub("/is_interacting_with_human", isInteractingCallback);
ros::Subscriber<std_msgs::String> login_sub("/gui_login_result", loginResultCallback);
ros::Subscriber<std_msgs::String> rfid_request_sub("/rfid_auth_request", rfidAuthRequestCallback);

void setup() {
    // 핀 모드 설정
    pinMode(LINEAR_IN1, OUTPUT);
    pinMode(LINEAR_IN2, OUTPUT);
    
    // 초기화
    strip.begin();
    setStripColor(0, 255, 0);  // 초기 LED 색상: 초록색
    SPI.begin();
    rfid.PCD_Init();
    
    // ROS 노드 초기화
    nh.initNode();
    nh.advertise(rfid_result_pub);
    nh.subscribe(human_sub);
    nh.subscribe(interact_sub);
    nh.subscribe(login_sub);
    nh.subscribe(rfid_request_sub);
}

void loop() {
    nh.spinOnce();
    delay(10);
}

// 유틸리티 함수들
void setStripColor(uint8_t r, uint8_t g, uint8_t b) {
    for(int i = 0; i < NEO_PIXEL_COUNT; i++) {
        strip.setPixelColor(i, strip.Color(r, g, b));
    }
    strip.show();
}

void unlockDrawer() {
    digitalWrite(LINEAR_IN1, HIGH);
    digitalWrite(LINEAR_IN2, LOW);
    isLocked = false;
}

void lockDrawer() {
    digitalWrite(LINEAR_IN1, LOW);
    digitalWrite(LINEAR_IN2, HIGH);
    isLocked = true;
}
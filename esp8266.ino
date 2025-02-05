//필요 라이브러리명 : Adafruit NeoPixel , MFRC522, rosserial_arduino, rosserial
//rosserial_arduino 패키지 설치후 추가 설정 필요. (ROS에 rosserial 설치.. 아마 되어있을듯)
//아두이노 ide에 rosserial 설치
//rosrun rosserial_python serial_node.py _port:=/dev/아두이노가연결된포트 _baud:=57600
//아두이노 항상 같은 자리에 꼽자!!! 아니면 그거 고정 등록 해주던지!
#include <Adafruit_NeoPixel.h>
#include <MFRC522.h>
#include <ros.h>
#include <std_msgs/String.h>
#include <std_msgs/Bool.h>
#include <Wire.h>
#include <SPI.h>
// ROS 노드 객체
ros::NodeHandle nh;

// RFID 값 전역 변수
byte expectedUID[4];  // ROS에서 받은 RFID 값 저장

//human_to_meet 전역변수
std::string user_to_meet;
std::string user_role_to_meet;

// 네오픽셀 설정
const int NEOPIXEL_PIN = D8;
const int NUM_PIXELS = 12;
Adafruit_NeoPixel strip(NUM_PIXELS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

// RFID 설정
#define RFID_SDA_PIN D2
#define RFID_RST_PIN D3
MFRC522 rfid(RFID_SDA_PIN, RFID_RST_PIN);

// 특정 색으로 모든 네오픽셀 설정
void setAllPixels(uint8_t red, uint8_t green, uint8_t blue) {
  for (int i = 0; i < NUM_PIXELS; i++) {
    strip.setPixelColor(i, strip.Color(red, green, blue));
  }
  strip.show();
}

// 초록색 LED 켜기
void Green_LED_ON() {
  setAllPixels(0, 255, 0);
  Serial.println("초록 LED가 켜졌습니다.");
}

// 빨간색 LED 켜기
void RED_LED_ON() {
  setAllPixels(255, 0, 0);
  Serial.println("빨간 LED가 켜졌습니다.");
}

// 리니어 액추에이터 제어 함수 (추후 구현 필요)
void Linear_LOCK_OFF() {
  Serial.println("리니어 액추에이터 잠금 해제");
}

void Linear_LOCK_ON() {
  Serial.println("리니어 액추에이터 잠금");
}

// RFID 카드 UID 체크 함수
bool checkRFIDCardUID() {
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    if (rfid.uid.size != sizeof(expectedUID)) {
      return false;
    }
    for (byte i = 0; i < rfid.uid.size; i++) {
      if (rfid.uid.uidByte[i] != expectedUID[i]) {
        return false;
      }
    }
    rfid.PICC_HaltA();
    return true;
  }
  return false;
}

// ROS에서 받은 RFID 문자열을 바이트 배열로 변환하는 함수
void parseRFIDStringToBytes(const String& rfidStr, byte* uidArray, int size) {
    int index = 0;
    char* token;
    char* rfidStrCopy = strdup(rfidStr.c_str());  // 원본 데이터 유지
    token = strtok(rfidStrCopy, ",");
    while (token != NULL && index < size) {
        uidArray[index++] = strtol(token, NULL, 16);
        token = strtok(NULL, ",");
    }
    free(rfidStrCopy);
}

// 인증 로직 실행 후 ROS에 결과 전송
void rfidAuth_and_LED_LINEAR_CONTROL_Callback(const std_msgs::String &msg) {
  String received_rfid = msg.data.c_str();
  nh.loginfo("[ESP8266] RFID 인증요청 수신, 10초간 태그 대기 ...");

  parseRFIDStringToBytes(received_rfid, expectedUID, sizeof(expectedUID));

  unsigned long startTime = millis();
  unsigned long timeout = 10000;
  bool auth_success = false;

  while (millis() - startTime < timeout) {
    if (checkRFIDCardUID()) {
      nh.loginfo("[ESP8266] RFID 태그 감지됨!");
      auth_success = true;
      break;
    }
    delay(100);
  }

  std_msgs::String success_msg;
  if (auth_success) {
      nh.loginfo("[ESP8266] RFID 인증 성공! LED 및 액추에이터 동작");
      Green_LED_ON();
      Linear_LOCK_OFF();
      success_msg.data = "rfid_auth_ok";
  } else {
      nh.loginfo("[ESP8266] RFID 인증 실패");
      RED_LED_ON();
      success_msg.data = "rfid_auth_no";
  }
  rfidAuthSuccessPub.publish(&success_msg);
}

// 적재/수령 완료 요청 콜백
void lock_and_LED_Callback(const std_msgs::String &msg) {
    if (user_role_to_meet == "caller") {
        nh.loginfo("[ESP8266] 적재 완료 요청 수신 - 잠금 및 LED 빨강(점유상태)!");
        RED_LED_ON();
    } else {
        nh.loginfo("[ESP8266] 픽업 완료 요청 수신 - 잠금 및 LED 초록(비점유상태)");
        Green_LED_ON();
    }
    Linear_LOCK_ON();
}

// 문자열 분리 함수
void splitString(const std::string& str, std::string& first, std::string& second, const char delimiter) {
  size_t delimiterPosition = str.find(delimiter);
  if (delimiterPosition != std::string::npos) {
    first = str.substr(0, delimiterPosition);
    second = str.substr(delimiterPosition + 1);
  }
}

//human_to_meet(이번턴에 만날사람) 정보 기억
void human_to_meet_memory(const std_msgs::String &msg) {
  splitString(msg.data, user_to_meet, user_role_to_meet, ',');
}

// ROS 퍼블리셔 및 서브스크라이버 설정
ros::Subscriber<std_msgs::String> rfidAuthSub("/rfid_auth_request", rfidAuth_and_LED_LINEAR_CONTROL_Callback);
ros::Publisher rfidAuthSuccessPub("/rfid_auth_success", &std_msgs::String);
ros::Subscriber<std_msgs::String> lockLEDControlSub("/is_interacting_with_human_done", lock_and_LED_Callback);
ros::Subscriber<std_msgs::String> HumanToMeetSub("/human_to_meet", &human_to_meet_memory);

void setup() {
  Serial.begin(115200);
  nh.initNode();
  
  // ROS 퍼블리셔, 섭스크라이버 등록
  nh.advertise(rfidAuthSuccessPub);
  nh.subscribe(rfidAuthSub);
  nh.subscribe(lockLEDControlSub);
  nh.subscribe(HumanToMeetSub);

  // 네오픽셀 초기화
  strip.begin();
  strip.show();
  setAllPixels(0, 0, 0);

  // RFID 초기화
  SPI.begin();
  rfid.PCD_Init();
}

void loop() {
  nh.spinOnce();
  delay(100);
}

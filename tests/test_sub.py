import zmq
import sys
import os
import cv2
import numpy as np

# 프로젝트 경로 추가 (로컬 모듈 임포트를 위함)
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

def main():
    # ZMQ 통신 세팅
    context = zmq.Context()
    socket = context.socket(zmq.SUB)

    # Frame 데이터를 받기 위한 포트
    socket.connect("tcp://127.0.0.1:5555")
    
    # Odom 데이터를 받기 위한 포트 (Config 반영)
    socket.connect("tcp://127.0.0.1:5557")

    socket.setsockopt(zmq.SUBSCRIBE, b"")

    print("🟢 [Subscriber] Connected to 5555(Frame) and 5557(Odom). Waiting...\n")
    
    window_name = "Aria Stream Viewer"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # Odom 데이터를 화면에 띄우기 위해 저장할 변수 초기화
    latest_odom_text = "Odom: Waiting..."
    
    try:
        while True:
            msg = socket.recv_pyobj()
            msg_type = type(msg).__name__
            
            # --- 1. Odom 메시지가 들어온 경우 위치 정보 업데이트 ---
            if msg_type == "OdomMsg":
                try:
                    # T_world_device 4x4 행렬에서 병진(Translation) 위치인 x, y, z 값만 추출합니다.
                    tx, ty, tz = msg.T_world_device[:3, 3]
                    latest_odom_text = f"Odom [X:{tx:.2f}, Y:{ty:.2f}, Z:{tz:.2f}]"
                except Exception:
                    latest_odom_text = "Odom: Matrix parse error"

            # --- 2. Frame 메시지가 들어온 경우 이미지에 텍스트 합성 후 출력 ---
            elif msg_type == "FrameMsg":
                if msg.image is not None:
                    display_img = msg.image.copy()
                    
                    if len(display_img.shape) == 3 and display_img.shape[2] == 3:
                        display_img = cv2.cvtColor(display_img, cv2.COLOR_RGB2BGR)
                    
                    text_seq = f"Seq: {msg.seq}"
                    text_time = f"Time: {msg.device_time_ns} ns"
                    
                    # 텍스트 합성 (Seq, Timestamp, Odom)
                    cv2.putText(display_img, text_seq, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                    cv2.putText(display_img, text_time, (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                    
                    # Odom 정보는 눈에 잘 띄게 노란색(0, 255, 255)으로 약간 아래쪽에 추가
                    cv2.putText(display_img, latest_odom_text, (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                    
                    cv2.imshow(window_name, display_img)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("🔴 [Subscriber] 'q' 키를 눌러 뷰어를 종료합니다.")
                        break
                        
            elif msg_type == "ControlMsg":
                if msg.command in ["EOS", "STOP"]:
                    print("\n🔴 [Subscriber] Stopping as requested by Publisher.")
                    break
                    
    except KeyboardInterrupt:
        print("\n🔴 [Subscriber] Stopped by user (Ctrl+C).")
    finally:
        socket.close()
        context.term()
        cv2.destroyAllWindows()
        print("🟢 [Subscriber] Cleaned up and exited.")

if __name__ == "__main__":
    main()
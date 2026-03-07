import os
import sys

# 프로젝트 루트를 PATH에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from aria_stream_replay.dataio.vrs_reader import VrsReader
from aria_stream_replay.core.replay_clock import ReplayClock
from aria_stream_replay.transport.zmq_pub import ZmqPublisher
from aria_stream_replay.event_types import FrameMsg, ControlMsg

def main():
    # 1. 파일 경로 설정 (유저 데이터 기준)
    vrs_path = os.path.expanduser("~/Desktop/26-1_RPL/CustomData/Aria_recordings/301_1253/301_1253.vrs")
    
    # 2. 모듈 초기화
    reader = VrsReader(vrs_path)
    clock = ReplayClock(speed_factor=1.0) # 1.0 = 실시간, 2.0 = 2배속
    publisher = ZmqPublisher(port=5555)
    
    print("Starting Replay Pipeline...")
    seq = 0
    
    try:
        while True:
            # DataSource에서 데이터 읽기
            ts_ns, image = reader.next_frame()
            if image is None:
                print("End of VRS stream.")
                publisher.send_control(ControlMsg(command="EOS"))
                break
                
            # ReplayClock으로 시간 동기화 (원래 FPS 모방)
            clock.wait_until(ts_ns)
            
            # 메시지 패키징 및 ZMQ 전송
            msg = FrameMsg(
                seq=seq,
                sensor_name="rgb",
                device_time_ns=ts_ns,
                image=image
            )
            publisher.send_frame(msg)
            
            seq += 1
            if seq % 30 == 0: # 30프레임마다 로그 출력
                print(f"Published Frame {seq} | Timestamp: {ts_ns}")
                
    except KeyboardInterrupt:
        print("Replay stopped by user.")
        publisher.send_control(ControlMsg(command="STOP"))

if __name__ == "__main__":
    main()
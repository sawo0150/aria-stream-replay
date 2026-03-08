import os
import sys
import hydra
from omegaconf import DictConfig, OmegaConf

# 프로젝트 루트를 PATH에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from aria_stream_replay.dataio.vrs_reader import VrsReader
from aria_stream_replay.dataio.mps_reader import MpsReader
from aria_stream_replay.core.replay_clock import ReplayClock
from aria_stream_replay.transport.zmq_pub import ZmqPublisher
from aria_stream_replay.event_types import FrameMsg, OdomMsg, ControlMsg

@hydra.main(version_base=None, config_path="../../conf", config_name="config")
def main(cfg: DictConfig):
    # 현재 로드된 설정 확인용 출력
    print(OmegaConf.to_yaml(cfg))

    # 1. 파일 경로 설정 (Hydra Config 사용)
    vrs_path = os.path.expanduser(cfg.source.vrs_path)
    
    # 2. 모듈 초기화 (Hydra Config 사용)
    reader = VrsReader(vrs_path)  
    mps_reader = None
    if cfg.replay.use_odom:
        mps_dir = os.path.expanduser(cfg.source.mps_path)
        mps_reader = MpsReader(mps_dir=mps_dir, odom_source=cfg.replay.odom_source)

    clock = ReplayClock(speed_factor=cfg.replay.rate) 
    publisher = ZmqPublisher(frame_endpoint=cfg.transport.frame_endpoint, 
                             odom_endpoint=cfg.transport.odom_endpoint)
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
            # 4. Odom이 활성화되어 있다면, 현재 이미지 시간과 가장 가까운 Odom을 쏴줍니다.
            if cfg.replay.use_odom and mps_reader is not None:
                T_wd = mps_reader.get_nearest_pose(ts_ns)
                odom_msg = OdomMsg(
                    seq=seq,
                    device_time_ns=ts_ns,
                    T_world_device=T_wd,
                    source=cfg.replay.odom_source
                )
                publisher.send_odom(odom_msg)

            seq += 1
            if seq % 30 == 0: # 30프레임마다 로그 출력
                print(f"Published Frame {seq} | Timestamp: {ts_ns}")
                
    except KeyboardInterrupt:
        print("Replay stopped by user.")
        publisher.send_control(ControlMsg(command="STOP"))

if __name__ == "__main__":
    # 이 스크립트가 실행될 때 hydra가 가로채서 cfg를 넣어줍니다.
    main()
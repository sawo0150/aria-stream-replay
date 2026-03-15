from dataclasses import dataclass
import numpy as np
from typing import Optional

@dataclass
class FrameMsg:
    seq: int
    sensor_name: str  # 'rgb', 'slam_left', 'slam_right'
    device_time_ns: int
    image: np.ndarray  # 이미지 배열
    exposure: Optional[float] = None
    gain: Optional[float] = None

@dataclass
class OdomMsg:
    seq: int
    device_time_ns: int
    T_world_device: np.ndarray  # 4x4 행렬
    source: str  # 'open_loop', 'closed_loop', 'live'

@dataclass
class ControlMsg:
    command: str  # 'START', 'STOP', 'PAUSE', 'EOS'

@dataclass
class BundleMsg:
    """
    Frame를 기준(anchor)으로 필요한 부가정보(현재는 odom)를 함께 담아 보내는 메시지.
    backend는 이 BundleMsg 하나만 받아서 처리하면 됨.
    """
    frame: FrameMsg
    odom: Optional[OdomMsg] = None
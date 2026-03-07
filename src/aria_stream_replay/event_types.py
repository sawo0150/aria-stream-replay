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
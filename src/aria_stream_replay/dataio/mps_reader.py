import os
import bisect
import numpy as np
from projectaria_tools.core.mps import read_open_loop_trajectory, read_closed_loop_trajectory

class MpsReader:
    def __init__(self, mps_dir: str, odom_source: str = "open_loop"):
        self.odom_source = odom_source
        
        # 1. 설정에 따라 다른 CSV 파일을 로드합니다.
        if odom_source == "open_loop":
            path = os.path.join(mps_dir, "slam", "open_loop_trajectory.csv")
            self.traj = read_open_loop_trajectory(path)
        elif odom_source == "closed_loop":
            path = os.path.join(mps_dir, "slam", "closed_loop_trajectory.csv")
            self.traj = read_closed_loop_trajectory(path)
        else:
            raise ValueError("odom_source must be 'open_loop' or 'closed_loop'")

        # 2. 이진 탐색(Binary Search)을 위해 타임스탬프만 따로 뽑아서 배열로 만듭니다.
        # tracking_timestamp는 초 단위이므로 ns로 변환합니다.
        self.timestamps_ns = [p.tracking_timestamp.total_seconds() * 1e9 for p in self.traj]
        
        # 3. 4x4 변환 행렬을 미리 추출합니다. 
        # (Open Loop는 Odometry 좌표계, Closed Loop는 World 좌표계 사용)
        if odom_source == "open_loop":
            self.poses = [p.transform_odometry_device.to_matrix() for p in self.traj]
        else:
            self.poses = [p.transform_world_device.to_matrix() for p in self.traj]
        print(f"[MpsReader] Loaded {len(self.traj)} poses from {odom_source}")

    def get_nearest_pose(self, query_ts_ns: float) -> np.ndarray:
        """
        주어진 시간(ns)과 가장 가까운 Odom Pose를 반환합니다.
        """
        # 이진 탐색으로 들어갈 위치(인덱스)를 찾습니다.
        idx = bisect.bisect_left(self.timestamps_ns, query_ts_ns)
        
        if idx == 0:
            return self.poses[0]
        if idx == len(self.timestamps_ns):
            return self.poses[-1]
        
        # 앞, 뒤 인덱스 중 시간차가 더 적은(가까운) 포즈를 선택합니다.
        before_time = self.timestamps_ns[idx - 1]
        after_time = self.timestamps_ns[idx]
        
        if (query_ts_ns - before_time) < (after_time - query_ts_ns):
            return self.poses[idx - 1]
        else:
            return self.poses[idx]
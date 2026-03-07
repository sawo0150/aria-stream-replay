import numpy as np

class FrustumCuller:
    def __init__(self, w: int, h: int, fx: float, fy: float, cx: float, cy: float, min_depth: float = 0.1, max_depth: float = 10.0):
        """
        카메라 Intrinsics와 이미지 해상도를 초기화합니다.
        """
        self.w = w
        self.h = h
        self.K = np.array([
            [fx, 0, cx],
            [0, fy, cy],
            [0,  0,  1]
        ])
        self.min_depth = min_depth
        self.max_depth = max_depth

    def cull(self, points_world: np.ndarray, T_wc: np.ndarray) -> np.ndarray:
        """
        points_world: (N, 3) numpy array (Global Point Cloud)
        T_wc: (4, 4) numpy array (World to Camera transform)
        반환값: (M, 3) Frustum 내부에 있는 필터링된 Point Cloud
        """
        if len(points_world) == 0:
            return points_world

        # 1. World -> Camera 좌표계 변환
        T_cw = np.linalg.inv(T_wc)
        
        # Nx3을 Nx4(동차좌표)로 변환
        ones = np.ones((points_world.shape[0], 1))
        pts_w_homo = np.hstack([points_world, ones])
        
        # 행렬 곱셈: (4x4) x (4xN) -> (4xN) -> Transpose해서 (Nx4)
        pts_c_homo = (T_cw @ pts_w_homo.T).T
        pts_c = pts_c_homo[:, :3]

        # 2. Depth(Z축) 필터링 (너무 가깝거나 너무 먼 점 제거)
        Z_c = pts_c[:, 2]
        depth_mask = (Z_c > self.min_depth) & (Z_c < self.max_depth)
        
        pts_c_filtered = pts_c[depth_mask]
        pts_w_filtered = points_world[depth_mask]

        if len(pts_c_filtered) == 0:
            return np.empty((0, 3))

        # 3. 2D 픽셀 투영 (Projection)
        # (3x3) x (3xM) -> (3xM) -> Transpose해서 (Mx3)
        uv_homo = (self.K @ pts_c_filtered.T).T
        
        u = uv_homo[:, 0] / uv_homo[:, 2]
        v = uv_homo[:, 1] / uv_homo[:, 2]

        # 4. 이미지 해상도 바운딩 박스 필터링
        fov_mask = (u >= 0) & (u <= self.w) & (v >= 0) & (v <= self.h)

        # 최종적으로 살아남은 World 좌표계 점들 반환
        return pts_w_filtered[fov_mask]
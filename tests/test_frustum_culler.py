import os
import numpy as np
import open3d as o3d
from projectaria_tools.core.mps import read_global_point_cloud, read_closed_loop_trajectory

# sys path 추가는 테스트 실행을 위해 임시로 넣습니다 (모듈 인식용)
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
from aria_stream_replay.core.frustum_culler import FrustumCuller

def main():
    # 1. 데이터 경로 설정 (유저 환경에 맞춤)
    base_dir = os.path.expanduser("~/Desktop/26-1_RPL/CustomData/Aria_recordings/301_1253")
    ply_path = os.path.join(base_dir, "mps_301_1253_vrs/slam/semidense_points.csv.gz")
    traj_path = os.path.join(base_dir, "mps_301_1253_vrs/slam/closed_loop_trajectory.csv")

    print(f"Loading Global Point Cloud... {ply_path}")
    global_pc = read_global_point_cloud(ply_path)
    # projectaria_tools의 point cloud를 numpy (N, 3)으로 변환
    points_3d = np.array([p.position_world for p in global_pc])
    print(f"Loaded {len(points_3d)} points.")

    print(f"Loading Trajectory... {traj_path}")
    trajectory = read_closed_loop_trajectory(traj_path)
    print(f"Loaded {len(trajectory)} poses.")

    # 중간쯤에 있는 Pose 하나를 샘플로 선택
    sample_pose = trajectory[len(trajectory) // 2]
    T_wd = sample_pose.transform_world_device.to_matrix() # World to Device 행렬 (4x4)
    print(f"Selected Timestamp: {sample_pose.tracking_timestamp.total_seconds()}s")

    # 2. Culler 초기화 (Aria RGB 카메라의 대략적인 근사값 사용 - 실제 개발시 calibration 파일에서 파싱 필요)
    # 해상도 1408x1408, 대략적인 초점거리 적용
    culler = FrustumCuller(w=1408, h=1408, fx=600.0, fy=600.0, cx=704.0, cy=704.0)

    # 3. Frustum Culling 실행
    print("Running Frustum Culling...")
    culled_points = culler.cull(points_3d, T_wc=T_wd)
    print(f"Points remaining after culling: {len(culled_points)}")

    # 4. Open3D 시각화
    # 전체 맵 (회색)
    pcd_global = o3d.geometry.PointCloud()
    pcd_global.points = o3d.utility.Vector3dVector(points_3d)
    pcd_global.paint_uniform_color([0.8, 0.8, 0.8]) 

    # 잘려진 맵 (빨간색)
    pcd_culled = o3d.geometry.PointCloud()
    pcd_culled.points = o3d.utility.Vector3dVector(culled_points)
    pcd_culled.paint_uniform_color([1.0, 0.0, 0.0])

    print("Opening Open3D Viewer. Close the window to exit.")
    # 잘려진 부분이 돋보이게 렌더링
    o3d.visualization.draw_geometries([pcd_global, pcd_culled], window_name="Frustum Culling Test")

if __name__ == "__main__":
    main()
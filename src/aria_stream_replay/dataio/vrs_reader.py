# dataio/vrs_reader.py

import os
import cv2
import numpy as np
from projectaria_tools.core import calibration

from projectaria_tools.core.data_provider import create_vrs_data_provider

class VrsReader:
    STREAM_LABEL_MAP = {
        "rgb": "camera-rgb",
        "slam_left": "camera-slam-left",
        "slam_right": "camera-slam-right",
    }

    def __init__(self, vrs_path: str, camera_stream: str = "rgb", rectify_cfg=None, calibration_path=None):

        if not os.path.exists(vrs_path):
            raise FileNotFoundError(f"VRS file not found: {vrs_path}")
        
        self.provider = create_vrs_data_provider(vrs_path)
        if not self.provider:
            raise RuntimeError("Failed to open VRS file.")
            
        # 외부 calibration_path는 현재 버전에서는 사용하지 않음
        # (VRS 내부 calibration 사용)
        self.calibration_path = calibration_path

        # 사용자가 지정한 stream 이름을 Aria camera label로 변환
        self.camera_stream = camera_stream
        self.camera_label = self.STREAM_LABEL_MAP.get(camera_stream, camera_stream)

        # 카메라 스트림 ID 찾기
        self.stream_id = self.provider.get_stream_id_from_label(self.camera_label)
        if not self.stream_id:
            raise ValueError(f"Camera stream not found in this VRS file: {self.camera_label}")

        # VRS 내부 device calibration에서 해당 카메라 calibration 로드
        self.device_calib = self.provider.get_device_calibration()
        self.src_calib = self.device_calib.get_camera_calib(self.camera_label)
        if self.src_calib is None:
            raise RuntimeError(f"Failed to load camera calibration for: {self.camera_label}")

        # Rectification 설정 파싱
        self.rectify_enabled = bool(rectify_cfg.enabled) if rectify_cfg is not None else False
        self.rotate_cw90 = bool(rectify_cfg.rotate_cw90) if rectify_cfg is not None else False
        self.save_debug_pair_once = bool(rectify_cfg.save_debug_pair_once) if rectify_cfg is not None else False
        self.debug_dir = str(rectify_cfg.debug_dir) if rectify_cfg is not None else "./debug_rectify"
        self._saved_debug = False

        # downstream에 내보낼 최종 센서 이름
        self.output_sensor_name = f"{self.camera_stream}_pinhole" if self.rectify_enabled else self.camera_stream

        # 기본 출력 calibration 정보
        self.output_width = None
        self.output_height = None
        self.output_fx = None
        self.output_fy = None
        self.output_cx = None
        self.output_cy = None

        # rectify용 target pinhole calibration
        self.rectify_target_calib = None

        if self.rectify_enabled:
            out_w = int(rectify_cfg.width)
            out_h = int(rectify_cfg.height)
            focal_px = float(rectify_cfg.focal_px)

            # 공식 문서 패턴:
            # get_linear_camera_calibration(width, height, focal, camera_label, T_device_camera)
            self.rectify_target_calib = calibration.get_linear_camera_calibration(
                out_w,
                out_h,
                focal_px,
                self.camera_label,
                self.src_calib.get_transform_device_camera(),
            )

            # downstream YAML에 복사하기 쉽게 출력 intrinsics를 별도 저장
            # 여기서는 구현 단순화를 위해 principal point를 이미지 중심으로 둠
            self.output_width = out_w
            self.output_height = out_h
            self.output_fx = focal_px
            self.output_fy = focal_px
            self.output_cx = out_w / 2.0
            self.output_cy = out_h / 2.0

            # 회전 시 최종 출력 크기와 principal point도 같이 갱신
            if self.rotate_cw90:
                self.output_width, self.output_height = out_h, out_w
                self.output_cx = self.output_width / 2.0
                self.output_cy = self.output_height / 2.0
        else:
            # raw mode일 때는 source calibration 값을 직접 downstream으로 넘기기 어렵기 때문에
            # 최소한 현재 image shape 기준 값은 first frame에서 채움
            self.output_width = None
            self.output_height = None
            self.output_fx = None
            self.output_fy = None
            self.output_cx = None
            self.output_cy = None

        # 전체 데이터(프레임) 개수를 가져오고 현재 읽을 인덱스를 0으로 초기화
        self.num_frames = self.provider.get_num_data(self.stream_id)

        self.current_index = 0
        
    def _save_debug_images_once(self, raw_rgb: np.ndarray, out_rgb: np.ndarray):
        if not self.save_debug_pair_once or self._saved_debug:
            return

        os.makedirs(self.debug_dir, exist_ok=True)

        raw_bgr = cv2.cvtColor(raw_rgb, cv2.COLOR_RGB2BGR)
        out_bgr = cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)

        cv2.imwrite(os.path.join(self.debug_dir, "raw_first.png"), raw_bgr)
        cv2.imwrite(os.path.join(self.debug_dir, "rectified_first.png"), out_bgr)
        self._saved_debug = True

    def get_output_sensor_name(self):
        return self.output_sensor_name

    def get_output_calibration(self):
        return {
            "width": self.output_width,
            "height": self.output_height,
            "fx": self.output_fx,
            "fy": self.output_fy,
            "cx": self.output_cx,
            "cy": self.output_cy,
        }

    def next_frame(self):
        """다음 프레임의 Timestamp(ns)와 이미지 배열을 반환합니다."""
        # 모든 프레임을 다 읽었다면 None 반환하여 종료 처리
        if self.current_index >= self.num_frames:
            return None, None
            
        # 현재 인덱스에 해당하는 센서 데이터 가져오기
        sensor_data = self.provider.get_sensor_data_by_index(self.stream_id, self.current_index)
        image_record = sensor_data.image_data_and_record()
        
        # device time (ns) 추출
        timestamp_ns = image_record[1].capture_timestamp_ns
        
        # numpy 배열로 변환
        image_array = image_record[0].to_numpy_array()

        # fisheye -> pinhole rectification
        if self.rectify_enabled:
            rectified = calibration.distort_by_calibration(
                image_array,
                self.rectify_target_calib,
                self.src_calib,
            )

            if self.rotate_cw90:
                rectified = np.rot90(rectified, k=3).copy()

            self._save_debug_images_once(image_array, rectified)
            image_array = rectified
        else:
            # raw 모드라면 첫 frame에서라도 shape 기반 calibration info를 채워 둠
            if self.output_width is None or self.output_height is None:
                h, w = image_array.shape[:2]
                self.output_width = w
                self.output_height = h
                self.output_cx = w / 2.0
                self.output_cy = h / 2.0
             
        # 다음 프레임을 위해 인덱스 1 증가
        self.current_index += 1
        
        return timestamp_ns, image_array
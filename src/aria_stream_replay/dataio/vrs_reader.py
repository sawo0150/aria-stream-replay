import os
from projectaria_tools.core.data_provider import create_vrs_data_provider
from projectaria_tools.core.sensor_data import TimeDomain

class VrsReader:
    def __init__(self, vrs_path: str):
        if not os.path.exists(vrs_path):
            raise FileNotFoundError(f"VRS file not found: {vrs_path}")
        
        self.provider = create_vrs_data_provider(vrs_path)
        if not self.provider:
            raise RuntimeError("Failed to open VRS file.")
            
        # RGB 카메라 스트림 ID 찾기 (보통 214-1 또는 1201-1)
        self.rgb_stream_id = self.provider.get_stream_id_from_label("camera-rgb")
        if not self.rgb_stream_id:
            raise ValueError("RGB stream not found in this VRS file.")
            
        self.iterator = self.provider.deliver_stream_data(self.rgb_stream_id)
        
    def next_frame(self):
        """다음 프레임의 Timestamp(ns)와 이미지 배열을 반환합니다."""
        try:
            sensor_data = next(self.iterator)
            image_record = sensor_data.image_data_and_record()
            
            # device time (ns) 추출
            timestamp_ns = image_record[1].capture_timestamp_ns
            
            # numpy 배열로 변환
            image_array = image_record[0].to_numpy_array()
            
            return timestamp_ns, image_array
        except StopIteration:
            return None, None
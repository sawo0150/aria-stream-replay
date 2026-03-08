import os
from projectaria_tools.core.data_provider import create_vrs_data_provider

class VrsReader:
    def __init__(self, vrs_path: str):
        if not os.path.exists(vrs_path):
            raise FileNotFoundError(f"VRS file not found: {vrs_path}")
        
        self.provider = create_vrs_data_provider(vrs_path)
        if not self.provider:
            raise RuntimeError("Failed to open VRS file.")
            
        # RGB 카메라 스트림 ID 찾기
        self.rgb_stream_id = self.provider.get_stream_id_from_label("camera-rgb")
        if not self.rgb_stream_id:
            raise ValueError("RGB stream not found in this VRS file.")
            
        # 전체 데이터(프레임) 개수를 가져오고 현재 읽을 인덱스를 0으로 초기화
        self.num_frames = self.provider.get_num_data(self.rgb_stream_id)
        self.current_index = 0
        
    def next_frame(self):
        """다음 프레임의 Timestamp(ns)와 이미지 배열을 반환합니다."""
        # 모든 프레임을 다 읽었다면 None 반환하여 종료 처리
        if self.current_index >= self.num_frames:
            return None, None
            
        # 현재 인덱스에 해당하는 센서 데이터 가져오기
        sensor_data = self.provider.get_sensor_data_by_index(self.rgb_stream_id, self.current_index)
        image_record = sensor_data.image_data_and_record()
        
        # device time (ns) 추출
        timestamp_ns = image_record[1].capture_timestamp_ns
        
        # numpy 배열로 변환
        image_array = image_record[0].to_numpy_array()
        
        # 다음 프레임을 위해 인덱스 1 증가
        self.current_index += 1
        
        return timestamp_ns, image_array
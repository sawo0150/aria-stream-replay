import time

class ReplayClock:
    def __init__(self, speed_factor: float = 1.0):
        self.speed_factor = speed_factor
        self.first_device_time_ns = -1
        self.first_real_time_sec = -1.0

    def wait_until(self, device_time_ns: int):
        if self.first_device_time_ns < 0:
            # 첫 프레임이 들어왔을 때 시간 초기화
            self.first_device_time_ns = device_time_ns
            self.first_real_time_sec = time.perf_counter()
            return

        # 기기 기준 경과 시간 (초)
        elapsed_device_sec = (device_time_ns - self.first_device_time_ns) / 1e9
        
        # 현재 물리 기준 경과 시간 (초)
        elapsed_real_sec = (time.perf_counter() - self.first_real_time_sec) * self.speed_factor
        
        # 남은 시간만큼 sleep (음수면 스킵)
        sleep_time = elapsed_device_sec - elapsed_real_sec
        if sleep_time > 0:
            time.sleep(sleep_time)
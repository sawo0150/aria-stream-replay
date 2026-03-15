# aria_stream_replay/core/replay_clock.py

import time

class ReplayClock:
    def __init__(
        self,
        mode: str = "rate",
        speed_factor: float = 1.0,
        fps: float = None,
    ):
        """
        mode='rate':
            원본 device timestamp 간격을 유지하되, speed_factor로만 재생 속도를 조절
            예) speed_factor=0.1 -> 10배 느리게 재생
                speed_factor=2.0 -> 2배 빠르게 재생

        mode='fps':
            원본 device timestamp 축을 따라가되,
            fps 격자(slot) 기준으로 대표 프레임만 발행하고 나머지는 drop
            예) 원본이 30Hz, fps=10이면 대략 3장 중 1장만 publish
        """
        self.mode = mode
        self.speed_factor = speed_factor
        self.fps = fps

        self.first_device_time_ns = -1
        self.first_real_time_sec = -1.0
        self.last_published_slot = -1

        if self.mode not in ("rate", "fps"):
            raise ValueError(f"Unsupported replay clock mode: {self.mode}")

        if self.mode == "rate" and self.speed_factor <= 0:
            raise ValueError("speed_factor must be > 0 in rate mode")

        if self.mode == "fps":
            if self.fps is None or self.fps <= 0:
                raise ValueError("fps must be set and > 0 in fps mode")
 
 
    def wait_until(self, device_time_ns: int) -> bool:
        """
        Returns:
            True  -> 이 프레임을 publish 해야 함
            False -> 이 프레임은 drop 해야 함
        """
        if self.first_device_time_ns < 0:
            # 첫 프레임 기준점 설정: 첫 프레임은 즉시 발행
            self.first_device_time_ns = device_time_ns
            self.first_real_time_sec = time.perf_counter()
            self.last_published_slot = 0
            return True
        
        if self.mode == "rate":
            # 원본 timestamp 기준 경과 시간 / speed_factor 만큼의 wall time이 지나도록 대기
            elapsed_device_sec = (device_time_ns - self.first_device_time_ns) / 1e9
            target_elapsed_real_sec = elapsed_device_sec / self.speed_factor
            elapsed_real_sec = time.perf_counter() - self.first_real_time_sec
            sleep_time = target_elapsed_real_sec - elapsed_real_sec

            if sleep_time > 0:
                time.sleep(sleep_time)
            return True

        # fps mode:
        # 원본 device timeline 상에서 현재 프레임이 어느 fps slot에 해당하는지 계산
        elapsed_device_sec = (device_time_ns - self.first_device_time_ns) / 1e9
        current_slot = int(elapsed_device_sec * self.fps)

        # 아직 같은 slot이면 publish하지 않고 drop
        if current_slot <= self.last_published_slot:
            return False

        # 새로운 slot의 첫 대표 프레임이므로 wall-clock도 그 slot 시간에 맞춰 동기화
        target_elapsed_real_sec = current_slot / self.fps
        elapsed_real_sec = time.perf_counter() - self.first_real_time_sec
        sleep_time = target_elapsed_real_sec - elapsed_real_sec

        if sleep_time > 0:
            time.sleep(sleep_time)

        self.last_published_slot = current_slot
        return True
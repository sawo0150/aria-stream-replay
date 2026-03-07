import zmq
from ..event_types import FrameMsg, ControlMsg

class ZmqPublisher:
    def __init__(self, port: int = 5555):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(f"tcp://127.0.0.1:{port}")
        print(f"[ZMQ] Publisher bound to tcp://127.0.0.1:{port}")

    def send_frame(self, msg: FrameMsg):
        # 파이썬 객체(numpy 포함)를 직렬화하여 전송
        self.socket.send_pyobj(msg)

    def send_control(self, msg: ControlMsg):
        self.socket.send_pyobj(msg)
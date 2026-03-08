import zmq
from ..event_types import FrameMsg, OdomMsg, ControlMsg

class ZmqPublisher:
    def __init__(self, frame_endpoint: str, odom_endpoint: str):
        self.context = zmq.Context()
        self.frame_socket = self.context.socket(zmq.PUB)
        self.frame_socket.bind(frame_endpoint)
        
        self.odom_socket = self.context.socket(zmq.PUB)
        self.odom_socket.bind(odom_endpoint)
        
        print(f"[ZMQ] Frame Publisher bound to {frame_endpoint}")
        print(f"[ZMQ] Odom Publisher bound to {odom_endpoint}")

    def send_frame(self, msg: FrameMsg):
        # 파이썬 객체(numpy 포함)를 직렬화하여 전송
        self.frame_socket.send_pyobj(msg)

    def send_odom(self, msg: OdomMsg):
        self.odom_socket.send_pyobj(msg)

    def send_control(self, msg: ControlMsg):
        self.frame_socket.send_pyobj(msg)
        self.odom_socket.send_pyobj(msg)
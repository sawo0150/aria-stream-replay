# aria_stream_replay/transport/zmq_pub.py

import zmq
from ..event_types import BundleMsg, ControlMsg

class ZmqPublisher:
    def __init__(self, bundle_endpoint: str):
        self.context = zmq.Context()
        self.bundle_socket = self.context.socket(zmq.PUB)
        self.bundle_socket.bind(bundle_endpoint)

        print(f"[ZMQ] Bundle Publisher bound to {bundle_endpoint}")


    def send_bundle(self, msg: BundleMsg):
        # 파이썬 객체(numpy 포함)를 직렬화하여 전송
        self.bundle_socket.send_pyobj(msg)

    def send_control(self, msg: ControlMsg):
        self.bundle_socket.send_pyobj(msg)
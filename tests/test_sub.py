import os
import sys
import cv2
import zmq
import numpy as np


def add_project_paths():
    """
    recv_pyobj()가 BundleMsg / ControlMsg를 unpickle할 수 있도록
    aria_stream_replay 패키지가 보일 만한 경로를 sys.path에 추가합니다.

    직접 import는 하지 않지만, pickle 복원을 위해 모듈 경로는 보여야 합니다.
    """
    this_dir = os.path.abspath(os.path.dirname(__file__))
    candidates = [
        this_dir,
        os.path.abspath(os.path.join(this_dir, ".")),
        os.path.abspath(os.path.join(this_dir, "..")),
        os.path.abspath(os.path.join(this_dir, "../..")),
    ]

    for path in candidates:
        if path not in sys.path:
            sys.path.insert(0, path)


def safe_class_name(obj):
    try:
        return type(obj).__name__
    except Exception:
        return "Unknown"


def format_odom_text(odom_msg):
    if odom_msg is None:
        return "Odom: None"

    try:
        T = odom_msg.T_world_device
        tx, ty, tz = T[:3, 3]
        source = getattr(odom_msg, "source", "unknown")
        return f"Odom [{source}] X:{tx:.2f}, Y:{ty:.2f}, Z:{tz:.2f}"
    except Exception as e:
        return f"Odom: parse error ({e})"


def to_bgr_for_display(image):
    """
    numpy image를 OpenCV 표시용 BGR로 변환합니다.
    """
    if image is None:
        return None

    display_img = image.copy()

    if display_img.dtype != np.uint8:
        display_img = np.clip(display_img, 0, 255).astype(np.uint8)

    if len(display_img.shape) == 2:
        display_img = cv2.cvtColor(display_img, cv2.COLOR_GRAY2BGR)
    elif len(display_img.shape) == 3 and display_img.shape[2] == 3:
        # publisher 쪽이 RGB라고 가정
        display_img = cv2.cvtColor(display_img, cv2.COLOR_RGB2BGR)
    elif len(display_img.shape) == 3 and display_img.shape[2] == 4:
        # RGBA라고 가정
        display_img = cv2.cvtColor(display_img, cv2.COLOR_RGBA2BGR)

    return display_img


def draw_text_block(img, lines, x=30, y=50, dy=40):
    for i, line in enumerate(lines):
        yy = y + i * dy
        color = (0, 255, 0)

        if line.startswith("Odom"):
            color = (0, 255, 255)  # 노란색
        elif line.startswith("Warning") or line.startswith("Error"):
            color = (0, 0, 255)    # 빨간색

        cv2.putText(
            img,
            line,
            (x, yy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            2,
            cv2.LINE_AA,
        )


def main():
    add_project_paths()

    context = zmq.Context()
    socket = context.socket(zmq.SUB)

    # bundle_endpoint 하나만 연결
    endpoint = "tcp://127.0.0.1:5555"
    socket.connect(endpoint)
    socket.setsockopt(zmq.SUBSCRIBE, b"")

    print(f"🟢 [Subscriber] Connected to bundle endpoint: {endpoint}")
    print("🟢 [Subscriber] Waiting for BundleMsg / ControlMsg...\n")

    window_name = "Aria Bundle Stream Viewer"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    last_status_text = "Waiting for first bundle..."
    frame_count = 0

    try:
        while True:
            try:
                msg = socket.recv_pyobj()
            except Exception as e:
                print(f"\n🔴 [Subscriber] recv_pyobj() failed: {e}")
                print("   - publisher가 send_pyobj(BundleMsg)를 쓰고 있다면")
                print("   - 이 스크립트 실행 위치에서 aria_stream_replay 패키지가 import 가능해야 합니다.")
                break

            msg_type = safe_class_name(msg)

            # 1) ControlMsg 처리
            if msg_type == "ControlMsg":
                command = getattr(msg, "command", None)
                print(f"🟡 [Subscriber] ControlMsg received: {command}")

                if command in ["EOS", "STOP"]:
                    print("🔴 [Subscriber] Stopping as requested by Publisher.")
                    break
                continue

            # 2) BundleMsg 처리
            if msg_type != "BundleMsg":
                print(f"🟡 [Subscriber] Unexpected message type: {msg_type}")
                continue

            frame_msg = getattr(msg, "frame", None)
            odom_msg = getattr(msg, "odom", None)

            if frame_msg is None:
                print("🟡 [Subscriber] BundleMsg received but frame is None. Skipping.")
                continue

            image = getattr(frame_msg, "image", None)
            seq = getattr(frame_msg, "seq", -1)
            ts_ns = getattr(frame_msg, "device_time_ns", -1)
            sensor_name = getattr(frame_msg, "sensor_name", "unknown")

            if image is None:
                print(f"🟡 [Subscriber] Bundle seq={seq} has no image. Skipping.")
                continue

            display_img = to_bgr_for_display(image)
            if display_img is None:
                print(f"🟡 [Subscriber] Bundle seq={seq} image conversion failed. Skipping.")
                continue

            odom_text = format_odom_text(odom_msg)
            has_odom = odom_msg is not None

            lines = [
                f"Seq: {seq}",
                f"Time: {ts_ns} ns",
                f"Sensor: {sensor_name}",
                odom_text,
            ]

            draw_text_block(display_img, lines)

            cv2.imshow(window_name, display_img)
            frame_count += 1
            last_status_text = f"Last bundle seq={seq}, odom={'yes' if has_odom else 'no'}"

            if frame_count % 30 == 0:
                print(f"🟢 [Subscriber] {last_status_text}")

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print("🔴 [Subscriber] 'q' pressed. Exiting viewer.")
                break

    except KeyboardInterrupt:
        print("\n🔴 [Subscriber] Stopped by user (Ctrl+C).")

    finally:
        socket.close()
        context.term()
        cv2.destroyAllWindows()
        print(f"🟢 [Subscriber] Cleaned up and exited. ({last_status_text})")


if __name__ == "__main__":
    main()
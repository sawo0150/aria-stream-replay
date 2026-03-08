# aria-stream-replay
aria-stream-replay

pip install -e .

python src/aria_stream_replay/main.py

python src/aria_stream_replay/main.py replay.rate=0.1

# SLAM 실행 (ZMQ config 사용)
python slam.py --config configs/live/aria_zmq.yaml
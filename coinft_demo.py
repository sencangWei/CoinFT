"""Local CoinFT presentation dashboard. Six axes are relative trends, not force units.

Examples:
    python coinft_demo.py --port COM10
    python coinft_demo.py --replay dynamic_20260907.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import struct
import threading
import time
import webbrowser
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
FRAME_SIZE = 26
SATURATION = 33782


class FrameParser:
    """Parse one-sensor Teensy frames, confirming each with the next header."""

    def __init__(self):
        self.buffer = bytearray()
        self.resyncs = 0

    def feed(self, chunk: bytes):
        self.buffer.extend(chunk)
        frames = []
        while len(self.buffer) >= FRAME_SIZE + 2:
            if self.buffer[:2] != b"\x00\x00":
                next_header = self.buffer.find(b"\x00\x00", 1)
                if next_header < 0:
                    self.resyncs += len(self.buffer) - 1
                    del self.buffer[:-1]
                    break
                self.resyncs += next_header
                del self.buffer[:next_header]
                continue
            if self.buffer[FRAME_SIZE:FRAME_SIZE + 2] != b"\x00\x00":
                self.resyncs += 1
                del self.buffer[0]
                continue
            frames.append(struct.unpack("<12H", self.buffer[2:FRAME_SIZE]))
            del self.buffer[:FRAME_SIZE]
        return frames


class RelativeProjector:
    """Apply the project's historical 24x6 matrix to locally tared counts."""

    def __init__(self, matrix):
        if len(matrix) != 24 or any(len(row) != 6 for row in matrix):
            raise ValueError("Expected a 24x6 historical matrix")
        self.matrix = matrix
        self.baseline = None

    def tare(self, frames):
        if not frames:
            raise ValueError("Cannot tare without frames")
        self.baseline = [median(frame[i] for frame in frames) for i in range(12)]

    def project(self, raw):
        if self.baseline is None:
            raise ValueError("Tare first")
        delta = [float(raw[i]) - self.baseline[i] for i in range(12)]
        features = delta + [value * value for value in delta]
        axes = [sum(features[i] * self.matrix[i][j] for i in range(24)) for j in range(6)]
        return axes, delta


class DemoSource:
    """Own the serial port or replay file and publish a small JSON snapshot."""

    def __init__(self, port=None, replay=None, replay_speed=1.0):
        matrix_path = ROOT / "calibration" / "coinft_calib.json"
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))["matrix_24x6"]
        self.projector = RelativeProjector(matrix)
        self.port = port
        self.replay = Path(replay).resolve() if replay else None
        self.replay_speed = replay_speed
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.tare_requested = True
        self.tare_frames = []
        self.axis_window = deque([[0.0] * 6 for _ in range(50)], maxlen=50)
        self.rate_started_at = None
        self.rate_started_frames = 0
        self.saturation_times = deque()
        self.invalid_times = deque()
        self.parser = FrameParser()
        self.state = {
            "mode": "replay" if replay else "live",
            "status": "connecting",
            "message": "正在准备数据源",
            "port": port or "",
            "axes": [0.0] * 6,
            "channels": [0.0] * 12,
            "raw": [0] * 12,
            "rate": 0.0,
            "frames": 0,
            "resyncs": 0,
            "saturated": 0,
            "saturated_recent": 0,
            "invalid_frames": 0,
            "invalid_recent": 0,
            "tare_progress": 0,
            "updated_at": 0,
            "diagnostics": {
                "serial_reads": 0,
                "serial_bytes": 0,
                "parsed_frames": 0,
                "last_byte_at": 0,
                "last_parsed_frame_at": 0,
                "parser_pending_bytes": 0,
                "parser_discarded_bytes": 0,
            },
            "recovery": {
                "attempts": 0,
                "successes": 0,
                "last_fault": None,
            },
        }
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=2)

    def request_tare(self):
        with self.lock:
            self.tare_requested = True
            self.tare_frames = []
            self.axis_window = deque([[0.0] * 6 for _ in range(50)], maxlen=50)
            self.state.update(status="taring", message="保持空载，正在采集基线", tare_progress=0)

    def snapshot(self):
        with self.lock:
            snapshot = dict(self.state)
            snapshot["diagnostics"] = dict(self.state["diagnostics"])
            snapshot["recovery"] = dict(self.state["recovery"])
            if self.state["recovery"]["last_fault"] is not None:
                snapshot["recovery"]["last_fault"] = dict(
                    self.state["recovery"]["last_fault"])
                snapshot["recovery"]["last_fault"]["diagnostics"] = dict(
                    self.state["recovery"]["last_fault"]["diagnostics"])
            return snapshot

    def _set_status(self, status, message):
        with self.lock:
            self.state.update(status=status, message=message)

    def _record_serial_fault(self, reason, status, message):
        with self.lock:
            self.state["recovery"]["last_fault"] = {
                "reason": reason,
                "observed_at": time.time(),
                "frames": self.state["frames"],
                "diagnostics": dict(self.state["diagnostics"]),
            }
            self.state.update(status=status, message=message)

    def _consume(self, raw):
        now = time.monotonic()
        with self.lock:
            if self.rate_started_at is None:
                self.rate_started_at = now
                self.rate_started_frames = self.state["frames"]
            invalid_now = any(value > SATURATION for value in raw)
            if invalid_now:
                self.invalid_times.append(now)
            while self.invalid_times and now - self.invalid_times[0] > 2:
                self.invalid_times.popleft()
            saturated_now = sum(value == SATURATION for value in raw)
            if saturated_now:
                self.saturation_times.append((now, saturated_now))
            while self.saturation_times and now - self.saturation_times[0][0] > 2:
                self.saturation_times.popleft()
            self.state["frames"] += 1
            self.state["rate"] = round(
                (self.state["frames"] - self.rate_started_frames - 1)
                / max(now - self.rate_started_at, 0.001), 1
            )
            self.state["resyncs"] = self.parser.resyncs
            self.state["saturated"] += saturated_now
            self.state["saturated_recent"] = sum(count for _, count in self.saturation_times)
            self.state["invalid_frames"] += int(invalid_now)
            self.state["invalid_recent"] = len(self.invalid_times)
            if invalid_now:
                return
            self.state["raw"] = list(raw)
            self.state["updated_at"] = time.time()
            if self.tare_requested:
                self.tare_frames.append(raw)
                self.state["status"] = "taring"
                self.state["message"] = "保持空载，正在采集基线"
                self.state["tare_progress"] = min(100, round(len(self.tare_frames) / 400 * 100))
                if len(self.tare_frames) >= 400:
                    self.projector.tare(self.tare_frames)
                    self.tare_frames = []
                    self.tare_requested = False
                    self.state.update(status="live", message="数据流正常", tare_progress=100)
                return
            axes, delta = self.projector.project(raw)
            self.axis_window.append(axes)
            self.state["axes"] = [
                round(median(frame[i] for frame in self.axis_window), 7)
                for i in range(6)
            ]
            self.state["channels"] = [round(value, 1) for value in delta]
            if self.state["status"] == "waiting":
                self.state.update(status="live", message="数据流正常")

    def _run_replay(self):
        with self.replay.open(newline="", encoding="utf-8-sig") as file:
            rows = []
            for row in csv.reader(file):
                if len(row) == 12:
                    try:
                        rows.append(tuple(int(float(value)) for value in row))
                    except ValueError:
                        continue
        if len(rows) < 401:
            raise ValueError("回放文件少于 401 帧，无法建立 2 秒空载基线")
        self._set_status("taring", "历史回放：建立基线")
        step = 1 / (200 * self.replay_speed)
        next_at = time.monotonic()
        while not self.stop_event.is_set():
            for row in rows:
                if self.stop_event.is_set():
                    break
                self._consume(row)
                next_at += step
                delay = next_at - time.monotonic()
                if delay > 0:
                    self.stop_event.wait(delay)
                elif delay < -0.25:
                    next_at = time.monotonic()

    def _run_serial(self):
        import serial

        automatic = False
        previous_automatic_start = None
        while not self.stop_event.is_set():
            if automatic:
                if previous_automatic_start is not None:
                    remaining = 5.0 - (time.monotonic() - previous_automatic_start)
                    if remaining > 0 and self.stop_event.wait(remaining):
                        return
                if self.stop_event.is_set():
                    return

            ser = None
            primary_fault = False
            try:
                if self.stop_event.is_set():
                    return
                if automatic:
                    previous_automatic_start = time.monotonic()
                    with self.lock:
                        self.state["recovery"]["attempts"] += 1
                ser = serial.Serial(self.port, 115200, timeout=0.1)
                self.parser.buffer.clear()
                with self.lock:
                    self.rate_started_at = None
                    self.state["rate"] = 0.0
                    self.state["diagnostics"]["parser_pending_bytes"] = 0
                ser.write(b"i")
                if self.stop_event.wait(0.2) or self.stop_event.is_set():
                    return
                ser.reset_input_buffer()
                if self.stop_event.is_set():
                    return
                ser.write(b"s")
                last_raw_progress = time.monotonic()
                last_frame_progress = last_raw_progress
                pending_success = automatic
                if automatic:
                    self._set_status("waiting", "串口已打开，尚未收到有效数据帧")
                while not self.stop_event.is_set():
                    chunk = ser.read(4096)
                    read_at = time.time()
                    progress_at = time.monotonic()
                    previous_resyncs = self.parser.resyncs
                    frames = self.parser.feed(chunk)
                    with self.lock:
                        diagnostics = self.state["diagnostics"]
                        diagnostics["serial_reads"] += 1
                        diagnostics["serial_bytes"] += len(chunk)
                        if chunk:
                            diagnostics["last_byte_at"] = read_at
                        diagnostics["parsed_frames"] += len(frames)
                        if frames:
                            diagnostics["last_parsed_frame_at"] = read_at
                        diagnostics["parser_pending_bytes"] = len(self.parser.buffer)
                        diagnostics["parser_discarded_bytes"] += self.parser.resyncs - previous_resyncs
                    if chunk:
                        last_raw_progress = progress_at
                    if frames:
                        last_frame_progress = progress_at
                    for frame in frames:
                        self._consume(frame)
                        if pending_success and all(value <= SATURATION for value in frame):
                            with self.lock:
                                if self.state["status"] == "live":
                                    self.state["recovery"]["successes"] += 1
                                    pending_success = False
                    progress_at = time.monotonic()
                    if (progress_at - last_raw_progress >= 2.0 and
                            progress_at - last_frame_progress >= 2.0):
                        self._record_serial_fault(
                            "serial silence: no byte or parsed-frame progress for 2.0s",
                            "waiting",
                            "串口已打开，尚未收到有效数据帧",
                        )
                        primary_fault = True
                        automatic = True
                        break
                    if progress_at - last_frame_progress >= 2.0:
                        self._set_status("waiting", "串口已打开，尚未收到有效数据帧")
            except (OSError, serial.SerialException) as exc:
                self._record_serial_fault(
                    str(exc),
                    "error",
                    f"无法连接 {self.port}：{exc}",
                )
                primary_fault = True
                automatic = True
            finally:
                if ser is not None:
                    if not primary_fault:
                        try:
                            ser.write(b"i")
                        except (OSError, serial.SerialException) as exc:
                            if not self.stop_event.is_set():
                                self._record_serial_fault(
                                    str(exc), "error", f"无法连接 {self.port}：{exc}")
                                automatic = True
                    try:
                        ser.close()
                    except (OSError, serial.SerialException) as exc:
                        if not primary_fault and not self.stop_event.is_set():
                            self._record_serial_fault(
                                str(exc), "error", f"无法连接 {self.port}：{exc}")
                            automatic = True

    def _run(self):
        try:
            if self.replay:
                self._run_replay()
            else:
                self._run_serial()
        except Exception as exc:
            self._set_status("error", str(exc))


def make_handler(source):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT / "demo_web"), **kwargs)

        def do_GET(self):
            if self.path == "/api/state":
                body = json.dumps(source.snapshot(), ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

        def do_POST(self):
            if self.path != "/api/tare":
                self.send_error(404)
                return
            source.request_tare()
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format, *args):
            if not self.path.startswith("/api/state"):
                super().log_message(format, *args)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM10", help="Teensy USB serial port (default COM10)")
    parser.add_argument("--replay", help="Replay a 12-column raw CSV instead of opening COM10")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    source = DemoSource(port=args.port, replay=args.replay)
    server = ThreadingHTTPServer((args.host, args.http_port), make_handler(source))
    source.start()
    url = f"http://{args.host}:{args.http_port}/"
    print(f"CoinFT dashboard: {url}")
    print("Mode: HISTORICAL REPLAY" if args.replay else f"Mode: LIVE {args.port}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        source.stop()


if __name__ == "__main__":
    main()

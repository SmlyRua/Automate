#!/usr/bin/env python3
"""Record and replay keyboard/mouse input on Windows 10.

Requires: pip install pynput
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from threading import Event
from typing import Any, Dict, Optional

from pynput import keyboard, mouse

STOP_RECORD_KEY = keyboard.Key.f8
STOP_REPLAY_KEY = keyboard.Key.esc
ALLOWED_MOUSE_BUTTONS = {mouse.Button.left, mouse.Button.middle, mouse.Button.right}


class InputRecorder:
    def __init__(self, output_dir: Path, output_prefix: str = "input_log") -> None:
        self.output_dir = output_dir
        self.output_prefix = output_prefix
        self.mouse_listener: Optional[mouse.Listener] = None
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self.start_time = 0.0
        self.events: list[Dict[str, Any]] = []

    def _timestamp(self) -> float:
        return time.perf_counter() - self.start_time

    def _serialize_key(self, key: keyboard.KeyCode | keyboard.Key) -> Dict[str, str]:
        if isinstance(key, keyboard.KeyCode):
            return {"kind": "char", "value": key.char or ""}
        return {"kind": "special", "value": key.name}

    def _on_key_press(self, key: keyboard.KeyCode | keyboard.Key) -> Optional[bool]:
        if key == STOP_RECORD_KEY:
            return False

        self.events.append(
            {
                "time": self._timestamp(),
                "event": "key_press",
                "key": self._serialize_key(key),
            }
        )
        return None

    def _on_key_release(self, key: keyboard.KeyCode | keyboard.Key) -> Optional[bool]:
        if key == STOP_RECORD_KEY:
            return False

        self.events.append(
            {
                "time": self._timestamp(),
                "event": "key_release",
                "key": self._serialize_key(key),
            }
        )
        return None

    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        if button not in ALLOWED_MOUSE_BUTTONS:
            return

        # pynput phát ra 2 callback cho mỗi click (pressed=True/False).
        # Chỉ lưu pressed=True để tránh duplicate log click.
        if not pressed:
            return

        self.events.append(
            {
                "time": self._timestamp(),
                "event": "mouse_click",
                "x": x,
                "y": y,
                "button": button.name,
            }
        )

    def _on_mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        self.events.append(
            {
                "time": self._timestamp(),
                "event": "mouse_scroll",
                "x": x,
                "y": y,
                "dx": dx,
                "dy": dy,
            }
        )

    def _build_output_file(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        candidate = self.output_dir / f"{self.output_prefix}_{timestamp}.json"
        if not candidate.exists():
            return candidate

        index = 1
        while True:
            fallback = self.output_dir / f"{self.output_prefix}_{timestamp}_{index}.json"
            if not fallback.exists():
                return fallback
            index += 1

    def record(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_file = self._build_output_file()

        print(f"Bắt đầu ghi input. Nhấn F8 để dừng...\nFile log: {output_file}")
        self.start_time = time.perf_counter()

        self.mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll,
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )

        self.mouse_listener.start()
        self.keyboard_listener.start()

        self.keyboard_listener.join()
        self.mouse_listener.stop()

        output_file.write_text(json.dumps(self.events, indent=2), encoding="utf-8")
        print(f"Đã lưu {len(self.events)} sự kiện vào: {output_file}")
        return output_file


class InputReplayer:
    def __init__(self, input_file: Path, speed: float = 1.0) -> None:
        if speed <= 0:
            raise ValueError("speed phải lớn hơn 0")

        self.input_file = input_file
        self.speed = speed
        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()
        self.stop_requested = Event()
        self.stop_listener: Optional[keyboard.Listener] = None
        self.injecting_event = False

    def _deserialize_key(self, key_data: Dict[str, str]) -> keyboard.KeyCode | keyboard.Key:
        kind = key_data.get("kind")
        value = key_data.get("value", "")

        if kind == "char":
            return keyboard.KeyCode.from_char(value)

        if kind == "special":
            key_obj = getattr(keyboard.Key, value, None)
            if key_obj is None:
                raise ValueError(f"Không hỗ trợ phím đặc biệt: {value}")
            return key_obj

        raise ValueError(f"Dữ liệu phím không hợp lệ: {key_data}")

    def _on_stop_key_press(self, key: keyboard.KeyCode | keyboard.Key) -> Optional[bool]:
        if self.injecting_event:
            return None

        if key == STOP_REPLAY_KEY:
            self.stop_requested.set()
            return False
        return None

    def _sleep_with_interrupt(self, seconds: float) -> bool:
        if seconds <= 0:
            return True

        end_time = time.perf_counter() + seconds
        while time.perf_counter() < end_time:
            if self.stop_requested.is_set():
                return False
            remaining = end_time - time.perf_counter()
            time.sleep(min(0.01, max(remaining, 0)))
        return not self.stop_requested.is_set()

    def _start_stop_listener(self) -> None:
        self.stop_requested.clear()
        self.stop_listener = keyboard.Listener(on_press=self._on_stop_key_press)
        self.stop_listener.start()

    def _stop_stop_listener(self) -> None:
        if self.stop_listener is not None:
            self.stop_listener.stop()
            self.stop_listener = None

    def replay(self) -> None:
        events = json.loads(self.input_file.read_text(encoding="utf-8"))
        if not events:
            print("File log rỗng, không có gì để replay.")
            return

        self._start_stop_listener()
        try:
            print("Bắt đầu replay sau 3 giây. Nhấn ESC để ngắt. Chuyển sang cửa sổ mục tiêu...")
            if not self._sleep_with_interrupt(3):
                print("Replay đã bị ngắt bởi ESC.")
                return

            prev_time = 0.0
            for event_data in events:
                if self.stop_requested.is_set():
                    print("Replay đã bị ngắt bởi ESC.")
                    return

                event_time = float(event_data["time"])
                delay = max((event_time - prev_time) / self.speed, 0)
                if not self._sleep_with_interrupt(delay):
                    print("Replay đã bị ngắt bởi ESC.")
                    return
                prev_time = event_time

                event_type = event_data["event"]

                if event_type == "mouse_click":
                    self.mouse_controller.position = (event_data["x"], event_data["y"])
                    btn = getattr(mouse.Button, event_data["button"], mouse.Button.left)
                    self.mouse_controller.click(btn)
                elif event_type == "mouse_scroll":
                    self.mouse_controller.position = (event_data["x"], event_data["y"])
                    self.mouse_controller.scroll(event_data["dx"], event_data["dy"])
                elif event_type == "key_press":
                    key = self._deserialize_key(event_data["key"])
                    self.injecting_event = True
                    try:
                        self.keyboard_controller.press(key)
                    finally:
                        self.injecting_event = False
                elif event_type == "key_release":
                    key = self._deserialize_key(event_data["key"])
                    self.injecting_event = True
                    try:
                        self.keyboard_controller.release(key)
                    finally:
                        self.injecting_event = False
                else:
                    print(f"Bỏ qua event không hỗ trợ: {event_type}")

            print("Replay hoàn tất.")
        finally:
            self._stop_stop_listener()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record/replay keyboard + mouse input trên Windows 10"
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    record_parser = sub.add_parser("record", help="Ghi input")
    record_parser.add_argument(
        "-d",
        "--output-dir",
        default="logs",
        help="Thư mục lưu log (mỗi lần record tạo file mới theo timestamp)",
    )
    record_parser.add_argument(
        "--prefix",
        default="input_log",
        help="Tiền tố tên file log, ví dụ input_log_YYYYmmdd_HHMMSS.json",
    )

    replay_parser = sub.add_parser("replay", help="Phát lại input đã ghi")
    replay_parser.add_argument("-i", "--input", required=True, help="File log đầu vào")
    replay_parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Tốc độ replay (1.0 = thời gian gốc, 2.0 = nhanh gấp đôi)",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.mode == "record":
        recorder = InputRecorder(Path(args.output_dir), output_prefix=args.prefix)
        recorder.record()
    else:
        InputReplayer(Path(args.input), speed=args.speed).replay()


if __name__ == "__main__":
    main()

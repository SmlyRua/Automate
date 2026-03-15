"""Ghi lại thao tác chuột/bàn phím và tạo luôn file replay.

Module này vừa làm nhiệm vụ record, vừa convert dữ liệu thô sang định dạng
lệnh replay để `replay.py` dùng trực tiếp.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pynput import keyboard, mouse

from convert import LogConverter


class InputRecorder:
    """Ghi sự kiện input và xuất cả log thô + log replay."""

    def __init__(self, output_dir: str = ".") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.raw_output_file = self.output_dir / f"raw_log_{stamp}.json"
        self.replay_output_file = self.output_dir / f"log_convert_{stamp}.json"

        self.events: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self._stop_event = threading.Event()

    def _timestamp(self) -> float:
        """Trả về thời gian (giây) tính từ lúc bắt đầu ghi."""
        if self.start_time is None:
            self.start_time = time.perf_counter()
        return round(time.perf_counter() - self.start_time, 6)

    @staticmethod
    def _safe_key_name(key: keyboard.Key | keyboard.KeyCode) -> str:
        """Đổi key của pynput sang chuỗi dễ lưu/đọc."""
        if hasattr(key, "char") and key.char is not None:
            return str(key.char)
        return str(key)

    def _append_event(
        self,
        event_type: str,
        x: Optional[int] = None,
        y: Optional[int] = None,
        key: Optional[str] = None,
        button: Optional[str] = None,
        scroll_delta: Optional[int] = None,
    ) -> None:
        """Thêm một sự kiện chuẩn hóa vào bộ nhớ."""
        event: Dict[str, Any] = {
            "timestamp": self._timestamp(),
            "event_type": event_type,
            "mouse_x": x,
            "mouse_y": y,
            "key": key,
            "button": button,
            "scroll_delta": scroll_delta,
        }
        self.events.append(event)

    def on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Bắt sự kiện nhấn phím (key_down)."""
        self._append_event(event_type="key_down", key=self._safe_key_name(key))

    def on_release(self, key: keyboard.Key | keyboard.KeyCode) -> bool | None:
        """Bắt sự kiện nhả phím (key_up).

        Nhấn F8 để dừng record. ESC vẫn được lưu như key bình thường.
        """
        key_name = self._safe_key_name(key)
        self._append_event(event_type="key_up", key=key_name)

        if key == keyboard.Key.f8:
            print("Đã phát hiện F8. Dừng ghi...")
            self._stop_event.set()
            return False
        return None

    def on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        """Bắt sự kiện click chuột (chỉ lưu lúc nhấn xuống)."""
        if not pressed:
            return

        button_name = str(button).split(".")[-1]
        self._append_event(
            event_type="mouse_click",
            x=x,
            y=y,
            button=button_name,
        )

    def on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Bắt sự kiện lăn chuột (scroll)."""
        _ = dx
        self._append_event(
            event_type="mouse_scroll",
            x=x,
            y=y,
            scroll_delta=dy,
        )


    def save_raw(self) -> None:
        """Lưu log thô ra file JSON."""
        self.raw_output_file.write_text(json.dumps(self.events, indent=2), encoding="utf-8")
        print(f"Đã lưu log thô: {self.raw_output_file}")

    def save_converted(self) -> None:
        """Convert và lưu file lệnh replay ngay sau khi record."""
        normalized = LogConverter.normalize_timestamps(self.events)
        with_delays = LogConverter.calculate_delays(normalized)
        commands = LogConverter(input_file=str(self.raw_output_file), output_file=str(self.replay_output_file)).to_replay_commands(with_delays)
        self.replay_output_file.write_text(json.dumps(commands, indent=2), encoding="utf-8")
        print(f"Đã lưu log replay: {self.replay_output_file} ({len(commands)} lệnh)")

    def record(self) -> None:
        """Bắt đầu ghi sự kiện và dừng khi người dùng nhấn F8."""
        print("Bắt đầu ghi thao tác. Nhấn F8 để dừng (ESC vẫn được lưu vào log).")
        self.start_time = time.perf_counter()

        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as k_listener, mouse.Listener(
            on_click=self.on_click,
            on_scroll=self.on_scroll,
        ) as m_listener:
            self._stop_event.wait()
            m_listener.stop()
            k_listener.stop()

        self.save_raw()
        self.save_converted()


def main() -> None:
    """Ví dụ chạy trực tiếp module record."""
    recorder = InputRecorder(output_dir=".")
    recorder.record()


if __name__ == "__main__":
    main()

"""Phát lại thao tác tự động từ file log replay."""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import pyautogui
from pynput import keyboard


class Replayer:
    """Đọc và chạy lần lượt các lệnh replay."""

    def __init__(self, input_file: str) -> None:
        self.input_file = Path(input_file)
        self._stop_event = threading.Event()

    def load_commands(self) -> List[Dict[str, Any]]:
        """Đọc danh sách command từ file JSON đã được convert."""
        return json.loads(self.input_file.read_text(encoding="utf-8"))

    @staticmethod
    def move_mouse(x: int, y: int) -> None:
        """Di chuyển chuột đến tọa độ (x, y)."""
        pyautogui.moveTo(x, y)

    @staticmethod
    def mouse_click(button: str) -> None:
        """Click chuột theo nút: left/right/middle."""
        pyautogui.click(button=button)

    @staticmethod
    def mouse_scroll(delta: int) -> None:
        """Cuộn chuột theo giá trị delta."""
        pyautogui.scroll(delta)

    @staticmethod
    def key_press(key: str, event_type: str = "key_down") -> None:
        """Nhấn hoặc nhả phím theo lệnh đã convert sẵn."""
        if event_type == "key_up":
            pyautogui.keyUp(key)
        else:
            pyautogui.keyDown(key)

    @staticmethod
    def key_hotkey(keys: List[str]) -> None:
        """Thực thi tổ hợp phím, ví dụ ['ctrl', 'c']."""
        pyautogui.hotkey(*keys)

    @staticmethod
    def sleep(delay: float) -> None:
        """Tạm dừng trước khi chạy lệnh kế tiếp."""
        if delay > 0:
            time.sleep(delay)

    def on_release(self, key: keyboard.Key | keyboard.KeyCode) -> bool | None:
        """Nhấn F8 để hủy replay ngay lập tức."""
        if key == keyboard.Key.f8:
            print("Đã phát hiện F8. Hủy replay...")
            self._stop_event.set()
            return False
        return None

    def execute(self, command: Dict[str, Any]) -> None:
        """Thực thi một command replay."""
        action = command.get("action")

        if action == "move":
            self.move_mouse(int(command["x"]), int(command["y"]))
        elif action == "click":
            self.mouse_click(str(command.get("button", "left")))
        elif action == "scroll":
            self.mouse_scroll(int(command.get("delta", 0)))
        elif action == "hotkey":
            keys = command.get("keys", [])
            if isinstance(keys, list) and keys:
                self.key_hotkey([str(key) for key in keys])
        elif action == "key":
            key = command.get("key")
            if key:
                self.key_press(str(key), event_type=str(command.get("event", "key_down")))

    def replay(self) -> None:
        """Chạy toàn bộ command theo thứ tự và delay; hủy bằng F8."""
        commands = self.load_commands()
        print(f"Đã tải {len(commands)} lệnh từ {self.input_file}")
        print("Replay bắt đầu sau 3 giây. Nhấn F8 để hủy.")
        time.sleep(3)

        with keyboard.Listener(on_release=self.on_release) as listener:
            for command in commands:
                if self._stop_event.is_set():
                    break
                self.sleep(float(command.get("delay", 0.0)))
                if self._stop_event.is_set():
                    break
                self.execute(command)

            listener.stop()

        print("Replay đã dừng." if self._stop_event.is_set() else "Replay hoàn tất.")


def parse_args() -> argparse.Namespace:
    """Đọc tham số CLI để chọn file log_convert cần replay."""
    parser = argparse.ArgumentParser(description="Replay thao tác từ file log_convert JSON")
    parser.add_argument(
        "-i",
        "--input",
        default=None,
        help="Đường dẫn file log_convert JSON (mặc định: file log_convert mới nhất)",
    )
    return parser.parse_args()


def resolve_input_file(input_arg: str | None) -> str:
    """Chọn file replay từ tham số hoặc tự lấy file log_convert mới nhất."""
    if input_arg:
        return input_arg

    candidates = sorted(Path(".").glob("log_convert_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if candidates:
        return str(candidates[0])
    return "log_convert.json"


def main() -> None:
    """Ví dụ chạy replay độc lập."""
    args = parse_args()
    pyautogui.FAILSAFE = True
    replayer = Replayer(input_file=resolve_input_file(args.input))
    replayer.replay()


if __name__ == "__main__":
    main()

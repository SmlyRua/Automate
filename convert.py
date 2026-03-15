"""Chuyển đổi log thô sang log replay tối ưu cho replay.py.

Mục tiêu:
- Chuẩn hóa tên phím ngay từ bước convert.
- Loại bớt key_down lặp (do giữ phím gây auto-repeat).
- Nhận diện tổ hợp phím phổ biến (vd: Ctrl+C, Ctrl+V) thành action `hotkey`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Set


class LogConverter:
    """Convert file log thô thành file lệnh replay."""

    MODIFIER_KEYS = {"ctrl", "alt", "shift", "win"}

    def __init__(self, input_file: str, output_file: str | None = None) -> None:
        self.input_file = Path(input_file)
        if output_file:
            self.output_file = Path(output_file)
        else:
            source = self.input_file.stem.replace("raw_log_", "")
            self.output_file = self.input_file.with_name(f"log_convert_{source}.json")

    def load_events(self) -> List[Dict[str, Any]]:
        """Đọc danh sách sự kiện từ file JSON thô."""
        return json.loads(self.input_file.read_text(encoding="utf-8"))

    @staticmethod
    def normalize_timestamps(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Chuẩn hóa mốc thời gian sao cho sự kiện đầu là 0.0 giây."""
        if not events:
            return []

        first_ts = float(events[0].get("timestamp", 0.0))
        normalized: List[Dict[str, Any]] = []
        for event in events:
            item = dict(event)
            item["timestamp"] = max(0.0, float(item.get("timestamp", 0.0)) - first_ts)
            normalized.append(item)
        return normalized

    @staticmethod
    def calculate_delays(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Tính delay giữa event hiện tại và event trước đó."""
        previous_ts = 0.0
        output: List[Dict[str, Any]] = []

        for event in events:
            current_ts = float(event.get("timestamp", 0.0))
            delay = max(0.0, current_ts - previous_ts)
            item = dict(event)
            item["delay"] = round(delay, 6)
            output.append(item)
            previous_ts = current_ts

        return output

    @staticmethod
    def normalize_key_name(raw_key: str | None) -> str | None:
        """Chuẩn hóa key từ format pynput sang format pyautogui."""
        if not raw_key:
            return None

        key = raw_key.strip()
        if key.startswith("Key."):
            key = key.split(".", 1)[1]

        aliases = {
            "ctrl_l": "ctrl",
            "ctrl_r": "ctrl",
            "alt_l": "alt",
            "alt_r": "alt",
            "shift_l": "shift",
            "shift_r": "shift",
            "cmd": "win",
            "cmd_l": "win",
            "cmd_r": "win",
            "esc": "esc",
            "space": "space",
            "enter": "enter",
            "tab": "tab",
            "backspace": "backspace",
            "caps_lock": "capslock",
            "page_up": "pageup",
            "page_down": "pagedown",
            "print_screen": "printscreen",
            "num_lock": "numlock",
            "scroll_lock": "scrolllock",
        }
        return aliases.get(key, key)

    def to_replay_commands(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Đổi event raw sang command dành cho replay.py.

        - Mouse: giữ nguyên hành vi move + click/scroll.
        - Keyboard:
          * bỏ key_down lặp khi phím đang được giữ
          * nhận diện hotkey nếu có modifier đang giữ + phím thường
          * xuất key_down/key_up đã chuẩn hóa sẵn cho replay
        """
        commands: List[Dict[str, Any]] = []
        pressed_keys: Set[str] = set()
        consumed_hotkey_keyups: Set[str] = set()

        for event in events:
            event_type = event.get("event_type")
            x = event.get("mouse_x")
            y = event.get("mouse_y")
            delay = float(event.get("delay", 0.0))

            if event_type == "mouse_click":
                if x is not None and y is not None:
                    commands.append({"action": "move", "x": x, "y": y, "delay": delay})
                commands.append({"action": "click", "button": event.get("button", "left"), "delay": 0.0})
                continue

            if event_type == "mouse_scroll":
                if x is not None and y is not None:
                    commands.append({"action": "move", "x": x, "y": y, "delay": delay})
                commands.append({"action": "scroll", "delta": event.get("scroll_delta", 0), "delay": 0.0})
                continue

            if event_type not in {"key_down", "key_up"}:
                continue

            normalized_key = self.normalize_key_name(event.get("key"))
            if not normalized_key:
                continue

            if event_type == "key_down":
                # Bỏ key_down lặp do OS auto-repeat khi đang giữ phím.
                if normalized_key in pressed_keys:
                    continue

                active_modifiers = [m for m in ["ctrl", "alt", "shift", "win"] if m in pressed_keys]
                if normalized_key not in self.MODIFIER_KEYS and active_modifiers:
                    commands.append(
                        {
                            "action": "hotkey",
                            "keys": [*active_modifiers, normalized_key],
                            "delay": delay,
                        }
                    )
                    pressed_keys.add(normalized_key)
                    consumed_hotkey_keyups.add(normalized_key)
                    continue

                if normalized_key in self.MODIFIER_KEYS:
                    pressed_keys.add(normalized_key)
                    continue

                commands.append(
                    {
                        "action": "key",
                        "event": "key_down",
                        "key": normalized_key,
                        "delay": delay,
                    }
                )
                pressed_keys.add(normalized_key)
                continue

            # key_up
            if normalized_key not in pressed_keys:
                # key_up mồ côi: bỏ qua để tránh replay sai.
                continue

            if normalized_key in consumed_hotkey_keyups:
                consumed_hotkey_keyups.remove(normalized_key)
                pressed_keys.remove(normalized_key)
                continue

            if normalized_key in self.MODIFIER_KEYS:
                pressed_keys.remove(normalized_key)
                continue

            commands.append(
                {
                    "action": "key",
                    "event": "key_up",
                    "key": normalized_key,
                    "delay": delay,
                }
            )
            pressed_keys.remove(normalized_key)

        return commands

    def convert(self) -> List[Dict[str, Any]]:
        """Chạy toàn bộ pipeline convert và ghi file đầu ra."""
        raw_events = self.load_events()
        normalized = self.normalize_timestamps(raw_events)
        with_delays = self.calculate_delays(normalized)
        commands = self.to_replay_commands(with_delays)

        self.output_file.write_text(json.dumps(commands, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Đã convert {len(raw_events)} event -> {len(commands)} lệnh replay.")
        print(f"File đầu ra: {self.output_file}")
        return commands


def parse_args() -> argparse.Namespace:
    """Đọc tham số CLI cho convert."""
    parser = argparse.ArgumentParser(description="Convert raw log JSON sang log replay JSON")
    parser.add_argument("-i", "--input", required=True, help="Đường dẫn file raw_log JSON")
    parser.add_argument("-o", "--output", default=None, help="Đường dẫn file log_convert JSON")
    return parser.parse_args()


def main() -> None:
    """Ví dụ chạy convert độc lập."""
    args = parse_args()
    converter = LogConverter(input_file=args.input, output_file=args.output)
    converter.convert()


if __name__ == "__main__":
    main()

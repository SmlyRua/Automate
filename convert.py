"""Chuyển đổi log thô sang log replay.

Lưu ý: Luồng chính hiện đã được gộp vào `record.py` (ghi xong là tự convert).
Module này vẫn giữ lại để bạn convert lại từ file `raw_log_*.json` khi cần.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


class LogConverter:
    """Convert file log thô thành file lệnh replay."""

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
    def to_replay_commands(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Đổi event raw sang command dành cho replay.py."""
        commands: List[Dict[str, Any]] = []

        for event in events:
            event_type = event.get("event_type")
            x = event.get("mouse_x")
            y = event.get("mouse_y")
            delay = float(event.get("delay", 0.0))

            if event_type == "mouse_click":
                if x is not None and y is not None:
                    commands.append({"action": "move", "x": x, "y": y, "delay": delay})
                commands.append({"action": "click", "button": event.get("button", "left"), "delay": 0.0})

            elif event_type == "mouse_scroll":
                if x is not None and y is not None:
                    commands.append({"action": "move", "x": x, "y": y, "delay": delay})
                commands.append({"action": "scroll", "delta": event.get("scroll_delta", 0), "delay": 0.0})

            elif event_type in {"key_down", "key_up"}:
                commands.append(
                    {
                        "action": "key",
                        "event": event_type,
                        "key": event.get("key"),
                        "delay": delay,
                    }
                )

        return commands

    def convert(self) -> List[Dict[str, Any]]:
        """Chạy toàn bộ pipeline convert và ghi file đầu ra."""
        raw_events = self.load_events()
        normalized = self.normalize_timestamps(raw_events)
        with_delays = self.calculate_delays(normalized)
        commands = self.to_replay_commands(with_delays)

        self.output_file.write_text(json.dumps(commands, indent=2), encoding="utf-8")
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

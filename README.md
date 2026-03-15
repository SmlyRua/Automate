# Input Recorder & Replayer (Windows 10)

Dự án Python để:
1. **Record** thao tác chuột + bàn phím.
2. **Tự động convert** log thô sang lệnh replay ngay sau khi dừng record.
3. **Replay** lại các thao tác đã ghi.

## Cấu trúc dự án

- `record.py`
  - Ghi sự kiện input thời gian thực bằng `pynput`.
  - Mỗi lần chạy sẽ tạo **file mới**:
    - `raw_log_YYYYMMDD_HHMMSS.json`
    - `log_convert_YYYYMMDD_HHMMSS.json`
  - Nhấn **F8** để dừng record (ESC vẫn được lưu vào log bình thường).
- `convert.py`
  - Module convert chạy độc lập (tùy chọn).
  - Dùng khi bạn muốn convert lại từ một file `raw_log_*.json`.
  - Tự xử lý dữ liệu thô cho replay: chuẩn hóa key, giảm key lặp do auto-repeat, và nhận diện tổ hợp phím (vd: `Ctrl+C`, `Ctrl+V`).

- `replay.py`
  - Đọc file `log_convert` và phát lại thao tác bằng `pyautogui`.
  - Có thể chọn file đầu vào bằng tham số `-i/--input`.
  - Nhấn **F8** để hủy replay.

## Cài đặt

```bash
pip install pynput pyautogui
```

> Trên Windows 10, nên chạy terminal bằng quyền phù hợp để đảm bảo hook input hoạt động ổn định.

## Định dạng log thô (`raw_log_*.json`)

Mỗi event có các trường:
- `timestamp`
- `event_type`
- `mouse_x`
- `mouse_y`
- `key`
- `button`
- `scroll_delta`

Ví dụ:

```json
{
  "timestamp": 0.532,
  "event_type": "mouse_click",
  "mouse_x": 530,
  "mouse_y": 410,
  "key": null,
  "button": "left",
  "scroll_delta": null
}
```

## Định dạng log replay (`log_convert_*.json`)

Ví dụ:

```json
[
  {"action": "move", "x": 530, "y": 410, "delay": 0.2},
  {"action": "click", "button": "left", "delay": 0.0},
  {"action": "hotkey", "keys": ["ctrl", "c"], "delay": 0.1}
]
```

## Hướng dẫn sử dụng

### 1) Record (và tự convert)

```bash
python record.py
```

- Chương trình bắt đầu ghi thao tác.
- Nhấn **F8** để dừng.
- Kết quả sau khi dừng sẽ là 2 file mới có timestamp.

### 2) Convert thủ công (tùy chọn)

```bash
python convert.py -i raw_log_20260101_120000.json
```

Hoặc chỉ định file đầu ra:

```bash
python convert.py -i raw_log_20260101_120000.json -o log_convert_custom.json
```

### 3) Replay

Replay mặc định (tự lấy file `log_convert_*.json` mới nhất):

```bash
python replay.py
```

Replay từ file cụ thể:

```bash
python replay.py -i log_convert_20260101_120000.json
```

- Chương trình chờ 3 giây trước khi chạy.
- Nhấn **F8** để hủy replay.
- Bật `pyautogui.FAILSAFE`: di chuyển chuột vào góc màn hình để dừng khẩn cấp.

## Lưu ý an toàn

- Replay có thể điều khiển chuột/bàn phím thật trên máy.
- Nên test trên môi trường an toàn trước khi dùng trên máy chính.

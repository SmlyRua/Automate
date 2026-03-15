# Automate

Công cụ nhỏ để **ghi lại thao tác chuột + bàn phím** và **phát lại** trên Windows 10.

## Cài đặt

```bash
pip install pynput
```

## Cách dùng

### 1) Record (mỗi lần tạo file log mới)

```bash
python input_macro.py record
```

- Mặc định log sẽ nằm trong thư mục `logs/`.
- Tên file tự động theo timestamp, ví dụ: `logs/input_log_20260315_203455_123456.json`.
- Nhấn **F8** để dừng record.
- Tên file có cả microseconds để tránh trùng tên khi record liên tiếp rất nhanh.

Tuỳ chọn:

```bash
python input_macro.py record --output-dir my_logs --prefix office_task
```

Ví dụ trên sẽ tạo file kiểu `my_logs/office_task_YYYYmmdd_HHMMSS_microseconds.json`.

### 2) Replay

```bash
python input_macro.py replay -i logs/input_log_20260315_203455_123456.json --speed 1.0
```

- Tool chờ 3 giây trước khi replay để bạn chuyển sang cửa sổ mục tiêu.
- Nhấn **ESC** để ngắt replay giữa chừng.
- `--speed 2.0` sẽ chạy nhanh gấp đôi.
- Trong replay, nếu log có chứa phím `Esc`, script vẫn replay bình thường (không tự ngắt do chính input giả lập).

## Theo yêu cầu mới đã chỉnh trong code

- Mỗi lần record luôn tạo **file log mới** (không ghi đè một file cố định).
- Với chuột chỉ log các hành động:
  - `left click`
  - `middle click`
  - `right click`
  - `scroll`
- **Không log mouse move** để log gọn và đúng yêu cầu.
- Đã xử lý nguyên nhân dễ gây cảm giác duplicate ở click:
  - `pynput` trả về callback click 2 lần (press/release).
  - Script chỉ lưu 1 lần tại thời điểm `pressed=True`.

## Lưu ý

- Chỉ dùng trên máy và ứng dụng bạn có quyền kiểm soát.
- Nếu app mục tiêu chạy quyền admin, hãy mở terminal quyền admin để hook/replay ổn định hơn.

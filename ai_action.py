# Kiểm tra taskbar đã có chrome hoạt động chưa
import win32gui
import win32process
import psutil
import json

import auto_computer

def is_chrome_active():
    hwnd = win32gui.GetForegroundWindow()  # lấy window đang foreground

    if hwnd == 0:
        return False

    _, pid = win32process.GetWindowThreadProcessId(hwnd)  # lấy process id

    process = psutil.Process(pid)

    return process.name().lower().__contains__("chrome")
# Mở App nếu chưa, Click nếu rồi
goal = "mở trình duyệt chrome"
#Screen => Request
if is_chrome_active():
    #Request: Tìm cho tôi vị trí chrome đang hoạt đông ở dưới taskbar
    response = "json"
    data = json.loads(response)
    auto_computer.double_click(data["x"],data["y"],data["button"])
else:
    print("Chrome không active")
# Di chuyển đến trang web
# Kiểm tra đăng nhập
# Lướt Feed
# Comment
# Like
# Share
# Inbox
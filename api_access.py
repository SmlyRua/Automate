import os
from google import genai
from PIL import Image
from google.genai import types

import config_user

def request_google(prompt, image_path=None):
    # 1. Khởi tạo Client
    client = genai.Client(api_key=config_user.GOOGLE_APIKEY)

    # 2. Khởi tạo danh sách contents với prompt (luôn luôn có)
    contents = [prompt]

    # 3. Kiểm tra nếu có đường dẫn ảnh thì chèn thêm object ảnh vào list
    if image_path and os.path.exists(image_path):
        try:
            img = Image.open(image_path)
            contents.append(img)
            print(f"--- Đang gửi Request: [Văn bản + Ảnh] ---")
        except Exception as e:
            return f"Lỗi khi mở file ảnh: {e}"
    else:
        print("--- Đang gửi Request: [Chỉ Văn bản] ---")

    # 4. Ép kiểu MIME type JSON
    config_type = {"response_mime_type": "application/json",}

    # 5. Thực hiện gọi API
    try:
        response = client.models.generate_content(
            model=config_user.GOOGLE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json")
        )
        return response.text
    except Exception as e:
        return f"Lỗi API: {str(e)}"
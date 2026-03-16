import api_access
import auto_computer
import json

def main():
    print("--- Chat ---")
    user_prompt = input("Nhập câu hỏi của bạn:\n")

    img_input = input("Nhập đường dẫn ảnh (để trống nếu không có ảnh):\n").strip()
    # Nếu img_input trống, nó sẽ truyền None
    path_to_send = img_input if img_input else None

    schema_prompt = auto_computer.planer(user_prompt)
    print(schema_prompt)

    require = input("nêu không muốn tiếp tục thì nhập ko\n")
    if require == "ko":
        return

    response = api_access.request_google(schema_prompt,path_to_send)
    print(response)

    require = input("nêu không muốn tiếp tục thì nhập ko\n")
    if require == "ko":
        return

    final = auto_computer.execute(json.loads(response))
    print(final)

if __name__ == '__main__':
    main()
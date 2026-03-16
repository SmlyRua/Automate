import pyautogui
import inspect
import json

from typing_extensions import SupportsInt

import api_access

# tránh lỗi khi chuột di chuyển vào góc màn hình
pyautogui.FAILSAFE = True

# delay mặc định giữa các lệnh
pyautogui.PAUSE = 0.1

actions = {}

def register(name):
    def wrapper(func):
        actions[name] = func
        return func
    return wrapper

# ==========================================================
# MOUSE CONTROL
# ==========================================================

@register("mouse_move")
def mouse_move(x:SupportsInt, y:SupportsInt, duration:float = 0):
    """
    di chuyển chuột tới tọa độ
    x,y = vị trí màn hình
    duration = thời gian di chuyển
    """
    pyautogui.moveTo(x=x, y=y, duration=duration)
    return {"status": "success"}

@register("mouse_drag")
def mouse_drag(x:SupportsInt, y:SupportsInt, duration:float = 0):
    pyautogui.dragTo(x=x, y=y, duration=duration)
    return {"status": "success"}

@register("mouse_click")
def mouse_click(x:SupportsInt, y:SupportsInt, button:str = "left", duration:float = 0):
    pyautogui.click(x=x,y=y,button=button,duration=duration)
    return {"status": "success"}

@register("mouse_double_click")
def mouse_double_click(x:SupportsInt,y:SupportsInt,interval:float = 0,duration:float = 0,button:str = "left"):
    pyautogui.doubleClick(x=x,y=y,interval=interval,duration=duration,button=button)
    return {"status": "success"}
    return {"status": "success"}

@register("mouse_scroll")
def mouse_scroll(clicks:float, duration:float = 0):
    """
    scroll chuột
    clicks > 0 = scroll up
    clicks < 0 = scroll down
    """
    pyautogui.scroll(clicks = clicks)
    return {"status": "success"}

# ==========================================================
# KEYBOARD CONTROL
# ==========================================================

@register("write_content")
def write_content(content:str, interval:float = 0):
    """
    gõ văn bản
    interval = delay giữa các ký tự
    """
    pyautogui.write(message=content, interval=interval)
    return {"status": "success"}

@register("press_key")
def press_key(key:str):
    pyautogui.press(key)
    return {"status": "success"}

@register("hold_key")
def hold_key(key:str):
    pyautogui.keyDown(key)
    return {"status": "success"}

@register("release_key")
def release_key(key:str):
    pyautogui.keyUp(key)
    return {"status": "success"}

@register("copy_content")
def copy_content():
    pyautogui.hotkey("ctrl", "c")
    return {"status": "success"}

@register("paste_content")
def paste_content():
    pyautogui.hotkey("ctrl", "v")
    return {"status": "success"}

def execute(actions_json):
    results = []
    for action_json in actions_json:
        action = action_json["action"]
        args = action_json["args"]

        if action not in actions:
            results.append({
                "status": "error",
                "message": f"unknown {action}"
            })
            continue
        try:
            result = actions[action](**args)
            results.append({
                "action": action,
                "result": result
            })
        except Exception as e:
            results.append({
                "action": action,
                "message": str(e)
            })
    return results

def actions_schema():
    schema = []

    for action, func in actions.items():
        sig = inspect.signature(func)

        params = {}

        for name, param in sig.parameters.items():
            if param.annotation != inspect._empty:
                param_type = param.annotation.__name__
            else:
                param_type = "any"

            params[name] = param_type

        schema.append({
            "action": action,
            "args": params
        })

    return schema

def planer(goal):
    prompt = f"""
You are an AI that converts a desktop screenshot into a sequence of computer control actions.

Environment:
- Screen resolution: 1920x1080
- The screenshot represents the current desktop state.
- The user wants to automate actions using pyautogui.

Task:
- Analyze the screenshot and determine the exact sequence of actions required to achieve the following goal

Goal:
{goal}

Available actions:

Output Rules:
- Output ONLY JSON objects.
- Do NOT include explanations.
- Actions must follow schemas below:
{json.dumps(actions_schema())}
"""
    return prompt
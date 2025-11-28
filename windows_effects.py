import os
from ctypes import windll, c_int, byref, sizeof, Structure, POINTER

# --- Windows 毛玻璃效果 ---
class ACCENT_POLICY(Structure):
    _fields_ = [("AccentState", c_int), 
                ("AccentFlags", c_int), 
                ("GradientColor", c_int), 
                ("AnimationId", c_int)]

class WINDOWCOMPOSITIONATTRIBDATA(Structure):
    _fields_ = [("Attribute", c_int), 
                ("Data", POINTER(ACCENT_POLICY)), 
                ("SizeOfData", c_int)]

def enable_acrylic(hwnd):
    try:
        policy = ACCENT_POLICY()
        policy.AccentState = 4
        policy.GradientColor = 0xCCF1F8E9  # 自然清新主题的背景色
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = byref(policy)
        data.SizeOfData = sizeof(policy)
        windll.user32.SetWindowCompositionAttribute(int(hwnd), byref(data))
    except:
        pass

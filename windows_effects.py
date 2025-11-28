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

def enable_acrylic(hwnd, theme):
    """根据当前主题调整毛玻璃颜色"""
    try:
        policy = ACCENT_POLICY()
        policy.AccentState = 4  # 启用毛玻璃效果
        
        # 根据主题动态调整玻璃颜色（ARGB格式）
        if theme == 'dark':
            policy.GradientColor = 0xCC1E2126  # 深色主题背景色（带透明度）
        else:
            policy.GradientColor = 0xCCF1F8E9  # 浅色主题背景色（带透明度）
            
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = byref(policy)
        data.SizeOfData = sizeof(policy)
        windll.user32.SetWindowCompositionAttribute(int(hwnd), byref(data))
    except Exception as e:
        print(f"毛玻璃效果启用失败: {e}")

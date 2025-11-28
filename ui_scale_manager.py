# --- 屏幕适配系统 ---
class UIScaleManager:
    def __init__(self):
        # 基准分辨率 (1920x1080)
        self.base_width = 1920
        self.base_height = 1080
        self.base_font_size = 14
        self.base_icon_size = 24
        self.base_padding = 10
        self.base_margin = 8

    def get_scale_factor(self, screen_width, screen_height):
        # 使用对角线作为缩放基准
        base_diag = (self.base_width ** 2 + self.base_height ** 2) ** 0.5
        current_diag = (screen_width ** 2 + screen_height ** 2) ** 0.5
        scale_factor = current_diag / base_diag
        # 限制缩放范围
        return max(0.8, min(scale_factor, 1.5))

    def get_scaled_font_size(self, screen_width, screen_height):
        scale_factor = self.get_scale_factor(screen_width, screen_height)
        return int(self.base_font_size * scale_factor)

    def get_scaled_icon_size(self, screen_width, screen_height):
        scale_factor = self.get_scale_factor(screen_width, screen_height)
        return int(self.base_icon_size * scale_factor)

    def get_scaled_padding(self, screen_width, screen_height, base_padding=None):
        if base_padding is None:
            base_padding = self.base_padding
        scale_factor = self.get_scale_factor(screen_width, screen_height)
        return int(base_padding * scale_factor)

    def get_scaled_margin(self, screen_width, screen_height, base_margin=None):
        if base_margin is None:
            base_margin = self.base_margin
        scale_factor = self.get_scale_factor(screen_width, screen_height)
        return int(base_margin * scale_factor)

    def get_scaled_size(self, screen_width, screen_height, base_size):
        scale_factor = self.get_scale_factor(screen_width, screen_height)
        return int(base_size * scale_factor)

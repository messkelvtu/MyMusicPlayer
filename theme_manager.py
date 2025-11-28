# --- 主题系统 ---
class ThemeManager:
    def __init__(self):
        self.themes = {
            'light': {
                'primary': '#4CAF50',
                'primary-light': '#81C784',
                'primary-dark': '#388E3C',
                'secondary': '#88C34A',
                'background': '#F1F8E9',
                'surface': '#FFFFFF',
                'card': '#FFFFFF',
                'error': '#E94560',
                'text_primary': '#185E20',
                'text_secondary': '#4CAF50',
                'text_tertiary': '#81C784',
                'text_disabled': '#A0AEC0',
                'border': '#C8E6C9',
                'hover': 'rgba(76, 175, 80, 0.08)',
                'selected': 'rgba(76, 175, 80, 0.15)',
                'shadow': 'rgba(0, 0, 0, 0.1)'
            },
            'dark': {  # 新增深色主题
                'primary': '#66BB6A',
                'primary-light': '#81C784',
                'primary-dark': '#388E3C',
                'secondary': '#43A047',
                'background': '#1E2126',
                'surface': '#2D3035',
                'card': '#2D3035',
                'error': '#EF5350',
                'text_primary': '#E8F5E9',
                'text_secondary': '#A5D6A7',
                'text_tertiary': '#81C784',
                'text_disabled': '#757575',
                'border': '#37474F',
                'hover': 'rgba(102, 187, 106, 0.1)',
                'selected': 'rgba(102, 187, 106, 0.2)',
                'shadow': 'rgba(0, 0, 0, 0.3)'
            }
        }
        self.current_theme = 'light'
        self.theme_changed = []  # 主题变更回调函数列表

    def get_theme(self):
        return self.themes[self.current_theme]

    def switch_theme(self, theme_name):
        if theme_name in self.themes:
            self.current_theme = theme_name
            # 触发所有注册的回调函数
            for callback in self.theme_changed:
                callback()
            return True
        return False

    def register_callback(self, callback):
        """注册主题变更时的回调函数（用于更新UI）"""
        self.theme_changed.append(callback)

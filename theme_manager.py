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
            }
        }
        self.current_theme = 'light'

    def get_theme(self):
        return self.themes[self.current_theme]

    def switch_theme(self, theme_name):
        if theme_name in self.themes:
            self.current_theme = theme_name
            return True
        return False

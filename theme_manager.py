from PyQt5.QtCore import QObject, pyqtSignal

class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)  # 主题切换信号

    def __init__(self):
        super().__init__()
        self.current_theme = "light"  # 默认浅色主题

    def switch_theme(self, theme):
        """切换主题（light/dark）"""
        if theme in ["light", "dark"]:
            self.current_theme = theme
            self.theme_changed.emit(theme)

    def generate_stylesheet(self):
        """生成全局美化样式表"""
        if self.current_theme == "dark":
            bg_gradient = "#0F172A linear-gradient(to bottom, #0F172A, #1E293B)"
            sidebar_bg = "#1E293B"
            card_bg = "#27374D"
            text_title = "#F8FAFC"
            text_normal = "#E2E8F0"
            text_secondary = "#94A3B8"
            border_color = "#334155"
        else:
            bg_gradient = "#F8FAFC linear-gradient(to bottom, #F8FAFC, #EEF2FF)"
            sidebar_bg = "#FFFFFF"
            card_bg = "#FFFFFF"
            text_title = "#1E293B"
            text_normal = "#475569"
            text_secondary = "#94A3B8"
            border_color = "#E2E8F0"

        # 主色调：柔和蓝紫色（现代感强，不刺眼）
        primary = "#6366F1"
        primary_light = "#A5B4FC"
        primary_dark = "#4F46E5"

        return f"""
        /* 全局重置 */
        * {{
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            margin: 0;
            padding: 0;
        }}

        /* 主窗口 */
        QMainWindow {{
            background: {bg_gradient};
            border: none;
        }}

        /* 侧边栏容器 */
        QWidget#Sidebar {{
            background-color: {sidebar_bg};
            border-right: 1px solid {border_color};
            padding: 16px 0;
            min-width: 60px;
            max-width: 200px;
        }}

        /* 侧边栏按钮 */
        QPushButton#SidebarButton {{
            background-color: transparent;
            color: {text_normal};
            font-size: 14px;
            padding: 12px 16px;
            border-radius: 8px;
            text-align: left;
            border: none;
            transition: all 0.3s ease;
        }}
        QPushButton#SidebarButton:hover {{
            background-color: rgba(99, 102, 241, 0.1);
            color: {primary};
            transform: translateY(-2px);
        }}
        QPushButton#SidebarButton:pressed {{
            background-color: rgba(99, 102, 241, 0.2);
            transform: translateY(0);
        }}
        QPushButton#SidebarButton:checked {{
            background-color: rgba(99, 102, 241, 0.2);
            color: {primary};
            font-weight: 500;
        }}

        /* 卡片容器（主内容区模块） */
        QWidget#Card {{
            background-color: {card_bg};
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            padding: 16px;
            margin: 8px;
            transition: box-shadow 0.3s ease;
        }}
        QWidget#Card:hover {{
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }}

        /* 标题文本 */
        QLabel#TitleLabel {{
            color: {text_title};
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
        }}

        /* 播放控制按钮（上一曲/下一曲） */
        QPushButton#PlayControlButton {{
            background-color: transparent;
            color: {text_normal};
            font-size: 20px;
            border: none;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            transition: all 0.3s ease;
        }}
        QPushButton#PlayControlButton:hover {{
            color: {primary};
            background-color: rgba(99, 102, 241, 0.1);
        }}

        /* 播放/暂停按钮（核心突出） */
        QPushButton#PlayPauseButton {{
            background: {primary} linear-gradient(to right, {primary}, {primary_dark});
            color: white;
            border-radius: 50%;
            width: 48px;
            height: 48px;
            font-size: 24px;
            border: none;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
            transition: all 0.3s ease;
        }}
        QPushButton#PlayPauseButton:hover {{
            transform: scale(1.05);
            box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
        }}
        QPushButton#PlayPauseButton:pressed {{
            transform: scale(0.98);
        }}

        /* 进度条 */
        QSlider::groove:horizontal {{
            height: 4px;
            background-color: {text_secondary};
            border-radius: 2px;
            margin: 0 4px;
        }}
        QSlider::sub-page:horizontal {{
            background: {primary} linear-gradient(to right, {primary_light}, {primary});
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            width: 12px;
            height: 12px;
            background-color: white;
            border: 2px solid {primary};
            border-radius: 50%;
            margin: -4px 0;
            transition: all 0.2s ease;
        }}
        QSlider::handle:horizontal:hover {{
            width: 14px;
            height: 14px;
            margin: -5px 0;
            box-shadow: 0 0 8px rgba(99, 102, 241, 0.5);
        }}
        QSlider::handle:horizontal:pressed {{
            background-color: {primary_dark};
            border-color: {primary_dark};
        }}

        /* 列表/表格 */
        QListWidget, QTableWidget {{
            background-color: transparent;
            border: none;
            gridline-color: {border_color};
            alternate-background-color: transparent;
        }}
        QListWidget::item, QTableWidget::item {{
            height: 36px;
            color: {text_normal};
            padding: 0 12px;
            border-radius: 8px;
        }}
        QListWidget::item:hover, QTableWidget::item:hover {{
            background-color: rgba(0, 0, 0, 0.03);
        }}
        QListWidget::item:selected, QTableWidget::item:selected {{
            background-color: rgba(99, 102, 241, 0.15);
            color: {primary};
            font-weight: 500;
        }}
        QHeaderView::section {{
            background-color: transparent;
            color: {text_secondary};
            border: none;
            border-bottom: 1px solid {border_color};
            padding: 8px 12px;
            font-size: 12px;
        }}

        /* 歌词标签 */
        QLabel#LyricLabel {{
            color: {text_secondary};
            font-size: 16px;
            margin: 8px 0;
            transition: color 0.3s ease;
        }}
        QLabel#CurrentLyricLabel {{
            font-size: 20px;
            font-weight: 600;
            margin: 12px 0;
            background: linear-gradient(to right, {primary}, {primary_dark});
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-shadow: 0 2px 4px rgba(99, 102, 241, 0.1);
        }}

        /* 输入框 */
        QLineEdit {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 8px 12px;
            color: {text_normal};
            transition: all 0.3s ease;
        }}
        QLineEdit:focus {{
            border-color: {primary};
            outline: none;
            box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
        }}

        /* 对话框 */
        QDialog {{
            background: {bg_gradient};
            border-radius: 12px;
            border: none;
        }}
        QDialogButtonBox QPushButton {{
            padding: 8px 16px;
            border-radius: 8px;
            border: none;
            background-color: {card_bg};
            color: {text_normal};
            transition: all 0.3s ease;
        }}
        QDialogButtonBox QPushButton:hover {{
            background-color: rgba(99, 102, 241, 0.1);
            color: {primary};
        }}
        QDialogButtonBox QPushButton:default {{
            background-color: {primary};
            color: white;
        }}

        /* 音量滑块（紧凑版） */
        QSlider#VolumeSlider::groove:horizontal {{
            height: 2px;
        }}
        QSlider#VolumeSlider::handle:horizontal {{
            width: 10px;
            height: 10px;
        }}
        """

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QMenu, QColorDialog, QFontDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QGraphicsDropShadowEffect

from ui_scale_manager import UIScaleManager

class DesktopLyricWindow(QWidget):
    def __init__(self, scale_manager=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 获取屏幕尺寸和缩放管理器
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        self.scale_manager = scale_manager if scale_manager else UIScaleManager()

        # 设置窗口尺寸
        window_width = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 1200)
        window_height = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 180)
        self.resize(window_width, window_height)

        self.color = QColor(76, 175, 80)  # 主题绿色
        base_font_size = self.scale_manager.get_scaled_font_size(screen_size.width(), screen_size.height())

        self.font = QFont("Segoe UI", base_font_size + 22, QFont.Bold)
        self.locked = False

        layout = QVBoxLayout(self)
        self.labels = [QLabel("") for _ in range(3)]

        for label in self.labels:
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)

        self.update_style()
        self.move(100, 800)

    def update_style(self):
        shadow_color = QColor(0, 0, 0, 100)

        for i, label in enumerate(self.labels):
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(12)
            effect.setColor(shadow_color)
            effect.setOffset(0, 0)
            label.setGraphicsEffect(effect)

            font = QFont(self.font)
            if i == 1:  # 当前歌词
                font_size = self.font.pointSize()
            else:  # 上下歌词
                font_size = int(self.font.pointSize() * 0.6)
            font.setPointSize(font_size)

            color = self.color.name() if i == 1 else f"rgba({self.color.red()},{self.color.green()},{self.color.blue()},100)"
            label.setStyleSheet(f"color: {color}")
            label.setFont(font)

    def set_text(self, prev, current, next_):
        self.labels[0].setText(prev)
        self.labels[1].setText(current)
        self.labels[2].setText(next_)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.locked:
            self.move(event.globalPos() - self.drag_position)

    def show_context_menu(self, position):
        menu = QMenu()
        menu.addAction("颜色", self.change_color)
        menu.addAction("字体", self.change_font)
        menu.addAction("锁定/解锁", self.toggle_lock)
        menu.addAction("✗ 关闭", self.hide)
        menu.exec_(position)

    def change_color(self):
        color = QColorDialog.getColor(self.color, self)
        if color.isValid():
            self.color = color
            self.update_style()

    def change_font(self):
        font, ok = QFontDialog.getFont(self.font, self)
        if ok:
            self.font = font
            self.update_style()

    def toggle_lock(self):
        self.locked = not self.locked

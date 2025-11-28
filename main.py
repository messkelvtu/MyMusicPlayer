import sys
import os
import json
import shutil
import random
import re
import urllib.request
import urllib.parse
import time
from ctypes import windll, c_int, byref, sizeof, Structure, POINTER
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QFileDialog, QFrame, QAbstractItemView, QCheckBox,
                             QGraphicsDropShadowEffect, QInputDialog, QMessageBox,
                             QFontDialog, QMenu, QAction, QSlider, QDialog, QRadioButton,
                             QComboBox, QLineEdit, QTabWidget, QSpinBox, QColorDialog,
                             QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget,
                             QSplitter, QGroupBox, QScrollArea, QSizePolicy, QProgressBar)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QCoreApplication, QTimer, QPropertyAnimation, QEasingCurve, QRect, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QIcon, QPixmap, QCursor, QFontDatabase
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# --- 核心配置 ---
os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"
try:
    import yt_dlp
except ImportError:
    yt_dlp = None

CONFIG_FILE = "config.json"
METADATA_FILE = "metadata.json"
HISTORY_FILE = "history.json"
OFFSET_FILE = "offsets.json"

# --- Windows 毛玻璃效果 ---
class ACCENT_POLICY(Structure):
    _fields_ = [("AccentState", c_int), ("AccentFlags", c_int), ("GradientColor", c_int), ("AnimationId", c_int)]

class WINDOWCOMPOSITIONATTRIBDATA(Structure):
    _fields_ = [("Attribute", c_int), ("Data", POINTER(ACCENT_POLICY)), ("SizeOfData", c_int)]

def enable_acrylic(hwnd):
    try:
        policy = ACCENT_POLICY()
        policy.AccentState = 4
        policy.GradientColor = 0xCCF1F8E9  # 自然清新主题的背景色
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = POINTER(ACCENT_POLICY)(policy)
        data.SizeOfData = sizeof(policy)
        windll.user32.SetWindowCompositionAttribute(int(hwnd), byref(data))
    except:
        pass

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

    # --- 修复部分 START: 允许传入自定义 padding 和 margin ---
    def get_scaled_padding(self, screen_width, screen_height, padding=None):
        scale_factor = self.get_scale_factor(screen_width, screen_height)
        base = padding if padding is not None else self.base_padding
        return int(base * scale_factor)

    def get_scaled_margin(self, screen_width, screen_height, margin=None):
        scale_factor = self.get_scale_factor(screen_width, screen_height)
        base = margin if margin is not None else self.base_margin
        return int(base * scale_factor)
    # --- 修复部分 END ---

    def get_scaled_size(self, screen_width, screen_height, base_size):
        scale_factor = self.get_scale_factor(screen_width, screen_height)
        return int(base_size * scale_factor)

# --- 主题系统 ---
class ThemeManager:
    def __init__(self):
        self.themes = {
            'light': {
                'primary': '#4CAF50',
                'primary-light': '#81C784',
                'primary-dark': '#388E3C',
                'secondary': '#8BC34A',
                'background': '#F1F8E9',
                'surface': '#FFFFFF',
                'card': '#FFFFFF',
                'error': '#E94560',
                'text_primary': '#1B5E20',
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

# --- 样式表生成器 ---
def generate_stylesheet(theme, scale_manager=None, screen_width=1920, screen_height=1080):
    if scale_manager is None:
        scale_manager = UIScaleManager()

    # 获取缩放后的尺寸
    font_size = scale_manager.get_scaled_font_size(screen_width, screen_height)
    padding = scale_manager.get_scaled_padding(screen_width, screen_height)
    margin = scale_manager.get_scaled_margin(screen_width, screen_height)
    icon_size = scale_manager.get_scaled_icon_size(screen_width, screen_height)

    button_height = scale_manager.get_scaled_size(screen_width, screen_height, 40)
    input_height = scale_manager.get_scaled_size(screen_width, screen_height, 44)
    table_row_height = scale_manager.get_scaled_size(screen_width, screen_height, 50)

    return f"""
    /* 全局样式 */
    QMainWindow {{
        background: {theme['background']};
        color: {theme['text_primary']};
    }}

    QWidget {{
        font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
        color: {theme['text_primary']};
        font-size: {font_size}px;
    }}

    /* 侧边栏 */
    QFrame#Sidebar {{
        background-color: {theme['surface']};
        border-right: 1px solid {theme['border']};
    }}

    QLabel#Logo {{
        font-size: {font_size + 10}px;
        font-weight: 900;
        color: {theme['primary']};
        padding: {padding * 3}px {padding * 2}px;
        letter-spacing: 1px;
        border-bottom: 1px solid {theme['border']};
    }}

    QLabel#SectionTitle {{
        font-size: {font_size - 2}px;
        color: {theme['text_secondary']};
        padding: {padding * 2}px {padding * 2.5}px {padding}px {padding * 2.5}px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* 导航按钮 - 边框强调方案 */
    QPushButton.NavBtn {{
        background: transparent;
        border: none;
        text-align: left;
        padding: {padding}px {padding * 2.5}px;
        font-size: {font_size}px;
        color: {theme['text_secondary']};
        border-radius: 8px;
        margin: 2px {margin * 1.5}px;
        border-left: 3px solid transparent;
        min-height: {button_height}px;
    }}

    QPushButton.NavBtn:hover {{
        background-color: {theme['hover']};
        color: {theme['primary']};
        border-left: 3px solid {theme['primary']};
    }}

    QPushButton.NavBtn:checked {{
        background: {theme['selected']};
        color: {theme['primary']};
        font-weight: 600;
        border-left: 3px solid {theme['primary']};
    }}

    /* 下载按钮 - 渐变方案 */
    QPushButton#DownloadBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme['primary']}, stop:1 {theme['primary-light']});
        color: white;
        font-weight: bold;
        border-radius: 20px;
        text-align: center;
        margin: {margin * 2}px {margin * 2.5}px;
        padding: {padding}px;
        border: none;
        font-size: {font_size}px;
        min-height: {button_height}px;
    }}

    QPushButton#DownloadBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme['primary-dark']}, stop:1 {theme['primary']});
    }}

    /* 工具按钮 - 边框强调方案 */
    QPushButton.ToolBtn {{
        background: transparent;
        border: none;
        text-align: left;
        padding: {padding}px {padding * 2.5}px;
        font-size: {font_size}px;
        color: {theme['text_secondary']};
        border-radius: 8px;
        margin: 2px {margin * 1.5}px;
        border-left: 3px solid transparent;
        min-height: {button_height}px;
    }}

    QPushButton.ToolBtn:hover {{
        background: {theme['hover']};
        color: {theme['primary']};
        border-left: 3px solid {theme['primary']};
    }}

    /* 搜索框 */
    QLineEdit#SearchBox {{
        background-color: {theme['background']};
        border: 1px solid {theme['border']};
        border-radius: 20px;
        color: {theme['text_primary']};
        padding: {padding}px {padding * 2}px;
        font-size: {font_size}px;
        min-height: {input_height}px;
    }}

    QLineEdit#SearchBox:focus {{
        background-color: white;
        border: 1px solid {theme['primary']};
    }}

    /* 表格样式 */
    QHeaderView::section {{
        background-color: {theme['background']};
        border: none;
        border-bottom: 1px solid {theme['border']};
        padding: {padding}px;
        font-weight: bold;
        color: {theme['text_secondary']};
        font-size: {font_size}px;
        min-height: {table_row_height}px;
    }}

    QTableWidget {{
        background-color: transparent;
        border: none;
        outline: none;
        gridline-color: transparent;
        selection-background-color: transparent;
        border: 1px solid {theme['border']};
        border-radius: 12px;
        font-size: {font_size}px;
    }}

    QTableWidget::item {{
        padding: {padding}px;
        border-bottom: 1px solid {theme['border']};
        color: {theme['text_primary']};
        min-height: {table_row_height}px;
    }}

    QTableWidget::item:hover {{
        background-color: {theme['hover']};
    }}

    QTableWidget::item:selected {{
        background-color: {theme['selected']};
        color: {theme['primary']};
        border-radius: 6px;
    }}

    /* 歌词页面 */
    QWidget#LyricsPage {{
        background-color: {theme['background']};
    }}

    QListWidget#BigLyric {{
        background: transparent;
        border: none;
        outline: none;
        font-size: {font_size + 10}px;
        color: {theme['text_secondary']};
        font-weight: 600;
    }}

    QListWidget#BigLyric::item {{
        padding: {padding * 2}px;
        text-align: center;
        min-height: {table_row_height + 20}px;
    }}

    QListWidget#BigLyric::item:selected {{
        color: {theme['primary']};
        font-size: {font_size + 18}px;
        font-weight: bold;
    }}

    /* 右侧面板 */
    QFrame#RightPanel {{
        background-color: {theme['surface']};
        border-left: 1px solid {theme['border']};
    }}

    QListWidget#LyricPanel {{
        background: transparent;
        border: none;
        outline: none;
        font-size: {font_size}px;
        color: {theme['text_secondary']};
        border: 1px solid {theme['border']};
        border-radius: 12px;
    }}

    QListWidget#LyricPanel::item {{
        padding: {padding}px 0;
        text-align: center;
        min-height: {table_row_height - 10}px;
    }}

    QListWidget#LyricPanel::item:selected {{
        color: {theme['primary']};
        font-size: {font_size + 2}px;
        font-weight: bold;
        background: transparent;
    }}

    /* 播放控制栏 */
    QFrame#PlayerBar {{
        background-color: {theme['surface']};
        border-top: 1px solid {theme['border']};
    }}

    /* 播放按钮 - 渐变方案 */
    QPushButton#PlayBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme['primary']}, stop:1 {theme['primary-light']});
        color: white;
        border: none;
        border-radius: 25px;
        font-size: {font_size + 6}px;
        min-width: {icon_size + 32}px;
        min-height: {icon_size + 32}px;
    }}

    QPushButton#PlayBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme['primary-dark']}, stop:1 {theme['primary']});
    }}

    /* 控制按钮 - 边框强调方案 */
    QPushButton.CtrlBtn {{
        background: transparent;
        border: 1px solid transparent;
        font-size: {font_size + 4}px;
        color: {theme['text_secondary']};
        min-width: {icon_size + 16}px;
        min-height: {icon_size + 16}px;
        border-radius: 6px;
    }}

    QPushButton.CtrlBtn:hover {{
        color: {theme['primary']};
        background: {theme['hover']};
    }}

    /* 偏移按钮 - 边框强调方案 */
    QPushButton.OffsetBtn {{
        background: transparent;
        border: 1px solid {theme['border']};
        color: {theme['text_secondary']};
        padding: {padding}px {padding * 2}px;
        border-radius: 8px;
        font-size: {font_size - 1}px;
        min-height: {button_height - 5}px;
    }}

    QPushButton.OffsetBtn:hover {{
        border: 1px solid {theme['primary']};
        color: {theme['primary']};
        background: {theme['hover']};
    }}

    /* 进度条 */
    QSlider::groove:horizontal {{
        height: {padding / 2}px;
        background: {theme['border']};
        border-radius: 3px;
    }}

    QSlider::handle:horizontal {{
        background: {theme['primary']};
        width: {icon_size - 10}px;
        height: {icon_size - 10}px;
        margin: -{padding / 2}px 0;
        border-radius: {icon_size / 2 - 5}px;
    }}

    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme['primary']}, stop:1 {theme['primary-light']});
        border-radius: 3px;
    }}

    /* 滚动条 */
    QScrollBar:vertical {{
        border: none;
        background: {theme['background']};
        width: {padding}px;
        margin: 0;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical {{
        background: {theme['border']};
        min-height: {icon_size}px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {theme['text_tertiary']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* 歌单列表 */
    QListWidget#CollectionList {{
        background: transparent;
        border: none;
        font-size: {font_size}px;
        color: {theme['text_secondary']};
        outline: none;
    }}

    QListWidget#CollectionList::item {{
        padding: {padding}px {padding * 1.5}px;
        border-left: 2px solid transparent;
        margin: 0 {margin}px;
        border-radius: 8px;
        min-height: {table_row_height - 15}px;
    }}

    QListWidget#CollectionList::item:hover {{
        background: {theme['hover']};
        color: {theme['primary']};
        border-left: 2px solid {theme['primary']};
    }}

    QListWidget#CollectionList::item:selected {{
        background: {theme['selected']};
        color: {theme['primary']};
        font-weight: 600;
    }}

    /* 操作按钮 */
    QPushButton.ActionBtn {{
        background: transparent;
        border: 1px solid {theme['border']};
        color: {theme['text_secondary']};
        padding: {padding}px {padding * 2}px;
        border-radius: 8px;
        font-size: {font_size - 1}px;
        min-height: {button_height - 5}px;
    }}

    QPushButton.ActionBtn:hover {{
        border-color: {theme['primary']};
        color: {theme['primary']};
        background: {theme['hover']};
    }}

    /* 歌词控制按钮 */
    QPushButton.LyricControlBtn {{
        background: transparent;
        border: 1px solid {theme['border']};
        color: {theme['text_secondary']};
        padding: {padding - 2}px {padding * 1.5}px;
        border-radius: 8px;
        font-size: {font_size - 2}px;
        min-height: {button_height - 10}px;
    }}

    QPushButton.LyricControlBtn:hover {{
        border-color: {theme['primary']};
        color: {theme['primary']};
        background: {theme['hover']};
    }}

    /* 歌曲操作按钮 */
    QPushButton.SongActionBtn {{
        background: transparent;
        border: none;
        color: {theme['text_secondary']};
        padding: {padding - 2}px;
        border-radius: 4px;
        font-size: {font_size}px;
        min-width: {icon_size}px;
        min-height: {icon_size}px;
    }}

    QPushButton.SongActionBtn:hover {{
        color: {theme['primary']};
        background: {theme['hover']};
    }}

    /* 对话框样式 */
    QDialog {{
        background: {theme['surface']};
        color: {theme['text_primary']};
        border: 1px solid {theme['border']};
        border-radius: 16px;
        font-size: {font_size}px;
    }}

    QDialog QLabel {{
        color: {theme['text_primary']};
        font-size: {font_size}px;
        padding: {padding / 2}px;
    }}

    QDialog QLineEdit {{
        background: {theme['background']};
        border: 1px solid {theme['border']};
        border-radius: 8px;
        color: {theme['text_primary']};
        padding: {padding}px {padding * 1.5}px;
        font-size: {font_size}px;
        min-height: {input_height}px;
        selection-background-color: {theme['selected']};
    }}

    QDialog QLineEdit:focus {{
        border: 1px solid {theme['primary']};
        background: white;
    }}

    QDialog QCheckBox {{
        color: {theme['text_primary']};
        font-size: {font_size}px;
        spacing: {padding}px;
        min-height: {icon_size}px;
    }}

    QDialog QCheckBox::indicator {{
        width: {icon_size - 6}px;
        height: {icon_size - 6}px;
        border-radius: 4px;
        border: 1px solid {theme['border']};
    }}

    QDialog QCheckBox::indicator:checked {{
        background: {theme['primary']};
        border: 1px solid {theme['primary']};
    }}

    QDialog QPushButton {{
        padding: {padding}px {padding * 2}px;
        border-radius: 8px;
        font-size: {font_size}px;
        font-weight: 600;
        min-height: {button_height}px;
    }}

    QDialog QPushButton[class="primary"] {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme['primary']}, stop:1 {theme['primary-light']});
        color: white;
        border: none;
    }}

    QDialog QPushButton[class="primary"]:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme['primary-dark']}, stop:1 {theme['primary']});
    }}

    QDialog QPushButton[class="outline"] {{
        background: transparent;
        color: {theme['primary']};
        border: 1px solid {theme['primary']};
    }}

    QDialog QPushButton[class="outline"]:hover {{
        background: {theme['hover']};
    }}

    QDialog QTabWidget::pane {{
        border: 1px solid {theme['border']};
        border-radius: 8px;
    }}

    QDialog QTabBar::tab {{
        background: transparent;
        padding: {padding}px {padding * 2}px;
        border: none;
        color: {theme['text_secondary']};
        border-bottom: 2px solid transparent;
        min-height: {button_height}px;
    }}

    QDialog QTabBar::tab:selected {{
        color: {theme['primary']};
        border-bottom: 2px solid {theme['primary']};
    }}

    QDialog QComboBox {{
        background: {theme['background']};
        border: 1px solid {theme['border']};
        border-radius: 8px;
        color: {theme['text_primary']};
        padding: {padding}px {padding * 1.5}px;
        font-size: {font_size}px;
        min-height: {input_height}px;
    }}

    QDialog QComboBox:focus {{
        border: 1px solid {theme['primary']};
    }}

    QDialog QComboBox::drop-down {{
        border: none;
        width: {icon_size}px;
    }}

    QDialog QComboBox::down-arrow {{
        image: none;
        border-left: 1px solid {theme['border']};
        padding: 0 {padding}px;
    }}

    QDialog QSpinBox {{
        background: {theme['background']};
        border: 1px solid {theme['border']};
        border-radius: 8px;
        color: {theme['text_primary']};
        padding: {padding}px {padding * 1.5}px;
        font-size: {font_size}px;
        min-height: {input_height}px;
    }}

    QDialog QSpinBox:focus {{
        border: 1px solid {theme['primary']};
    }}

    /* 分割器样式 */
    QSplitter::handle {{
        background: rgba(76, 175, 80, 0.1);
        width: {padding / 2}px;
        height: {padding / 2}px;
    }}

    /* 分组框样式 */
    QGroupBox {{
        font-weight: bold;
        border: 1px solid {theme['border']};
        border-radius: 8px;
        margin-top: {padding * 1.5}px;
        padding-top: {padding * 1.5}px;
        font-size: {font_size}px;
        color: {theme['text_primary']};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: {padding}px;
        padding: 0 {padding}px;
        color: {theme['text_primary']};
    }}

    /* 进度条样式 */
    QProgressBar {{
        border: 1px solid {theme['border']};
        border-radius: 4px;
        background: {theme['background']};
        text-align: center;
        color: {theme['text_primary']};
        font-size: {font_size - 1}px;
    }}

    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme['primary']}, stop:1 {theme['primary-light']});
        border-radius: 3px;
    }}

    /* 菜单样式 */
    QMenu {{
        background: {theme['surface']};
        color: {theme['text_primary']};
        border: 1px solid {theme['border']};
        border-radius: 8px;
        padding: {padding / 2}px;
        font-size: {font_size}px;
    }}

    QMenu::item {{
        padding: {padding}px {padding * 1.5}px;
        border-radius: 4px;
        min-height: {button_height - 5}px;
    }}

    QMenu::item:selected {{
        background: {theme['selected']};
        color: {theme['primary']};
    }}

    QMenu::separator {{
        height: 1px;
        background: {theme['border']};
        margin: {padding / 2}px {padding}px;
    }}
    """

# --- 辅助函数 ---
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def ms_to_str(ms):
    if not ms:
        return "00:00"
    s = ms // 1000
    return f"{s//60:02}:{s%60:02}"

# --- 功能线程 ---
class LyricListSearchWorker(QThread):
    search_finished = pyqtSignal(list)

    def __init__(self, keyword):
        super().__init__()
        self.keyword = keyword

    def run(self):
        try:
            url = "http://music.163.com/api/search/get/web?csrf_token="
            headers = {'User-Agent': 'Mozilla/5.0'}
            data = urllib.parse.urlencode({
                's': self.keyword,
                'type': 1,
                'offset': 0,
                'total': 'true',
                'limit': 15
            }).encode('utf-8')

            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as f:
                res = json.loads(f.read().decode('utf-8'))

            results = []
            if res.get('result') and res['result'].get('songs'):
                for s in res['result']['songs']:
                    artist = s['artists'][0]['name'] if s['artists'] else "未知"
                    duration = s.get('duration', 0)
                    results.append({
                        'name': s['name'],
                        'artist': artist,
                        'id': s['id'],
                        'duration': duration,
                        'duration_str': ms_to_str(duration)
                    })

            self.search_finished.emit(results)
        except Exception as e:
            print(f"歌词搜索错误: {e}")
            self.search_finished.emit([])

class LyricDownloader(QThread):
    finished_signal = pyqtSignal(str)

    def __init__(self, sid, path):
        super().__init__()
        self.sid = sid
        self.path = path

    def run(self):
        try:
            url = f"http://music.163.com/api/song/lyric?os=pc&id={self.sid}&lv=-1&kv=-1&tv=-1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as f:
                res = json.loads(f.read().decode('utf-8'))

            if 'lrc' in res:
                lrc = res['lrc']['lyric']
                with open(self.path, 'w', encoding='utf-8') as f:
                    f.write(lrc)
                self.finished_signal.emit(lrc)
        except Exception as e:
            print(f"歌词下载错误: {e}")

class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str, str)
    error_signal = pyqtSignal(str)

    def __init__(self, url, path, mode, sp):
        super().__init__()
        self.u = url
        self.p = path
        self.m = mode
        self.sp = sp

    def run(self):
        if not yt_dlp:
            self.error_signal.emit("未安装 yt-dlp，无法下载")
            return

        if not os.path.exists(self.p):
            try:
                os.makedirs(self.p)
            except Exception as e:
                self.error_signal.emit(f"无法创建目录: {e}")
                return

        def progress_hook(d):
            if d['status'] == 'downloading':
                self.progress_signal.emit(f"⬇️ {d.get('_percent_str', '')} {os.path.basename(d.get('filename', ''))[:20]}...")

        opts = {
            'format': 'bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': os.path.join(self.p, '%(title)s.%(ext)s'),
            'overwrites': True,
            'noplaylist': self.m == 'single',
            'playlist_items': str(self.sp) if self.m == 'single' else f"{self.sp}-",
            'progress_hooks': [progress_hook],
            'quiet': True,
            'nocheckcertificate': True,
            'restrictfilenames': False
        }

        try:
            with yt_dlp.YoutubeDL(opts) as y:
                y.download([self.u])
            self.finished_signal.emit(self.p, "")
        except Exception as e:
            self.error_signal.emit(str(e))

# 图标映射
ICONS = {
    "music": "🎵",
    "download": "⬇️",
    "disc": "💿",
    "history": "🕒",
    "heart": "❤️",
    "fire": "🔥",
    "star": "⭐",
    "sync": "🔄",
    "folder_plus": "📁+",
    "truck": "🚚",
    "folder_open": "📂",
    "microphone": "🎤",
    "search": "🔍",
    "edit": "✏️",
    "random": "🔀",
    "play": "▶️",
    "pause": "⏸️",
    "ellipsis": "⋯",
    "step_backward": "⏮️",
    "step_forward": "⏭️",
    "retweet": "🔁",
    "volume": "🔊",
    "sliders": "🎚️",
    "youtube": "📺",
    "save": "💾",
    "check": "✅",
    "text_height": "🔤",
    "palette": "🎨",
    "font": "🔡",
    "align_center": "☰",
    "chevron_down": "⌄",
    "close": "❌",
    "info": "ℹ️",
    "warning": "⚠️",
    "error": "❌"
}

# --- 对话框类 ---
class LyricSearchDialog(QDialog):
    def __init__(self, song_name, duration_ms=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("搜索歌词")

        # 获取屏幕尺寸和缩放管理器
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        self.scale_manager = parent.scale_manager if hasattr(parent, 'scale_manager') else UIScaleManager()
        self.theme_manager = parent.theme_manager if hasattr(parent, 'theme_manager') else ThemeManager()

        # 设置对话框尺寸
        dialog_width = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 700)
        dialog_height = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 500)
        self.resize(dialog_width, dialog_height)

        self.result_id = None
        self.duration_ms = duration_ms

        theme = self.theme_manager.get_theme()
        self.setStyleSheet(generate_stylesheet(theme, self.scale_manager, screen_size.width(), screen_size.height()))

        layout = QVBoxLayout(self)
        layout.setSpacing(self.scale_manager.get_scaled_margin(screen_size.width(), screen_size.height()))
        layout.setContentsMargins(
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2
        )

        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit(song_name)
        self.search_input.setPlaceholderText("输入歌曲名称")
        self.search_button = QPushButton("搜索")
        self.search_button.setProperty("class", "primary")
        self.search_button.clicked.connect(self.search_lyrics)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["歌名", "歌手", "时长", "ID"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.itemDoubleClicked.connect(self.on_item_double_click)
        layout.addWidget(self.result_table)

        # 状态标签
        self.status_label = QLabel("输入关键词...")
        layout.addWidget(self.status_label)

        # 绑定按钮
        button_layout = QHBoxLayout()
        self.bind_button = QPushButton("下载并绑定")
        self.bind_button.setProperty("class", "primary")
        self.bind_button.clicked.connect(self.confirm_bind)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setProperty("class", "outline")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.bind_button)
        layout.addLayout(button_layout)

    def search_lyrics(self):
        keyword = self.search_input.text()
        self.result_table.setRowCount(0)
        self.status_label.setText("搜索中...")

        self.worker = LyricListSearchWorker(keyword)
        self.worker.search_finished.connect(self.on_search_finished)
        self.worker.start()

    def on_search_finished(self, results):
        self.status_label.setText(f"找到 {len(results)} 条")
        self.result_table.setRowCount(len(results))

        for i, result in enumerate(results):
            self.result_table.setItem(i, 0, QTableWidgetItem(result['name']))
            self.result_table.setItem(i, 1, QTableWidgetItem(result['artist']))

            duration_item = QTableWidgetItem(result['duration_str'])
            if abs(result['duration'] - self.duration_ms) < 3000 and self.duration_ms > 0:
                duration_item.setForeground(QColor("#1ECD97"))

            self.result_table.setItem(i, 2, duration_item)
            self.result_table.setItem(i, 3, QTableWidgetItem(str(result['id'])))

    def on_item_double_click(self, item):
        self.result_id = self.result_table.item(item.row(), 3).text()
        self.accept()

    def confirm_bind(self):
        row = self.result_table.currentRow()
        if row >= 0:
            self.result_id = self.result_table.item(row, 3).text()
            self.accept()
        else:
            QMessageBox.warning(self, "提示", "请选择一首歌曲")

class BatchInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑信息")

        # 获取屏幕尺寸和缩放管理器
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        self.scale_manager = parent.scale_manager if hasattr(parent, 'scale_manager') else UIScaleManager()
        self.theme_manager = parent.theme_manager if hasattr(parent, 'theme_manager') else ThemeManager()

        # 设置对话框尺寸
        dialog_width = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 500)
        dialog_height = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 400)
        self.resize(dialog_width, dialog_height)

        theme = self.theme_manager.get_theme()
        self.setStyleSheet(generate_stylesheet(theme, self.scale_manager, screen_size.width(), screen_size.height()))

        layout = QVBoxLayout(self)
        layout.setSpacing(self.scale_manager.get_scaled_margin(screen_size.width(), screen_size.height()))
        layout.setContentsMargins(
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2
        )

        # 歌曲标题
        title_group = QGroupBox("歌曲信息")
        title_layout = QVBoxLayout(title_group)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("歌曲标题")
        title_layout.addWidget(self.title_input)

        # 歌手
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("歌手")
        title_layout.addWidget(self.artist_input)

        # 专辑
        self.album_input = QLineEdit()
        self.album_input.setPlaceholderText("专辑")
        title_layout.addWidget(self.album_input)

        # 年份
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("年份")
        title_layout.addWidget(self.year_input)

        layout.addWidget(title_group)

        # 按钮
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setProperty("class", "outline")
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("保存更改")
        self.save_button.setProperty("class", "primary")
        self.save_button.clicked.connect(self.accept)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

    def get_data(self):
        return (
            self.title_input.text(),
            self.artist_input.text(),
            self.album_input.text(),
            self.year_input.text()
        )

    def set_data(self, title, artist, album, year):
        self.title_input.setText(title)
        self.artist_input.setText(artist)
        self.album_input.setText(album)
        self.year_input.setText(year)

class DownloadDialog(QDialog):
    def __init__(self, parent=None, current_p=1, collections=[]):
        super().__init__(parent)
        self.setWindowTitle("下载")

        # 获取屏幕尺寸和缩放管理器
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        self.scale_manager = parent.scale_manager if hasattr(parent, 'scale_manager') else UIScaleManager()
        self.theme_manager = parent.theme_manager if hasattr(parent, 'theme_manager') else ThemeManager()

        # 设置对话框尺寸
        dialog_width = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 600)
        dialog_height = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 500)
        self.resize(dialog_width, dialog_height)

        theme = self.theme_manager.get_theme()
        self.setStyleSheet(generate_stylesheet(theme, self.scale_manager, screen_size.width(), screen_size.height()))

        layout = QVBoxLayout(self)
        layout.setSpacing(self.scale_manager.get_scaled_margin(screen_size.width(), screen_size.height()))
        layout.setContentsMargins(
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2
        )

        # 视频链接
        url_group = QGroupBox("视频链接")
        url_layout = QVBoxLayout(url_group)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入B站视频链接")
        url_layout.addWidget(self.url_input)
        layout.addWidget(url_group)

        # 标签页
        self.tab_widget = QTabWidget()

        # 下载设置标签页
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setSpacing(self.scale_manager.get_scaled_margin(screen_size.width(), screen_size.height()))

        # 下载模式
        mode_group = QGroupBox("下载模式")
        mode_layout = QVBoxLayout(mode_group)
        self.single_radio = QRadioButton("单曲下载")
        self.playlist_radio = QRadioButton("合集下载")
        self.single_radio.setChecked(True)
        mode_layout.addWidget(self.single_radio)
        mode_layout.addWidget(self.playlist_radio)
        settings_layout.addWidget(mode_group)

        # 保存位置
        location_group = QGroupBox("保存位置")
        location_layout = QVBoxLayout(location_group)
        self.folder_combo = QComboBox()
        self.folder_combo.addItem("根目录", "")
        for collection in collections:
            self.folder_combo.addItem(f"{ICONS['folder_open']} {collection}", collection)
        self.folder_combo.addItem(f"{ICONS['folder_plus']} 新建...", "NEW")
        location_layout.addWidget(self.folder_combo)

        self.new_folder_input = QLineEdit()
        self.new_folder_input.setPlaceholderText("文件夹名称")
        self.new_folder_input.hide()
        location_layout.addWidget(self.new_folder_input)

        self.folder_combo.currentIndexChanged.connect(self.on_folder_combo_changed)
        settings_layout.addWidget(location_group)

        # 预设信息
        preset_group = QGroupBox("预设信息")
        preset_layout = QVBoxLayout(preset_group)
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("预设歌手")
        preset_layout.addWidget(self.artist_input)

        self.album_input = QLineEdit()
        self.album_input.setPlaceholderText("预设专辑")
        preset_layout.addWidget(self.album_input)
        settings_layout.addWidget(preset_group)

        self.tab_widget.addTab(settings_tab, "下载设置")

        # 高级选项标签页
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.addWidget(QLabel("高级选项内容..."))
        self.tab_widget.addTab(advanced_tab, "高级选项")

        layout.addWidget(self.tab_widget)

        # 按钮
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setProperty("class", "outline")
        self.cancel_button.clicked.connect(self.reject)
        self.download_button = QPushButton(f"{ICONS['download']} 开始下载")
        self.download_button.setProperty("class", "primary")
        self.download_button.clicked.connect(self.accept)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.download_button)
        layout.addLayout(button_layout)

    def on_folder_combo_changed(self):
        self.new_folder_input.setVisible(self.folder_combo.currentData() == "NEW")

    def get_data(self):
        mode = "playlist" if self.playlist_radio.isChecked() else "single"
        folder = self.folder_combo.currentData()

        if folder == "NEW":
            folder = self.new_folder_input.text().strip()

        return self.url_input.text(), mode, folder, self.artist_input.text(), self.album_input.text()

class SyncLyricsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("歌词同步")

        # 获取屏幕尺寸和缩放管理器
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        self.scale_manager = parent.scale_manager if hasattr(parent, 'scale_manager') else UIScaleManager()
        self.theme_manager = parent.theme_manager if hasattr(parent, 'theme_manager') else ThemeManager()

        # 设置对话框尺寸
        dialog_width = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 500)
        dialog_height = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 400)
        self.resize(dialog_width, dialog_height)

        theme = self.theme_manager.get_theme()
        self.setStyleSheet(generate_stylesheet(theme, self.scale_manager, screen_size.width(), screen_size.height()))

        layout = QVBoxLayout(self)
        layout.setSpacing(self.scale_manager.get_scaled_margin(screen_size.width(), screen_size.height()))
        layout.setContentsMargins(
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2
        )

        # 当前播放时间
        time_group = QGroupBox("当前播放时间")
        time_layout = QHBoxLayout(time_group)
        self.time_input = QLineEdit("00:29")
        self.play_button = QPushButton(f"{ICONS['play']} 播放")
        self.play_button.setProperty("class", "outline")
        time_layout.addWidget(self.time_input)
        time_layout.addWidget(self.play_button)
        layout.addWidget(time_group)

        # 选择歌词行
        lyric_group = QGroupBox("选择歌词行")
        lyric_layout = QVBoxLayout(lyric_group)
        self.lyric_combo = QComboBox()
        self.lyric_combo.addItems([
            "窗外的麻雀 在电线杆上多嘴",
            "你说这一句 很有夏天的感觉",
            "手中的铅笔 在纸上来来回回",
            "我用几行字形容你是我的谁",
            "秋刀鱼的滋味 猫跟你都想了解"
        ])
        lyric_layout.addWidget(self.lyric_combo)
        layout.addWidget(lyric_group)

        # 时间偏移
        offset_group = QGroupBox("时间偏移")
        offset_layout = QVBoxLayout(offset_group)
        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setRange(-10, 10)
        self.offset_slider.setValue(0)
        self.offset_label = QLabel("当前偏移: 0秒")
        offset_layout.addWidget(self.offset_slider)
        offset_layout.addWidget(self.offset_label)
        layout.addWidget(offset_group)

        self.offset_slider.valueChanged.connect(self.on_offset_changed)

        # 按钮
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setProperty("class", "outline")
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button = QPushButton(f"{ICONS['check']} 应用同步")
        self.apply_button.setProperty("class", "primary")
        self.apply_button.clicked.connect(self.accept)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
        layout.addLayout(button_layout)

    def on_offset_changed(self, value):
        self.offset_label.setText(f"当前偏移: {value}秒")

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
        menu.addAction("🎨 颜色", self.change_color)
        menu.addAction("🅰️ 字体", self.change_font)
        menu.addAction("🔒 锁定/解锁", self.toggle_lock)
        menu.addAction("❌ 关闭", self.hide)
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

# --- 主程序 ---
class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 2025 - 自然清新版")

        # 初始化缩放管理器和主题管理器
        self.scale_manager = UIScaleManager()
        self.theme_manager = ThemeManager()

        # 获取屏幕尺寸
        screen = QApplication.primaryScreen()
        screen_size = screen.size()

        # 设置窗口尺寸
        window_width = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 1280)
        window_height = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 820)
        self.resize(window_width, window_height)

        # 设置样式
        self.setStyleSheet(generate_stylesheet(self.theme_manager.get_theme(), self.scale_manager, screen_size.width(), screen_size.height()))
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Windows 毛玻璃效果
        if os.name == 'nt':
            try:
                enable_acrylic(int(self.winId()))
            except:
                pass

        # 初始化数据
        self.music_folder = ""
        self.current_collection = ""
        self.collections = []
        self.playlist = []
        self.history = []
        self.lyrics = []
        self.current_index = -1
        self.offset = 0.0
        self.saved_offsets = {}
        self.metadata = {}
        self.mode = 0  # 0:顺序 1:单曲循环 2:随机
        self.rate = 1.0
        self.volume = 80
        self.is_slider_pressed = False

        # 初始化播放器
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.stateChanged.connect(self.on_state_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.error.connect(self.handle_player_error)
        self.player.setVolume(self.volume)

        # 初始化桌面歌词
        self.desktop_lyric = DesktopLyricWindow(self.scale_manager)
        self.desktop_lyric.show()

        # 初始化界面
        self.init_ui()
        self.load_config()

    def init_ui(self):
        # 中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 左侧边栏 ===
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar_width = self.scale_manager.get_scaled_size(self.width(), self.height(), 240)
        sidebar.setFixedWidth(sidebar_width)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(5)

        # 标题
        title_label = QLabel(f"{ICONS['music']} 汽水音乐")
        title_label.setObjectName("Logo")
        sidebar_layout.addWidget(title_label)

        # B站下载按钮
        download_button = QPushButton(f"{ICONS['youtube']} B站音频下载")
        download_button.setObjectName("DownloadBtn")
        download_button.clicked.connect(self.download_bilibili)
        sidebar_layout.addWidget(download_button)

        # 导航区域
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setSpacing(2)
        nav_layout.setContentsMargins(0, 0, 0, 0)

        self.all_music_button = QPushButton(f"{ICONS['disc']} 全部音乐")
        self.all_music_button.setProperty("class", "NavBtn")
        self.all_music_button.setCheckable(True)
        self.all_music_button.setChecked(True)
        self.all_music_button.clicked.connect(lambda: self.switch_collection(None))

        self.history_button = QPushButton(f"{ICONS['history']} 最近播放")
        self.history_button.setProperty("class", "NavBtn")
        self.history_button.setCheckable(True)
        self.history_button.clicked.connect(lambda: self.switch_collection("HISTORY"))

        nav_layout.addWidget(self.all_music_button)
        nav_layout.addWidget(self.history_button)
        sidebar_layout.addWidget(nav_widget)

        # 歌单标题
        collection_title = QLabel("  歌单宝藏库")
        collection_title.setObjectName("SectionTitle")
        sidebar_layout.addWidget(collection_title)

        # 歌单列表
        self.collection_list = QListWidget()
        self.collection_list.setObjectName("CollectionList")
        self.collection_list.itemClicked.connect(self.on_collection_clicked)
        sidebar_layout.addWidget(self.collection_list)

        # 工具按钮
        sidebar_layout.addStretch()
        tools_widget = QWidget()
        tools_layout = QVBoxLayout(tools_widget)
        tools_layout.setSpacing(2)

        refresh_button = QPushButton(f"{ICONS['sync']} 刷新库")
        refresh_button.setProperty("class", "ToolBtn")
        refresh_button.clicked.connect(self.full_scan)
        tools_layout.addWidget(refresh_button)

        new_collection_button = QPushButton(f"{ICONS['folder_plus']} 新建合集")
        new_collection_button.setProperty("class", "ToolBtn")
        new_collection_button.clicked.connect(self.new_collection)
        tools_layout.addWidget(new_collection_button)

        batch_move_button = QPushButton(f"{ICONS['truck']} 批量移动")
        batch_move_button.setProperty("class", "ToolBtn")
        batch_move_button.clicked.connect(self.batch_move_dialog)
        tools_layout.addWidget(batch_move_button)

        folder_button = QPushButton(f"{ICONS['folder_open']} 根目录")
        folder_button.setProperty("class", "ToolBtn")
        folder_button.clicked.connect(self.select_folder)
        tools_layout.addWidget(folder_button)

        desktop_lyric_button = QPushButton(f"{ICONS['microphone']} 桌面歌词")
        desktop_lyric_button.setProperty("class", "ToolBtn")
        desktop_lyric_button.clicked.connect(self.toggle_desktop_lyric)
        tools_layout.addWidget(desktop_lyric_button)

        sidebar_layout.addWidget(tools_widget)
        main_layout.addWidget(sidebar)

        # === 右侧内容区域 ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 堆叠窗口
        self.stacked_widget = QStackedWidget()

        # 页面0: 歌曲列表
        page0 = QWidget()
        page0_layout = QVBoxLayout(page0)
        page0_layout.setContentsMargins(0, 0, 0, 0)
        page0_layout.setSpacing(0)

        # 顶部栏
        top_bar = QWidget()
        top_bar_height = self.scale_manager.get_scaled_size(self.width(), self.height(), 70)
        top_bar.setFixedHeight(top_bar_height)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(30, 15, 30, 15)

        self.title_label = QLabel("全部音乐")
        title_font_size = self.scale_manager.get_scaled_font_size(self.width(), self.height())
        self.title_label.setStyleSheet(f"font-size: {title_font_size + 12}px; font-weight: bold; color: #4CAF50;")

        self.search_box = QLineEdit()
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText(f"{ICONS['search']} 搜索歌曲、歌手或专辑...")
        search_width = self.scale_manager.get_scaled_size(self.width(), self.height(), 280)
        self.search_box.setFixedWidth(search_width)
        self.search_box.textChanged.connect(self.filter_list)

        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.search_box)
        page0_layout.addWidget(top_bar)

        # 内容区域
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_margin = self.scale_manager.get_scaled_padding(self.width(), self.height(), 20)
        content_spacing = self.scale_manager.get_scaled_margin(self.width(), self.height(), 20)
        content_layout.setContentsMargins(content_margin, 0, content_margin, content_margin)
        content_layout.setSpacing(content_spacing)

        # 分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧歌曲表格容器
        song_table_container = QWidget()
        song_table_layout = QVBoxLayout(song_table_container)
        song_table_layout.setContentsMargins(0, 0, 0, 0)
        song_table_layout.setSpacing(0)

        # 歌曲表格头部
        song_table_header = QWidget()
        song_table_header_height = self.scale_manager.get_scaled_size(self.width(), self.height(), 60)
        song_table_header.setFixedHeight(song_table_header_height)
        song_header_layout = QHBoxLayout(song_table_header)
        song_header_layout.setContentsMargins(20, 15, 20, 15)

        song_table_title = QLabel("歌曲列表")
        song_table_font_size = self.scale_manager.get_scaled_font_size(self.width(), self.height())
        song_table_title.setStyleSheet(f"font-size: {song_table_font_size + 5}px; font-weight: bold; color: #1B5E20;")

        song_table_actions = QHBoxLayout()
        song_table_actions.setSpacing(10)

        batch_edit_button = QPushButton(f"{ICONS['edit']} 批量编辑")
        batch_edit_button.setProperty("class", "ActionBtn")
        batch_edit_button.clicked.connect(self.batch_edit_dialog)

        random_play_button = QPushButton(f"{ICONS['random']} 随机播放")
        random_play_button.setProperty("class", "ActionBtn")

        song_table_actions.addWidget(batch_edit_button)
        song_table_actions.addWidget(random_play_button)

        song_header_layout.addWidget(song_table_title)
        song_header_layout.addStretch()
        song_header_layout.addLayout(song_table_actions)

        song_table_layout.addWidget(song_table_header)

        # 歌曲表格
        self.song_table = QTableWidget()
        self.song_table.setColumnCount(5)
        self.song_table.setHorizontalHeaderLabels(["标题", "歌手", "专辑", "时长", "操作"])
        self.song_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.song_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.song_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.song_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.song_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.song_table.verticalHeader().setVisible(False)
        self.song_table.setShowGrid(False)
        self.song_table.setAlternatingRowColors(False)
        self.song_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.song_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.song_table.itemDoubleClicked.connect(self.play_selected)
        self.song_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.song_table.customContextMenuRequested.connect(self.show_context_menu)

        song_table_layout.addWidget(self.song_table)
        splitter.addWidget(song_table_container)

        # 歌词面板
        lyric_panel = QWidget()
        lyric_panel_width = self.scale_manager.get_scaled_size(self.width(), self.height(), 320)
        lyric_panel.setFixedWidth(lyric_panel_width)
        lyric_layout = QVBoxLayout(lyric_panel)
        lyric_layout.setContentsMargins(0, 0, 0, 0)
        lyric_layout.setSpacing(0)

        # 歌词面板头部
        lyric_header = QWidget()
        lyric_header_height = self.scale_manager.get_scaled_size(self.width(), self.height(), 50)
        lyric_header.setFixedHeight(lyric_header_height)
        lyric_header_layout = QHBoxLayout(lyric_header)
        lyric_header_layout.setContentsMargins(20, 15, 20, 15)

        lyric_title = QLabel("歌词")
        lyric_title_font_size = self.scale_manager.get_scaled_font_size(self.width(), self.height())
        lyric_title.setStyleSheet(f"font-size: {lyric_title_font_size + 3}px; font-weight: bold; color: #1B5E20;")

        lyric_controls = QHBoxLayout()
        lyric_controls.setSpacing(8)

        sync_lyrics_button = QPushButton(f"{ICONS['sync']} 同步")
        sync_lyrics_button.setProperty("class", "LyricControlBtn")
        sync_lyrics_button.clicked.connect(self.sync_lyrics)

        search_lyrics_button = QPushButton(f"{ICONS['search']} 搜索")
        search_lyrics_button.setProperty("class", "LyricControlBtn")
        search_lyrics_button.clicked.connect(self.manual_search_lyrics)

        lyric_controls.addWidget(sync_lyrics_button)
        lyric_controls.addWidget(search_lyrics_button)

        lyric_header_layout.addWidget(lyric_title)
        lyric_header_layout.addStretch()
        lyric_header_layout.addLayout(lyric_controls)

        lyric_layout.addWidget(lyric_header)

        # 歌词内容
        self.lyric_panel = QListWidget()
        self.lyric_panel.setObjectName("LyricPanel")
        self.lyric_panel.setFocusPolicy(Qt.NoFocus)
        self.lyric_panel.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        lyric_layout.addWidget(self.lyric_panel)
        splitter.addWidget(lyric_panel)

        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        content_layout.addWidget(splitter)

        page0_layout.addWidget(content_widget)

        self.stacked_widget.addWidget(page0)

        # 页面1: 歌词页面
        page1 = QWidget()
        page1.setObjectName("LyricsPage")
        page1_layout = QVBoxLayout(page1)
        page1_margin = self.scale_manager.get_scaled_padding(self.width(), self.height(), 60)
        page1_layout.setContentsMargins(page1_margin, page1_margin, page1_margin, page1_margin)

        # 歌词容器
        lyrics_container = QWidget()
        lyrics_layout = QHBoxLayout(lyrics_container)

        # 左侧封面和信息
        left_widget = QWidget()
        left_widget_width = self.scale_manager.get_scaled_size(self.width(), self.height(), 320)
        left_widget.setFixedWidth(left_widget_width)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setAlignment(Qt.AlignCenter)

        self.cover_label = QLabel()
        cover_size = self.scale_manager.get_scaled_size(self.width(), self.height(), 280)
        self.cover_label.setFixedSize(cover_size, cover_size)
        self.cover_label.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4CAF50, stop:1 #81C784); border-radius: 16px;")

        self.song_title_label = QLabel("歌曲标题")
        self.song_title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #1B5E20; margin-top: 20px;")

        self.artist_label = QLabel("歌手")
        self.artist_label.setStyleSheet("font-size: 18px; color: #4CAF50;")

        back_button = QPushButton(f"{ICONS['chevron_down']} 返回列表")
        back_button.setCursor(Qt.PointingHandCursor)
        back_button.setStyleSheet("background: transparent; color: #4CAF50; border: 1px solid #C8E6C9; border-radius: 12px; margin-top: 30px; padding: 10px 20px;")
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))

        left_layout.addWidget(self.cover_label)
        left_layout.addWidget(self.song_title_label)
        left_layout.addWidget(self.artist_label)
        left_layout.addWidget(back_button)
        lyrics_layout.addWidget(left_widget)

        # 右侧歌词
        self.big_lyric_list = QListWidget()
        self.big_lyric_list.setObjectName("BigLyric")
        self.big_lyric_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.big_lyric_list.setFocusPolicy(Qt.NoFocus)
        lyrics_layout.addWidget(self.big_lyric_list, stretch=1)

        page1_layout.addWidget(lyrics_container)

        # 歌词控制栏
        lyrics_controls = QWidget()
        lyrics_controls_height = self.scale_manager.get_scaled_size(self.width(), self.height(), 80)
        lyrics_controls.setFixedHeight(lyrics_controls_height)
        lyrics_controls_layout = QHBoxLayout(lyrics_controls)
        lyrics_controls_layout.setAlignment(Qt.AlignCenter)

        font_size_button = QPushButton(f"{ICONS['text_height']} 字体大小")
        font_size_button.setProperty("class", "LyricControlBtn")
        font_size_button.clicked.connect(self.adjust_font_size)

        font_color_button = QPushButton(f"{ICONS['palette']} 字体颜色")
        font_color_button.setProperty("class", "LyricControlBtn")
        font_color_button.clicked.connect(self.adjust_font_color)

        font_family_button = QPushButton(f"{ICONS['font']} 字体")
        font_family_button.setProperty("class", "LyricControlBtn")
        font_family_button.clicked.connect(self.adjust_font_family)

        align_lyrics_button = QPushButton(f"{ICONS['align_center']} 居中")
        align_lyrics_button.setProperty("class", "LyricControlBtn")
        align_lyrics_button.clicked.connect(self.toggle_lyrics_alignment)

        sync_lyrics_big_button = QPushButton(f"{ICONS['sync']} 同步歌词")
        sync_lyrics_big_button.setProperty("class", "LyricControlBtn")
        sync_lyrics_big_button.clicked.connect(self.sync_lyrics)

        lyrics_controls_layout.addWidget(font_size_button)
        lyrics_controls_layout.addWidget(font_color_button)
        lyrics_controls_layout.addWidget(font_family_button)
        lyrics_controls_layout.addWidget(align_lyrics_button)
        lyrics_controls_layout.addWidget(sync_lyrics_big_button)

        page1_layout.addWidget(lyrics_controls)

        self.stacked_widget.addWidget(page1)
        right_layout.addWidget(self.stacked_widget)

        # === 底部播放控制栏 ===
        player_bar = QFrame()
        player_bar.setObjectName("PlayerBar")
        player_bar_height = self.scale_manager.get_scaled_size(self.width(), self.height(), 100)
        player_bar.setFixedHeight(player_bar_height)
        player_layout = QVBoxLayout(player_bar)
        player_margin = self.scale_manager.get_scaled_padding(self.width(), self.height(), 25)
        player_layout.setContentsMargins(player_margin, 15, player_margin, 15)

        # 进度条
        progress_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet("color: #4CAF50; font-size: 11px;")

        self.total_time_label = QLabel("00:00")
        self.total_time_label.setStyleSheet("color: #4CAF50; font-size: 11px;")

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        self.progress_slider.valueChanged.connect(self.on_slider_moved)

        progress_layout.addWidget(self.current_time_label)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.total_time_label)
        player_layout.addLayout(progress_layout)

        # 控制按钮
        control_layout = QHBoxLayout()

        # 左侧信息
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)

        self.cover_button = QPushButton()
        cover_button_size = self.scale_manager.get_scaled_size(self.width(), self.height(), 50)
        self.cover_button.setFixedSize(cover_button_size, cover_button_size)
        self.cover_button.setCursor(Qt.PointingHandCursor)
        self.cover_button.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4CAF50, stop:1 #81C784); border-radius: 8px; border: none;")
        self.cover_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(12, 0, 0, 0)

        self.song_title_mini = QLabel("--")
        self.song_title_mini.setStyleSheet("font-weight: bold; color: #1B5E20; font-size: 13px;")
        self.song_title_mini.setCursor(Qt.PointingHandCursor)
        self.song_title_mini.mousePressEvent = lambda e: self.edit_song_info()

        self.artist_mini = QLabel("--")
        self.artist_mini.setStyleSheet("color: #4CAF50; font-size: 12px;")

        text_layout.addWidget(self.song_title_mini)
        text_layout.addWidget(self.artist_mini)

        info_layout.addWidget(self.cover_button)
        info_layout.addWidget(text_widget)
        control_layout.addWidget(info_widget)

        control_layout.addStretch()

        # 播放控制
        self.mode_button = QPushButton(f"{ICONS['retweet']}")
        self.mode_button.setProperty("class", "CtrlBtn")
        self.mode_button.clicked.connect(self.toggle_play_mode)

        self.prev_button = QPushButton(f"{ICONS['step_backward']}")
        self.prev_button.setProperty("class", "CtrlBtn")
        self.prev_button.clicked.connect(self.play_previous)

        self.play_button = QPushButton(f"{ICONS['play']}")
        self.play_button.setObjectName("PlayBtn")
        self.play_button.clicked.connect(self.toggle_play)

        self.next_button = QPushButton(f"{ICONS['step_forward']}")
        self.next_button.setProperty("class", "CtrlBtn")
        self.next_button.clicked.connect(self.play_next)

        self.rate_button = QPushButton("1.0x")
        self.rate_button.setProperty("class", "CtrlBtn")
        self.rate_button.clicked.connect(self.toggle_playback_rate)

        control_layout.addWidget(self.mode_button)
        control_layout.addSpacing(15)
        control_layout.addWidget(self.prev_button)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.next_button)
        control_layout.addSpacing(15)
        control_layout.addWidget(self.rate_button)
        control_layout.addStretch()

        # 右侧控制
        right_control_layout = QHBoxLayout()
        right_control_layout.setAlignment(Qt.AlignRight)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        volume_slider_width = self.scale_manager.get_scaled_size(self.width(), self.height(), 90)
        self.volume_slider.setFixedWidth(volume_slider_width)
        self.volume_slider.valueChanged.connect(self.player.setVolume)

        self.offset_button = QPushButton(f"{ICONS['sliders']} 微调")
        self.offset_button.setProperty("class", "OffsetBtn")
        self.offset_button.clicked.connect(self.adjust_offset)

        right_control_layout.addWidget(QLabel(f"{ICONS['volume']}"))
        right_control_layout.addWidget(self.volume_slider)
        right_control_layout.addWidget(self.offset_button)
        control_layout.addLayout(right_control_layout)

        player_layout.addLayout(control_layout)
        right_layout.addWidget(player_bar)

        main_layout.addWidget(right_widget)

        # 初始化歌单列表
        self.init_collection_list()

    def init_collection_list(self):
        self.collection_list.clear()

        # 添加默认歌单
        collections = [
            (ICONS['heart'], "我的收藏"),
            (ICONS['fire'], "流行音乐"),
            (ICONS['star'], "经典老歌"),
            (ICONS['music'], "学习专注"),
            (ICONS['disc'], "驾车音乐"),
            (ICONS['play'], "运动节奏")
        ]

        for icon, name in collections:
            item = QListWidgetItem(f"{icon} {name}")
            item.setData(Qt.UserRole, name)
            self.collection_list.addItem(item)

    # === 核心功能 ===
    def full_scan(self):
        if not self.music_folder:
            QMessageBox.information(self, "提示", "请先选择音乐文件夹")
            return

        try:
            self.collections = []
            extensions = ('.mp3', '.wav', '.m4a', '.flac', '.mp4')

            for item in os.listdir(self.music_folder):
                item_path = os.path.join(self.music_folder, item)
                if os.path.isdir(item_path):
                    music_files = [f for f in os.listdir(item_path) if f.lower().endswith(extensions)]
                    if len(music_files) > 1:
                        self.collections.append(item)

            self.init_collection_list()
            self.switch_collection(None)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"扫描文件夹时出错: {str(e)}")

    def switch_collection(self, collection_name):
        self.all_music_button.setChecked(collection_name is None)
        self.history_button.setChecked(collection_name == "HISTORY")

        if collection_name == "HISTORY":
            self.current_collection = "HISTORY"
            self.title_label.setText("最近播放")
        elif collection_name:
            self.current_collection = collection_name
            self.title_label.setText(collection_name)
        else:
            self.current_collection = ""
            self.title_label.setText("全部音乐")

        self.load_playlist()

    def on_collection_clicked(self, item):
        collection_name = item.data(Qt.UserRole)
        self.switch_collection(collection_name)

    def load_playlist(self):
        self.playlist = []
        self.song_table.setRowCount(0)
        extensions = ('.mp3', '.wav', '.m4a', '.flac', '.mp4')
        directories = []

        if self.current_collection == "HISTORY":
            for song in self.history:
                self.add_song_to_table(song)
            return

        if self.current_collection:
            directories = [os.path.join(self.music_folder, self.current_collection)]
        else:
            directories = [self.music_folder]
            for collection in self.collections:
                directories.append(os.path.join(self.music_folder, collection))

        for directory in directories:
            if os.path.exists(directory):
                for file in os.listdir(directory):
                    if file.lower().endswith(extensions):
                        file_path = os.path.abspath(os.path.join(directory, file))
                        metadata = self.metadata.get(file, {})
                        self.add_song_to_table({
                            "path": file_path,
                            "name": file,
                            "artist": metadata.get("a", "未知"),
                            "album": metadata.get("b", "未知")
                        })

    def add_song_to_table(self, song):
        self.playlist.append(song)
        row = self.song_table.rowCount()
        self.song_table.insertRow(row)

        self.song_table.setItem(row, 0, QTableWidgetItem(os.path.splitext(song["name"])[0]))
        self.song_table.setItem(row, 1, QTableWidgetItem(song["artist"]))
        self.song_table.setItem(row, 2, QTableWidgetItem(song["album"]))
        self.song_table.setItem(row, 3, QTableWidgetItem(song.get("duration", "-")))

        # 操作按钮
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(0)

        play_button = QPushButton(f"{ICONS['play']}")
        play_button.setProperty("class", "SongActionBtn")
        icon_size = self.scale_manager.get_scaled_icon_size(self.width(), self.height())
        play_button.setFixedSize(icon_size, icon_size)
        play_button.clicked.connect(lambda: self.play(row))

        edit_button = QPushButton(f"{ICONS['edit']}")
        edit_button.setProperty("class", "SongActionBtn")
        edit_button.setFixedSize(icon_size, icon_size)
        edit_button.clicked.connect(lambda: self.edit_song_info(row))

        more_button = QPushButton(f"{ICONS['ellipsis']}")
        more_button.setProperty("class", "SongActionBtn")
        more_button.setFixedSize(icon_size, icon_size)

        action_layout.addWidget(play_button)
        action_layout.addWidget(edit_button)
        action_layout.addWidget(more_button)
        action_layout.addStretch()

        self.song_table.setCellWidget(row, 4, action_widget)

    def filter_list(self, text):
        search_text = text.lower()
        for row in range(self.song_table.rowCount()):
            hide = True
            for column in range(3):
                item = self.song_table.item(row, column)
                if item and search_text in item.text().lower():
                    hide = False
                    break
            self.song_table.setRowHidden(row, hide)

    def play_selected(self, item):
        self.play(item.row())

    def play(self, index):
        if not self.playlist or index < 0 or index >= len(self.playlist):
            return

        # 释放之前的媒体资源
        self.player.setMedia(QMediaContent())

        self.current_index = index
        song = self.playlist[index]

        # 检查文件是否存在
        if not os.path.exists(song["path"]):
            QMessageBox.warning(self, "错误", f"文件不存在: {song['path']}")
            return

        # 添加到播放历史
        if song not in self.history:
            self.history.insert(0, song)
            # 只保留最近50首
            if len(self.history) > 50:
                self.history = self.history[:50]
            self.save_history()

        try:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(song["path"])))
            self.player.setPlaybackRate(self.rate)
            self.player.play()
            self.play_button.setText(f"{ICONS['pause']}")

            # 更新界面信息
            song_name = os.path.splitext(song["name"])[0]
            self.song_title_mini.setText(song_name[:15] + ".." if len(song_name) > 15 else song_name)
            self.artist_mini.setText(song["artist"])
            self.song_title_label.setText(song_name)
            self.artist_label.setText(song["artist"])

            # 恢复偏移量
            self.offset = self.saved_offsets.get(song["name"], 0.0)

            # 加载歌词
            lyric_path = os.path.splitext(song["path"])[0] + ".lrc"
            if os.path.exists(lyric_path):
                try:
                    with open(lyric_path, 'r', encoding='utf-8', errors='ignore') as f:
                        self.parse_lyrics(f.read())
                except Exception as e:
                    print(f"歌词解析错误: {e}")
                    self.clear_lyrics()
            else:
                self.clear_lyrics()
                self.lyric_panel.addItem("搜索歌词...")
                self.big_lyric_list.addItem("搜索歌词...")

                # 自动搜索歌词
                self.auto_search_lyrics(song_name, lyric_path)

        except Exception as e:
            print(f"播放错误: {e}")
            QMessageBox.warning(self, "播放错误", f"无法播放文件: {str(e)}")

    def auto_search_lyrics(self, song_name, lyric_path):
        """自动搜索歌词"""
        self.lyric_search_worker = LyricListSearchWorker(song_name)
        self.lyric_search_worker.search_finished.connect(
            lambda results: self.on_auto_search_finished(results, lyric_path)
        )
        self.lyric_search_worker.start()

    def on_auto_search_finished(self, results, lyric_path):
        """自动搜索完成回调"""
        if results and self.current_index >= 0:
            # 下载第一首匹配的歌词
            self.lyric_downloader = LyricDownloader(results[0]['id'], lyric_path)
            self.lyric_downloader.finished_signal.connect(self.parse_lyrics)
            self.lyric_downloader.start()
        else:
            self.clear_lyrics()
            self.lyric_panel.addItem("无歌词")
            self.big_lyric_list.addItem("无歌词")

    def clear_lyrics(self):
        self.lyrics = []
        self.lyric_panel.clear()
        self.big_lyric_list.clear()

    def parse_lyrics(self, lyrics_text):
        self.lyrics = []
        self.lyric_panel.clear()
        self.big_lyric_list.clear()

        for line in lyrics_text.splitlines():
            match = re.match(r'\[(\d+):(\d+)\.(\d+)\](.*)', line)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                hundredths = int(match.group(3))
                text = match.group(4).strip()

                if text:
                    time_in_seconds = minutes * 60 + seconds + hundredths / 100
                    self.lyrics.append({"t": time_in_seconds, "txt": text})
                    self.lyric_panel.addItem(text)
                    self.big_lyric_list.addItem(text)

    def on_position_changed(self, position):
        if not self.is_slider_pressed:
            self.progress_slider.setValue(position)

        self.current_time_label.setText(ms_to_str(position))

        current_time = position / 1000 + self.offset

        if self.lyrics:
            current_lyric_index = -1
            for i, lyric in enumerate(self.lyrics):
                if current_time >= lyric["t"]:
                    current_lyric_index = i
                else:
                    break

            if current_lyric_index != -1:
                prev_lyric = self.lyrics[current_lyric_index - 1]["txt"] if current_lyric_index > 0 else ""
                current_lyric = self.lyrics[current_lyric_index]["txt"]
                next_lyric = self.lyrics[current_lyric_index + 1]["txt"] if current_lyric_index < len(self.lyrics) - 1 else ""

                self.desktop_lyric.set_text(prev_lyric, current_lyric, next_lyric)

                if current_lyric_index < self.lyric_panel.count():
                    self.lyric_panel.setCurrentRow(current_lyric_index)
                    self.lyric_panel.scrollToItem(self.lyric_panel.item(current_lyric_index), QAbstractItemView.PositionAtCenter)

                if current_lyric_index < self.big_lyric_list.count():
                    self.big_lyric_list.setCurrentRow(current_lyric_index)
                    self.big_lyric_list.scrollToItem(self.big_lyric_list.item(current_lyric_index), QAbstractItemView.PositionAtCenter)

    def on_duration_changed(self, duration):
        self.progress_slider.setRange(0, duration)
        self.total_time_label.setText(ms_to_str(duration))

    def on_state_changed(self, state):
        self.play_button.setText(f"{ICONS['pause']}" if state == QMediaPlayer.PlayingState else f"{ICONS['play']}")

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            if self.mode == 1:  # 单曲循环
                self.player.play()
            else:
                self.play_next()

    def handle_player_error(self):
        QTimer.singleShot(1000, self.play_next)

    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            if self.player.mediaStatus() == QMediaPlayer.NoMedia:
                if self.playlist:
                    self.play(0)
            else:
                self.player.play()

    def toggle_play_mode(self):
        self.mode = (self.mode + 1) % 3
        self.mode_button.setText([f"{ICONS['retweet']}", "🔂", "🔀"][self.mode])

    def toggle_playback_rate(self):
        rates = [1.0, 1.25, 1.5, 2.0, 0.5]
        current_index = rates.index(self.rate) if self.rate in rates else 0
        self.rate = rates[(current_index + 1) % len(rates)]
        self.player.setPlaybackRate(self.rate)
        self.rate_button.setText(f"{self.rate}x")

    def play_next(self):
        if not self.playlist:
            return

        if self.mode == 2:  # 随机播放
            next_index = random.randint(0, len(self.playlist) - 1)
        else:  # 顺序播放
            next_index = (self.current_index + 1) % len(self.playlist)

        self.play(next_index)

    def play_previous(self):
        if not self.playlist:
            return

        if self.mode == 2:  # 随机播放
            prev_index = random.randint(0, len(self.playlist) - 1)
        else:  # 顺序播放
            prev_index = (self.current_index - 1) % len(self.playlist)

        self.play(prev_index)

    def on_slider_pressed(self):
        self.is_slider_pressed = True

    def on_slider_released(self):
        self.is_slider_pressed = False
        self.player.setPosition(self.progress_slider.value())

    def on_slider_moved(self, value):
        if self.is_slider_pressed:
            self.current_time_label.setText(ms_to_str(value))

    def adjust_offset(self):
        offset, ok = QInputDialog.getDouble(self, "歌词微调", "调整秒数:", self.offset, -10, 10, 1)
        if ok:
            self.offset = offset
            if self.current_index >= 0:
                song_name = self.playlist[self.current_index]["name"]
                self.saved_offsets[song_name] = self.offset
                self.save_offsets()

    # === 歌词控制功能 ===
    def adjust_font_size(self):
        current_font = self.big_lyric_list.font()
        current_size = current_font.pointSize()
        new_size, ok = QInputDialog.getInt(self, "字体大小", "请输入字体大小:", current_size, 12, 48, 2)
        if ok:
            font = QFont(current_font)
            font.setPointSize(new_size)
            self.big_lyric_list.setFont(font)

    def adjust_font_color(self):
        color = QColorDialog.getColor(QColor(76, 175, 80), self)
        if color.isValid():
            # 更新主题主色调
            self.theme_manager.themes['light']['primary'] = color.name()
            self.theme_manager.themes['light']['primary-light'] = color.lighter(120).name()
            self.theme_manager.themes['light']['primary-dark'] = color.darker(120).name()
            self.update_stylesheet()

    def adjust_font_family(self):
        font, ok = QFontDialog.getFont(self.big_lyric_list.font(), self)
        if ok:
            self.big_lyric_list.setFont(font)
            self.lyric_panel.setFont(font)

    def toggle_lyrics_alignment(self):
        current_alignment = self.big_lyric_list.itemAlignment(self.big_lyric_list.currentItem() or QListWidgetItem())
        alignments = [Qt.AlignCenter, Qt.AlignLeft, Qt.AlignRight]
        current_index = alignments.index(current_alignment) if current_alignment in alignments else 0
        next_index = (current_index + 1) % len(alignments)

        for i in range(self.big_lyric_list.count()):
            item = self.big_lyric_list.item(i)
            item.setTextAlignment(alignments[next_index])

        for i in range(self.lyric_panel.count()):
            item = self.lyric_panel.item(i)
            item.setTextAlignment(alignments[next_index])

    def sync_lyrics(self):
        dialog = SyncLyricsDialog(self)
        dialog.exec_()

    def manual_search_lyrics(self):
        """手动搜索歌词"""
        if not self.playlist or self.current_index < 0:
            QMessageBox.warning(self, "提示", "请先选择一首歌曲")
            return

        song = self.playlist[self.current_index]
        duration = self.player.duration()

        dialog = LyricSearchDialog(os.path.splitext(song["name"])[0], duration, self)
        if dialog.exec_() == QDialog.Accepted and dialog.result_id:
            lyric_path = os.path.splitext(song["path"])[0] + ".lrc"
            self.lyric_downloader = LyricDownloader(dialog.result_id, lyric_path)
            self.lyric_downloader.finished_signal.connect(lambda lyrics: self.on_manual_lyrics_downloaded(lyrics))
            self.lyric_downloader.start()

    def on_manual_lyrics_downloaded(self, lyrics):
        """手动歌词下载完成回调"""
        self.parse_lyrics(lyrics)
        QMessageBox.information(self, "成功", "歌词下载成功")

    # === 文件操作 ===
    def show_context_menu(self, position):
        selected_rows = sorted(set(item.row() for item in self.song_table.selectedItems()))
        if not selected_rows:
            return

        theme = self.theme_manager.get_theme()
        menu = QMenu()
        menu.setStyleSheet(f"""
        QMenu {{
            background: {theme['surface']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border']};
        }}
        QMenu::item:selected {{
            background: {theme['selected']};
            color: {theme['primary']};
        }}
        """)

        # 移动到菜单
        move_menu = menu.addMenu("📂 移动到...")
        move_menu.addAction("根目录", lambda: self.move_songs(selected_rows, ""))
        for collection in self.collections:
            move_menu.addAction(collection, lambda _, c=collection: self.move_songs(selected_rows, c))

        menu.addAction("🔠 批量重命名", lambda: self.batch_rename(selected_rows))
        menu.addAction("✏️ 编辑信息", lambda: self.batch_edit_dialog())
        menu.addSeparator()

        if len(selected_rows) == 1:
            index = selected_rows[0]
            menu.addAction("🔐 绑定/整理", lambda: self.bind_song(index))
            menu.addAction("🔍 搜索歌词", lambda: self.manual_search_lyrics())
            menu.addAction("❌ 删除歌词", lambda: self.delete_lyrics(index))

        menu.addAction("🗑️ 删除", lambda: self.delete_songs(selected_rows))
        menu.exec_(self.song_table.mapToGlobal(position))

    def move_songs(self, rows, target_folder):
        self.player.setMedia(QMediaContent())

        target_path = os.path.join(self.music_folder, target_folder) if target_folder else self.music_folder
        if not os.path.exists(target_path):
            try:
                os.makedirs(target_path)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法创建目录: {str(e)}")
                return

        moved_count = 0
        for row in rows:
            if row < len(self.playlist):
                song = self.playlist[row]
                try:
                    source_path = song["path"]
                    destination_path = os.path.join(target_path, song["name"])

                    if source_path != destination_path:
                        shutil.move(source_path, destination_path)

                    # 移动歌词文件
                    lyric_source = os.path.splitext(source_path)[0] + ".lrc"
                    if os.path.exists(lyric_source):
                        lyric_destination = os.path.join(target_path, os.path.basename(lyric_source))
                        shutil.move(lyric_source, lyric_destination)

                    moved_count += 1
                except Exception as e:
                    print(f"移动文件错误: {e}")

        self.full_scan()
        QMessageBox.information(self, "完成", f"成功移动 {moved_count} 首歌曲")

    def batch_rename(self, rows):
        if not rows:
            QMessageBox.warning(self, "提示", "请先选择要重命名的歌曲")
            return

        prefix, ok = QInputDialog.getText(self, "批量重命名", "请输入前缀:")
        if ok and prefix:
            renamed_count = 0
            for row in rows:
                if row < len(self.playlist):
                    song = self.playlist[row]
                    try:
                        old_path = song["path"]
                        dir_name = os.path.dirname(old_path)
                        file_ext = os.path.splitext(song["name"])[1]
                        new_name = f"{prefix} {os.path.splitext(song['name'])[0]}{file_ext}"
                        new_path = os.path.join(dir_name, new_name)

                        if old_path != new_path:
                            shutil.move(old_path, new_path)

                        # 重命名歌词文件
                        lyric_old = os.path.splitext(old_path)[0] + ".lrc"
                        if os.path.exists(lyric_old):
                            lyric_new = os.path.join(dir_name, f"{prefix} {os.path.splitext(song['name'])[0]}.lrc")
                            shutil.move(lyric_old, lyric_new)

                        renamed_count += 1
                    except Exception as e:
                        print(f"重命名错误: {e}")

            self.full_scan()
            QMessageBox.information(self, "完成", f"成功重命名 {renamed_count} 首歌曲")

    def edit_song_info(self, row=None):
        if row is None and self.current_index >= 0:
            row = self.current_index

        if row is None or row >= len(self.playlist):
            QMessageBox.warning(self, "提示", "请先选择一首歌曲")
            return

        song = self.playlist[row]
        dialog = BatchInfoDialog(self)

        # 设置当前信息
        song_name = os.path.splitext(song["name"])[0]
        artist = song.get("artist", "未知")
        album = song.get("album", "未知")
        year = song.get("year", "")

        dialog.set_data(song_name, artist, album, year)

        if dialog.exec_() == QDialog.Accepted:
            title, artist, album, year = dialog.get_data()

            # 更新元数据
            if song["name"] not in self.metadata:
                self.metadata[song["name"]] = {}

            if title:
                self.metadata[song["name"]]["title"] = title
            if artist:
                self.metadata[song["name"]]["artist"] = artist
            if album:
                self.metadata[song["name"]]["album"] = album
            if year:
                self.metadata[song["name"]]["year"] = year

            self.save_metadata()
            self.full_scan()

    def batch_edit_dialog(self):
        selected_rows = sorted(set(item.row() for item in self.song_table.selectedItems()))
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要编辑的歌曲")
            return

        dialog = BatchInfoDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            title, artist, album, year = dialog.get_data()
            for row in selected_rows:
                if row < len(self.playlist):
                    song_name = self.playlist[row]["name"]
                    if song_name not in self.metadata:
                        self.metadata[song_name] = {}

                    if title:
                        self.metadata[song_name]["title"] = title
                    if artist:
                        self.metadata[song_name]["artist"] = artist
                    if album:
                        self.metadata[song_name]["album"] = album
                    if year:
                        self.metadata[song_name]["year"] = year

            self.save_metadata()
            self.full_scan()

    def bind_song(self, index):
        self.player.setMedia(QMediaContent())

        song = self.playlist[index]
        source_path = song["path"]

        file_path, _ = QFileDialog.getOpenFileName(self, "选择歌词文件", "", "歌词文件 (*.lrc)")
        if file_path:
            folder_name = os.path.splitext(song["name"])[0]
            destination_folder = os.path.join(os.path.dirname(source_path), folder_name)

            try:
                os.makedirs(destination_folder, exist_ok=True)

                # 移动音频文件
                shutil.move(source_path, os.path.join(destination_folder, song["name"]))

                # 复制歌词文件
                lyric_destination = os.path.join(destination_folder, os.path.splitext(song["name"])[0] + ".lrc")
                shutil.copy(file_path, lyric_destination)

                self.full_scan()
                QMessageBox.information(self, "完成", "歌曲整理完成")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"整理失败: {str(e)}")

    def delete_lyrics(self, index):
        lyric_path = os.path.splitext(self.playlist[index]["path"])[0] + ".lrc"
        if os.path.exists(lyric_path):
            try:
                os.remove(lyric_path)
                QMessageBox.information(self, "完成", "歌词已删除")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除歌词失败: {str(e)}")

        if self.current_index == index:
            self.clear_lyrics()

    def delete_songs(self, rows):
        reply = QMessageBox.question(self, "确认", "确定要删除选中的歌曲吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.player.setMedia(QMediaContent())

            deleted_count = 0
            for row in rows:
                if row < len(self.playlist):
                    try:
                        song_path = self.playlist[row]["path"]
                        os.remove(song_path)

                        lyric_path = os.path.splitext(song_path)[0] + ".lrc"
                        if os.path.exists(lyric_path):
                            os.remove(lyric_path)

                        deleted_count += 1
                    except Exception as e:
                        print(f"删除文件错误: {e}")

            self.full_scan()
            QMessageBox.information(self, "完成", f"成功删除 {deleted_count} 首歌曲")

    # === B站下载 ===
    def download_bilibili(self):
        if not self.music_folder:
            QMessageBox.warning(self, "提示", "请先设置音乐文件夹")
            return

        dialog = DownloadDialog(self, 1, self.collections)
        if dialog.exec_() == QDialog.Accepted:
            url, mode, folder, artist, album = dialog.get_data()

            if not url:
                QMessageBox.warning(self, "错误", "请输入视频链接")
                return

            download_path = os.path.join(self.music_folder, folder) if folder else self.music_folder
            self.temp_metadata = (artist, album)

            self.title_label.setText("⏳ 下载中...")

            self.downloader = BilibiliDownloader(url, download_path, mode, 1)
            self.downloader.progress_signal.connect(lambda status: self.title_label.setText(status))
            self.downloader.finished_signal.connect(self.on_download_finished)
            self.downloader.error_signal.connect(self.on_download_error)
            self.downloader.start()

    def on_download_finished(self, path, _):
        artist, album = self.temp_metadata
        if artist or album:
            for file in os.listdir(path):
                if file not in self.metadata:
                    self.metadata[file] = {"a": artist or "未知", "b": album or "未知"}

        self.save_metadata()

        self.full_scan()
        self.title_label.setText("下载完成")

    def on_download_error(self, error):
        QMessageBox.warning(self, "下载错误", error)
        self.title_label.setText("下载失败")

    # === 其他功能 ===
    def new_collection(self):
        name, ok = QInputDialog.getText(self, "新建合集", "请输入合集名称:")
        if ok and name:
            safe_name = sanitize_filename(name)
            try:
                os.makedirs(os.path.join(self.music_folder, safe_name), exist_ok=True)
                self.full_scan()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建合集失败: {str(e)}")

    def batch_move_dialog(self):
        selected_rows = sorted(set(item.row() for item in self.song_table.selectedItems()))
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要移动的歌曲")
            return

        collections = ["根目录"] + self.collections
        target, ok = QInputDialog.getItem(self, "批量移动", "选择目标位置:", collections, 0, False)
        if ok:
            target_folder = "" if target == "根目录" else target
            self.move_songs(selected_rows, target_folder)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择音乐文件夹")
        if folder:
            self.music_folder = folder
            self.full_scan()
            self.save_config()

    def toggle_desktop_lyric(self):
        if self.desktop_lyric.isVisible():
            self.desktop_lyric.hide()
        else:
            self.desktop_lyric.show()

    def update_stylesheet(self):
        """更新样式表"""
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        self.setStyleSheet(generate_stylesheet(
            self.theme_manager.get_theme(),
            self.scale_manager,
            screen_size.width(),
            screen_size.height()
        ))

    # === 配置管理 ===
    def load_config(self):
        # 加载音乐文件夹
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.music_folder = config.get("folder", "")
                if self.music_folder:
                    self.full_scan()
            except:
                pass

        # 加载元数据
        if os.path.exists(METADATA_FILE):
            try:
                with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            except:
                pass

        # 加载偏移量
        if os.path.exists(OFFSET_FILE):
            try:
                with open(OFFSET_FILE, 'r', encoding='utf-8') as f:
                    self.saved_offsets = json.load(f)
            except:
                pass

        # 加载历史记录
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except:
                pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({"folder": self.music_folder}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置错误: {e}")

    def save_metadata(self):
        try:
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存元数据错误: {e}")

    def save_offsets(self):
        try:
            with open(OFFSET_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.saved_offsets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存偏移量错误: {e}")

    def save_history(self):
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史记录错误: {e}")

# === 主程序入口 ===
if __name__ == "__main__":
    # 处理打包后的资源路径
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(app_path, 'PyQt5', 'Qt', 'plugins')
        QCoreApplication.addLibraryPath(os.path.join(app_path, 'PyQt5', 'Qt', 'plugins'))

    # 创建应用
    app = QApplication(sys.argv)

    # 设置字体 - 使用系统默认字体，确保在桌面应用中显示合适
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # 创建主窗口
    player = SodaPlayer()
    player.show()

    # 运行
    sys.exit(app.exec_())

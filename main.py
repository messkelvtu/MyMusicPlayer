import sys
import os
import json
import shutil
import random
import re
import urllib.request
import urllib.parse
import time
from datetime import datetime

# 确保先导入PyQt5相关模块
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QFileDialog, QFrame, QAbstractItemView, QCheckBox,
                             QGraphicsDropShadowEffect, QInputDialog, QMessageBox, 
                             QFontDialog, QMenu, QAction, QSlider, QDialog, QRadioButton, 
                             QComboBox, QLineEdit, QTabWidget, QSpinBox, QColorDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
                             QProgressBar, QScrollArea, QSizePolicy, QTextEdit,
                             QButtonGroup, QToolButton, QStackedWidget, QSplitter)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize, QCoreApplication, QTimer, QRect, QSettings, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QColor, QPalette, QLinearGradient, QPainter, QIcon, QPixmap, QCursor
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

# --- 2025年现代化UI样式表 ---
STYLESHEET = """
/* 主窗口样式 - 现代化毛玻璃效果 */
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                               stop:0 #0f0f23, stop:0.5 #1a1a2e, stop:1 #16213e);
    font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif;
    color: #ffffff;
    border-radius: 16px;
}

/* 侧边栏样式 - 现代化毛玻璃效果 */
QFrame#Sidebar {
    background: rgba(255, 255, 255, 0.08);
    border-right: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px 0 0 16px;
}

QLabel#Logo {
    font-size: 24px;
    font-weight: 700;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #00d2ff, stop:1 #3a7bd5);
    -webkit-background-clip: text;
    color: transparent;
    padding: 25px 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

QLabel#SectionTitle {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.5);
    padding: 20px 20px 8px 20px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* 现代化导航按钮 */
QPushButton.NavBtn {
    background: transparent;
    border: none;
    text-align: left;
    padding: 14px 20px;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.8);
    border-radius: 12px;
    margin: 4px 15px;
    transition: all 0.3s ease;
    font-weight: 500;
}

QPushButton.NavBtn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #ffffff;
    transform: translateX(5px);
}

QPushButton.NavBtn:checked {
    background: rgba(58, 123, 213, 0.3);
    color: #00d2ff;
    font-weight: 600;
    border-left: 3px solid #00d2ff;
}

/* 现代化下载按钮 */
QPushButton#DownloadBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #00d2ff, stop:1 #3a7bd5);
    color: white;
    font-weight: 600;
    border-radius: 25px;
    margin: 20px 15px;
    padding: 14px;
    border: none;
    font-size: 14px;
    min-height: 25px;
    box-shadow: 0 4px 15px rgba(0, 210, 255, 0.3);
}

QPushButton#DownloadBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #3a7bd5, stop:1 #00d2ff);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 210, 255, 0.4);
}

/* 现代化表格样式 */
QTableWidget {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    margin: 15px;
    selection-background-color: rgba(0, 210, 255, 0.2);
    selection-color: #00d2ff;
    gridline-color: rgba(255, 255, 255, 0.05);
    outline: none;
    font-size: 13px;
}

QHeaderView::section {
    background: rgba(255, 255, 255, 0.08);
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding: 15px 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
    font-size: 12px;
}

QTableWidget::item {
    padding: 12px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.9);
}

QTableWidget::item:selected {
    background: rgba(0, 210, 255, 0.15);
    color: #00d2ff;
    border-radius: 6px;
}

QTableWidget::item:hover {
    background: rgba(255, 255, 255, 0.05);
}

/* 现代化歌词面板 */
QListWidget#LyricPanel {
    background: transparent;
    border: none;
    outline: none;
    font-size: 15px;
    color: rgba(255, 255, 255, 0.6);
}

QListWidget#LyricPanel::item {
    padding: 16px 20px;
    border: none;
    background: transparent;
    text-align: center;
    color: rgba(255, 255, 255, 0.6);
    border-radius: 8px;
    margin: 2px 10px;
}

QListWidget#LyricPanel::item:selected {
    background: rgba(0, 210, 255, 0.2);
    color: #00d2ff;
    font-weight: 700;
    font-size: 18px;
}

QListWidget#LyricPanel::item:hover {
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.8);
}

/* 现代化播放控制栏 */
QFrame#PlayerBar {
    background: rgba(255, 255, 255, 0.08);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0 0 16px 0;
}

QPushButton#PlayBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                               stop:0 #00d2ff, stop:1 #3a7bd5);
    color: white;
    border-radius: 50%;
    font-size: 18px;
    min-width: 60px;
    min-height: 60px;
    border: none;
    box-shadow: 0 8px 25px rgba(0, 210, 255, 0.4);
}

QPushButton#PlayBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                               stop:0 #3a7bd5, stop:1 #00d2ff);
    transform: scale(1.1);
    box-shadow: 0 12px 30px rgba(0, 210, 255, 0.6);
}

QPushButton.CtrlBtn {
    background: rgba(255, 255, 255, 0.1);
    border: none;
    font-size: 20px;
    color: rgba(255, 255, 255, 0.8);
    border-radius: 50%;
    padding: 10px;
    min-width: 44px;
    min-height: 44px;
}

QPushButton.CtrlBtn:hover {
    color: #00d2ff;
    background: rgba(0, 210, 255, 0.2);
    transform: scale(1.1);
}

QPushButton.OffsetBtn {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 20px;
    color: rgba(255, 255, 255, 0.8);
    font-size: 12px;
    padding: 8px 16px;
}

QPushButton.OffsetBtn:hover {
    background: #00d2ff;
    border-color: #00d2ff;
    color: #0f0f23;
}

/* 现代化进度条 */
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: rgba(255, 255, 255, 0.1);
    margin: 0px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    border: 3px solid #00d2ff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #00d2ff, stop:1 #3a7bd5);
    border-radius: 3px;
}

/* 音量滑块 */
QSlider#VolumeSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: rgba(255, 255, 255, 0.1);
    margin: 0px;
    border-radius: 2px;
}

QSlider#VolumeSlider::handle:horizontal {
    background: #ffffff;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 2px solid #00d2ff;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

QSlider#VolumeSlider::sub-page:horizontal {
    background: #00d2ff;
    border-radius: 2px;
}

/* 现代化输入控件 */
QLineEdit, QComboBox, QTextEdit {
    padding: 12px 16px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.08);
    color: #ffffff;
    font-size: 14px;
    selection-background-color: rgba(0, 210, 255, 0.3);
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border-color: #00d2ff;
    background: rgba(255, 255, 255, 0.12);
    outline: none;
}

QLineEdit::placeholder {
    color: rgba(255, 255, 255, 0.4);
}

QComboBox::drop-down {
    border: none;
    width: 35px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 6px solid rgba(255, 255, 255, 0.6);
    width: 0px;
    height: 0px;
}

QComboBox QAbstractItemView {
    background: rgba(40, 40, 60, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    color: white;
    selection-background-color: rgba(0, 210, 255, 0.3);
}

/* 现代化对话框 */
QDialog {
    background: rgba(40, 40, 60, 0.95);
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

QGroupBox {
    font-weight: 600;
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    margin-top: 10px;
    padding-top: 15px;
    background: rgba(255, 255, 255, 0.05);
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 10px;
    color: rgba(255, 255, 255, 0.8);
}

/* 现代化按钮 */
QPushButton {
    padding: 10px 20px;
    border-radius: 10px;
    font-size: 14px;
    border: none;
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
    font-weight: 500;
}

QPushButton:hover {
    background: rgba(255, 255, 255, 0.15);
}

QPushButton:pressed {
    background: rgba(255, 255, 255, 0.2);
}

QPushButton[style*="primary"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d2ff, stop:1 #3a7bd5);
    color: white;
}

QPushButton[style*="primary"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a7bd5, stop:1 #00d2ff);
}

/* 现代化标签页 */
QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.05);
}

QTabWidget::tab-bar {
    alignment: center;
}

QTabBar::tab {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-bottom: none;
    padding: 10px 20px;
    margin-right: 3px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    color: rgba(255, 255, 255, 0.7);
}

QTabBar::tab:selected {
    background: rgba(0, 210, 255, 0.2);
    border-color: rgba(0, 210, 255, 0.3);
    border-bottom: 1px solid rgba(0, 210, 255, 0.2);
    color: #00d2ff;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background: rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.9);
}

/* 现代化复选框和单选框 */
QCheckBox, QRadioButton {
    spacing: 12px;
    color: rgba(255, 255, 255, 0.9);
    font-weight: 500;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 20px;
    height: 20px;
    border-radius: 5px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    background: rgba(255, 255, 255, 0.1);
}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: #00d2ff;
    border: 2px solid #00d2ff;
}

QRadioButton::indicator {
    border-radius: 10px;
}

QRadioButton::indicator:checked {
    background: #00d2ff;
    border: 2px solid #00d2ff;
}

/* 现代化滚动条 */
QScrollBar:vertical {
    border: none;
    background: rgba(255, 255, 255, 0.05);
    width: 12px;
    margin: 0px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    min-height: 25px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(0, 210, 255, 0.6);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}

/* 现代化进度条 */
QProgressBar {
    border: none;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    text-align: center;
    color: white;
    font-size: 12px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #00d2ff, stop:1 #3a7bd5);
    border-radius: 6px;
}

/* 现代化菜单 */
QMenu {
    background: rgba(40, 40, 60, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 8px;
    color: white;
}

QMenu::item {
    padding: 8px 16px;
    border-radius: 6px;
    margin: 2px;
}

QMenu::item:selected {
    background: rgba(0, 210, 255, 0.3);
    color: #00d2ff;
}

QMenu::separator {
    height: 1px;
    background: rgba(255, 255, 255, 0.1);
    margin: 5px 10px;
}

/* 现代化消息框 */
QMessageBox {
    background: rgba(40, 40, 60, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
}

QMessageBox QLabel {
    color: white;
}
"""

def sanitize_filename(name):
    """清理文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def ms_to_str(ms):
    """毫秒转换为时间字符串"""
    s = ms // 1000
    return f"{s//60:02}:{s%60:02}"

# --- 在线歌词搜索线程 ---
class LyricListSearchWorker(QThread):
    search_finished = pyqtSignal(list)

    def __init__(self, keyword):
        super().__init__()
        self.keyword = keyword

    def run(self):
        try:
            url = "http://music.163.com/api/search/get/web?csrf_token="
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            data = urllib.parse.urlencode({'s': self.keyword, 'type': 1, 'offset': 0, 'total': 'true', 'limit': 20}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as f:
                res = json.loads(f.read().decode('utf-8'))
            
            results = []
            if res.get('result') and res['result'].get('songs'):
                for s in res['result']['songs']:
                    artists = [art['name'] for art in s.get('artists', [])]
                    artist = ' / '.join(artists) if artists else "未知"
                    album = s.get('album', {}).get('name', '未知专辑')
                    duration = s.get('duration', 0)
                    results.append({
                        'name': s['name'],
                        'artist': artist,
                        'album': album,
                        'id': s['id'],
                        'duration': duration,
                        'duration_str': ms_to_str(duration)
                    })
            self.search_finished.emit(results)
        except Exception as e:
            print(f"搜索错误: {e}")
            self.search_finished.emit([])

# --- 桌面歌词窗口 ---
class DesktopLyricWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1200, 180)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        self.font_color = QColor(0, 210, 255)  # 现代化蓝色主题
        self.current_font = QFont("Microsoft YaHei", 36, QFont.Bold)
        
        self.labels = []
        for i in range(3):
            lbl = QLabel("")
            lbl.setAlignment(Qt.AlignCenter)
            self.labels.append(lbl)
            self.layout.addWidget(lbl)
        
        self.update_styles()
        self.locked = False

    def update_styles(self):
        base_size = self.current_font.pointSize()
        shadow_color = QColor(0, 0, 0, 200)
        for i, lbl in enumerate(self.labels):
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(8)
            effect.setColor(shadow_color)
            effect.setOffset(1, 1)
            lbl.setGraphicsEffect(effect)
            f = QFont(self.current_font)
            color_css = self.font_color.name()
            if i == 1:
                f.setPointSize(base_size)
                lbl.setStyleSheet(f"color: {color_css};")
            else:
                f.setPointSize(int(base_size * 0.6))
                r,g,b = self.font_color.red(), self.font_color.green(), self.font_color.blue()
                lbl.setStyleSheet(f"color: rgba({r}, {g}, {b}, 160);")
            lbl.setFont(f)

    def set_lyrics(self, p, c, n):
        self.labels[0].setText(p)
        self.labels[1].setText(c)
        self.labels[2].setText(n)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.locked:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self.show_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.locked:
            self.move(event.globalPos() - self.drag_pos)

    def wheelEvent(self, event):
        d = event.angleDelta().y()
        s = self.current_font.pointSize()
        self.current_font.setPointSize(min(120, s+2) if d>0 else max(15, s-2))
        self.update_styles()

    def show_menu(self, pos):
        menu = QMenu()
        act_color = menu.addAction("🎨 修改颜色")
        act_font = menu.addAction("🅰️ 修改字体")
        lock_text = "🔒 解锁位置" if self.locked else "🔒 锁定位置"
        act_lock = menu.addAction(lock_text)
        act_close = menu.addAction("❌ 隐藏歌词")
        action = menu.exec_(pos)
        if action == act_color:
            c = QColorDialog.getColor(self.font_color, self)
            if c.isValid():
                self.font_color = c
                self.update_styles()
        elif action == act_font:
            f, ok = QFontDialog.getFont(self.current_font, self)
            if ok:
                self.current_font = f
                self.update_styles()
        elif action == act_lock:
            self.locked = not self.locked
        elif action == act_close:
            self.hide()

# --- B站下载线程 ---
class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str, list)
    error_signal = pyqtSignal(str)

    def __init__(self, url, save_path, mode="single", start_p=1, metadata=None):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.mode = mode
        self.start_p = start_p
        self.metadata = metadata or {}

    def run(self):
        if not yt_dlp:
            self.error_signal.emit("错误：缺少 yt-dlp 库")
            return
            
        if not os.path.exists(self.save_path):
            try:
                os.makedirs(self.save_path)
            except Exception as e:
                self.error_signal.emit(f"无法创建文件夹: {e}")
                return

        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%').strip()
                fn = os.path.basename(d.get('filename', '未知'))
                if len(fn) > 20:
                    fn = fn[:20] + "..."
                self.progress_signal.emit(f"⬇️ {p} : {fn}")
            elif d['status'] == 'finished':
                self.progress_signal.emit("✅ 下载完成，处理中...")

        items_range = str(self.start_p) if self.mode == 'single' else f"{self.start_p}:"
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best[height<=720]',
            'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
            'overwrites': True,
            'noplaylist': self.mode == 'single',
            'playlist_items': items_range,
            'ignoreerrors': True,
            'progress_hooks': [progress_hook],
            'quiet': False,
            'nocheckcertificate': True,
            'restrictfilenames': False,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }],
        }
        
        try:
            self.progress_signal.emit("🔍 开始解析视频信息...")
            downloaded_files = []
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息
                info = ydl.extract_info(self.url, download=False)
                
                if self.mode == 'playlist' and 'entries' in info:
                    total = len(info['entries'])
                    self.progress_signal.emit(f"📺 发现 {total} 个视频，开始下载...")
                
                # 开始下载
                ydl.download([self.url])
                
                # 获取下载的文件列表
                for f in os.listdir(self.save_path):
                    if f.endswith(('.m4a', '.mp3', '.mp4')):
                        downloaded_files.append(f)
                        
            self.progress_signal.emit("🎉 所有任务完成")
            self.finished_signal.emit(self.save_path, downloaded_files)
            
        except Exception as e:
            self.error_signal.emit(f"下载失败: {str(e)}")

# --- 增强版智能重命名解析器 ---
class EnhancedSmartNamingParser:
    def __init__(self):
        self.bilibili_keywords = [
            '官方', 'MV', '高清', '4K', '修复', '音质', '完整版', 
            '无水印', '首发', '首发音乐', '超清', '极致音质', '无损',
            '【', '】', '[]', '()', '（）', '1080p', '720p', 'P1', 'P2', 'P3'
        ]
        self.common_patterns = [
            # 优先级从高到低
            (r'^(.*?)[-—~]\s*(.*?)(?:\s*\[.*?\])?$', "artist - song"),  # 歌手 - 歌曲
            (r'^(.*?)\s*《(.*?)》', "artist《song》"),  # 歌手《歌曲》
            (r'^(.*?)\s*[(（](.*?)[)）]', "artist(song)"),  # 歌手(歌曲)
            (r'^(.*?)\s*-\s*(.*?)$', "artist - song"),  # 歌手 - 歌曲
        ]
        
    def parse_filename(self, filename):
        """解析文件名，提取歌曲信息"""
        name_without_ext = os.path.splitext(filename)[0]
        cleaned_name = self.clean_special_chars(name_without_ext)
        
        # 尝试多种模式匹配
        for pattern, pattern_type in self.common_patterns:
            match = re.match(pattern, cleaned_name)
            if match:
                artist = match.group(1).strip()
                song = match.group(2).strip()
                
                artist = self.clean_common_noise(artist)
                song = self.clean_common_noise(song)
                
                if artist and song:
                    return {
                        'artist': artist, 
                        'song': song, 
                        'confidence': 'high',
                        'pattern': pattern_type
                    }
        
        # 如果无法解析，使用备选策略
        return self.fallback_parse(cleaned_name)
    
    def clean_special_chars(self, text):
        """清理特殊字符和B站标记"""
        # 移除B站关键词
        for keyword in self.bilibili_keywords:
            text = text.replace(keyword, '')
        
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)
        
        # 移除首尾的特殊字符
        text = re.sub(r'^[^\w\u4e00-\u9fff]+|[^\w\u4e00-\u9fff]+$', '', text)
        
        return text.strip()
    
    def clean_common_noise(self, text):
        """清理常见噪音"""
        # 移除版本信息
        text = re.sub(r'(?i)\b(ver|version|mix|remix|cover)\b.*$', '', text)
        
        # 移除质量标记
        text = re.sub(r'(?i)\b(\d+kbps|\d+bit|hi-res|master)\b', '', text)
        
        return text.strip()
    
    def fallback_parse(self, text):
        """备选解析策略"""
        # 按常见分隔符分割
        separators = [' - ', ' _ ', ' ', '·']
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                if len(parts) >= 2:
                    # 假设最后一部分是歌曲名
                    song = parts[-1]
                    artist = sep.join(parts[:-1])
                    return {
                        'artist': artist, 
                        'song': song, 
                        'confidence': 'medium',
                        'pattern': f'separator: {sep}'
                    }
        
        # 如果文本较短，直接作为歌曲名
        if len(text) <= 25:
            return {
                'artist': '未知歌手', 
                'song': text, 
                'confidence': 'low',
                'pattern': 'fallback'
            }
        
        return {
            'artist': '未知歌手', 
            'song': text, 
            'confidence': 'low',
            'pattern': 'fallback'
        }

# --- 现代化批量重命名对话框 ---
class ModernBatchRenameDialog(QDialog):
    def __init__(self, file_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("智能批量重命名")
        self.resize(1000, 700)
        self.setStyleSheet(STYLESHEET)
        
        self.file_list = file_list
        self.parser = EnhancedSmartNamingParser()
        self.results = []
        
        self.init_ui()
        self.analyze_files()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("🔤 智能批量重命名")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 20px;
                color: rgba(255, 255, 255, 0.6);
                border-radius: 15px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)
        layout.addLayout(title_layout)
        
        # 策略选择区域
        strategy_container = QWidget()
        strategy_container.setStyleSheet("background: rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 15px;")
        strategy_layout = QVBoxLayout(strategy_container)
        
        strategy_label = QLabel("🎯 重命名策略")
        strategy_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        strategy_layout.addWidget(strategy_label)
        
        strategy_buttons_layout = QHBoxLayout()
        
        self.auto_radio = QRadioButton("🔍 智能分析 + 预览确认")
        self.manual_radio = QRadioButton("✏️ 手动逐个确认") 
        self.prefix_radio = QRadioButton("🔄 前缀替换模式")
        
        self.auto_radio.setChecked(True)
        self.auto_radio.toggled.connect(self.on_strategy_changed)
        self.prefix_radio.toggled.connect(self.on_strategy_changed)
        
        strategy_buttons_layout.addWidget(self.auto_radio)
        strategy_buttons_layout.addWidget(self.manual_radio)
        strategy_buttons_layout.addWidget(self.prefix_radio)
        strategy_buttons_layout.addStretch()
        
        strategy_layout.addLayout(strategy_buttons_layout)
        
        # 前缀替换选项（默认隐藏）
        self.prefix_container = QWidget()
        self.prefix_container.hide()
        prefix_layout = QHBoxLayout(self.prefix_container)
        
        prefix_layout.addWidget(QLabel("查找前缀:"))
        self.prefix_find = QLineEdit()
        self.prefix_find.setPlaceholderText("例如: 【B站搬运】")
        prefix_layout.addWidget(self.prefix_find)
        
        prefix_layout.addWidget(QLabel("替换为:"))
        self.prefix_replace = QLineEdit()
        self.prefix_replace.setPlaceholderText("例如: 翻唱-")
        prefix_layout.addWidget(self.prefix_replace)
        
        btn_test = QPushButton("测试替换")
        btn_test.clicked.connect(self.test_prefix_replace)
        prefix_layout.addWidget(btn_test)
        
        strategy_layout.addWidget(self.prefix_container)
        layout.addWidget(strategy_container)
        
        # 文件预览表格
        table_container = QWidget()
        table_container.setStyleSheet("background: rgba(255, 255, 255, 0.05); border-radius: 12px;")
        table_layout = QVBoxLayout(table_container)
        
        # 表格标题
        table_header = QLabel(f"📁 共 {len(self.file_list)} 个文件待处理")
        table_header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.1);")
        table_layout.addWidget(table_header)
        
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(6)
        self.preview_table.setHorizontalHeaderLabels([
            "原文件名", "歌手", "歌曲名", "匹配模式", "置信度", "操作"
        ])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.preview_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.preview_table)
        
        layout.addWidget(table_container, 1)
        
        # 按钮区域
        btn_container = QWidget()
        btn_container.setStyleSheet("background: rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 15px;")
        btn_layout = QHBoxLayout(btn_container)
        
        self.btn_apply_all = QPushButton("🚀 应用所有推荐")
        self.btn_apply_all.setStyleSheet("background: #00d2ff; color: white; font-weight: bold; padding: 12px 24px;")
        self.btn_apply_all.clicked.connect(self.apply_all)
        
        self.btn_apply_selected = QPushButton("✅ 应用选中项")
        self.btn_apply_selected.setStyleSheet("background: #00d2ff; color: white; font-weight: bold; padding: 12px 24px;")
        self.btn_apply_selected.clicked.connect(self.apply_selected)
        
        self.btn_manual_edit = QPushButton("✏️ 手动编辑选中")
        self.btn_manual_edit.setStyleSheet("padding: 12px 24px;")
        self.btn_manual_edit.clicked.connect(self.manual_edit)
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setStyleSheet("padding: 12px 24px;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_apply_all)
        btn_layout.addWidget(self.btn_apply_selected)
        btn_layout.addWidget(self.btn_manual_edit)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addWidget(btn_container)
    
    def on_strategy_changed(self):
        """策略改变时的处理"""
        if self.prefix_radio.isChecked():
            self.prefix_container.show()
            self.analyze_files_with_prefix()
        else:
            self.prefix_container.hide()
            self.analyze_files()
    
    def analyze_files(self):
        """智能分析所有文件"""
        self.results = []
        self.preview_table.setRowCount(len(self.file_list))
        
        for i, file_info in enumerate(self.file_list):
            filename = file_info["name"]
            file_path = file_info["path"]
            
            result = self.parser.parse_filename(filename)
            result['original_name'] = filename
            result['file_path'] = file_path
            result['new_name'] = f"{result['artist']} - {result['song']}{os.path.splitext(filename)[1]}"
            self.results.append(result)
            
            self.update_table_row(i, result)
    
    def analyze_files_with_prefix(self):
        """前缀替换模式分析"""
        self.results = []
        self.preview_table.setRowCount(len(self.file_list))
        
        find_text = self.prefix_find.text().strip()
        replace_text = self.prefix_replace.text().strip()
        
        for i, file_info in enumerate(self.file_list):
            filename = file_info["name"]
            file_path = file_info["path"]
            
            new_name = filename
            if find_text and find_text in filename:
                new_name = filename.replace(find_text, replace_text)
            
            result = {
                'original_name': filename,
                'file_path': file_path,
                'new_name': new_name,
                'artist': '前缀替换',
                'song': os.path.splitext(new_name)[0],
                'confidence': 'high',
                'pattern': f'前缀替换: {find_text} -> {replace_text}'
            }
            self.results.append(result)
            
            self.update_table_row(i, result)
    
    def update_table_row(self, index, result):
        """更新表格行"""
        self.preview_table.setItem(index, 0, QTableWidgetItem(result['original_name']))
        self.preview_table.setItem(index, 1, QTableWidgetItem(result['artist']))
        self.preview_table.setItem(index, 2, QTableWidgetItem(result['song']))
        self.preview_table.setItem(index, 3, QTableWidgetItem(result.get('pattern', '')))
        
        confidence_item = QTableWidgetItem()
        confidence_item.setTextAlignment(Qt.AlignCenter)
        if result['confidence'] == 'high':
            confidence_item.setText("高")
            confidence_item.setForeground(QColor("#00d2ff"))
            confidence_item.setBackground(QColor("rgba(0, 210, 255, 0.2)"))
        elif result['confidence'] == 'medium':
            confidence_item.setText("中")
            confidence_item.setForeground(QColor("#ff6b35"))
            confidence_item.setBackground(QColor("rgba(255, 107, 53, 0.2)"))
        else:
            confidence_item.setText("低")
            confidence_item.setForeground(QColor("rgba(255, 255, 255, 0.5)"))
            confidence_item.setBackground(QColor("rgba(255, 255, 255, 0.1)"))
        self.preview_table.setItem(index, 4, confidence_item)
        
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(5, 2, 5, 2)
        btn_layout.setSpacing(5)
        
        btn_accept = QPushButton("✓")
        btn_accept.setFixedSize(28, 28)
        btn_accept.setStyleSheet("""
            QPushButton {
                background: #00d2ff;
                color: white;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3a7bd5;
            }
        """)
        btn_accept.clicked.connect(lambda checked, idx=index: self.accept_single(idx))
        
        btn_edit = QPushButton("✎")
        btn_edit.setFixedSize(28, 28)
        btn_edit.setStyleSheet("""
            QPushButton {
                background: #ff6b35;
                color: white;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e55a2b;
            }
        """)
        btn_edit.clicked.connect(lambda checked, idx=index: self.edit_single(idx))
        
        btn_layout.addWidget(btn_accept)
        btn_layout.addWidget(btn_edit)
        btn_layout.addStretch()
        
        self.preview_table.setCellWidget(index, 5, btn_widget)
    
    def test_prefix_replace(self):
        """测试前缀替换效果"""
        find_text = self.prefix_find.text().strip()
        if not find_text:
            self.show_message("提示", "请输入要查找的前缀")
            return
        
        self.analyze_files_with_prefix()
    
    def accept_single(self, index):
        """接受单个文件的推荐"""
        result = self.results[index]
        try:
            old_path = result['file_path']
            new_path = os.path.join(os.path.dirname(old_path), result['new_name'])
            
            if old_path != new_path:
                os.rename(old_path, new_path)
                self.file_list[index]["name"] = result['new_name']
                self.file_list[index]["path"] = new_path
                
                item = self.preview_table.item(index, 0)
                item.setText(result['new_name'])
                item.setForeground(QColor("#00d2ff"))
                
                self.preview_table.item(index, 4).setText("已处理")
                self.preview_table.item(index, 4).setBackground(QColor("rgba(0, 210, 255, 0.2)"))
                
        except Exception as e:
            self.show_message("错误", f"重命名失败: {str(e)}")
    
    def edit_single(self, index):
        """编辑单个文件信息"""
        result = self.results[index]
        
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle("编辑文件信息")
        edit_dialog.resize(500, 300)
        edit_dialog.setStyleSheet(STYLESHEET)
        
        layout = QVBoxLayout(edit_dialog)
        
        original_label = QLabel(f"原文件: {result['original_name']}")
        original_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); padding: 10px; background: rgba(255, 255, 255, 0.05); border-radius: 6px;")
        layout.addWidget(original_label)
        
        form_layout = QVBoxLayout()
        
        artist_layout = QHBoxLayout()
        artist_layout.addWidget(QLabel("歌手:"))
        edit_artist = QLineEdit(result['artist'])
        edit_artist.setMinimumHeight(40)
        artist_layout.addWidget(edit_artist)
        form_layout.addLayout(artist_layout)
        
        song_layout = QHBoxLayout()
        song_layout.addWidget(QLabel("歌曲名:"))
        edit_song = QLineEdit(result['song'])
        edit_song.setMinimumHeight(40)
        song_layout.addWidget(edit_song)
        form_layout.addLayout(song_layout)
        
        layout.addLayout(form_layout)
        
        preview_label = QLabel()
        preview_label.setStyleSheet("color: #00d2ff; font-weight: bold; padding: 10px;")
        
        def update_preview():
            new_name = f"{edit_artist.text()} - {edit_song.text()}{os.path.splitext(result['original_name'])[1]}"
            preview_label.setText(f"新文件名: {new_name}")
        
        edit_artist.textChanged.connect(update_preview)
        edit_song.textChanged.connect(update_preview)
        update_preview()
        
        layout.addWidget(preview_label)
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("确定")
        btn_ok.setStyleSheet("background: #00d2ff; color: white; font-weight: bold; padding: 10px 20px;")
        btn_ok.clicked.connect(edit_dialog.accept)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.setStyleSheet("padding: 10px 20px;")
        btn_cancel.clicked.connect(edit_dialog.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        if edit_dialog.exec_() == QDialog.Accepted:
            result['artist'] = edit_artist.text()
            result['song'] = edit_song.text()
            result['new_name'] = f"{result['artist']} - {result['song']}{os.path.splitext(result['original_name'])[1]}"
            
            self.preview_table.setItem(index, 1, QTableWidgetItem(result['artist']))
            self.preview_table.setItem(index, 2, QTableWidgetItem(result['song']))
    
    def apply_all(self):
        """应用所有推荐"""
        reply = self.show_confirm_message("确认批量重命名", 
                                        f"确定要应用所有推荐的重命名吗？共 {len(self.results)} 个文件")
        if reply == QMessageBox.Yes:
            success_count = 0
            for i, result in enumerate(self.results):
                try:
                    old_path = result['file_path']
                    new_path = os.path.join(os.path.dirname(old_path), result['new_name'])
                    
                    if old_path != new_path:
                        os.rename(old_path, new_path)
                        success_count += 1
                        self.file_list[i]["name"] = result['new_name']
                        self.file_list[i]["path"] = new_path
                        
                except Exception as e:
                    print(f"重命名失败 {result['original_name']}: {e}")
            
            self.show_message("完成", f"成功重命名 {success_count} 个文件")
            self.accept()
    
    def apply_selected(self):
        """应用选中的推荐"""
        selected_rows = set(index.row() for index in self.preview_table.selectedIndexes())
        if not selected_rows:
            self.show_message("提示", "请先选择要重命名的文件")
            return
        
        reply = self.show_confirm_message("确认重命名", 
                                        f"确定要重命名选中的 {len(selected_rows)} 个文件吗？")
        if reply != QMessageBox.Yes:
            return
        
        success_count = 0
        for row in selected_rows:
            try:
                result = self.results[row]
                old_path = result['file_path']
                new_path = os.path.join(os.path.dirname(old_path), result['new_name'])
                
                if old_path != new_path:
                    os.rename(old_path, new_path)
                    success_count += 1
                    self.file_list[row]["name"] = result['new_name']
                    self.file_list[row]["path"] = new_path
                    
            except Exception as e:
                print(f"重命名失败 {result['original_name']}: {e}")
        
        self.show_message("完成", f"成功重命名 {success_count} 个文件")
        self.accept()
    
    def manual_edit(self):
        """手动编辑选中项"""
        selected_rows = set(index.row() for index in self.preview_table.selectedIndexes())
        if not selected_rows:
            self.show_message("提示", "请先选择要编辑的文件")
            return
        
        for row in selected_rows:
            self.edit_single(row)
    
    def show_message(self, title, message):
        """显示现代化消息框"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStyleSheet(STYLESHEET)
        return msg.exec_()
    
    def show_confirm_message(self, title, message):
        """显示确认对话框"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.setStyleSheet(STYLESHEET)
        return msg.exec_()

# --- 现代化主程序 ---
class ModernSodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 - 2025现代化音乐播放器")
        
        # 获取屏幕分辨率并设置窗口大小
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        self.screen_width = screen_rect.width()
        self.screen_height = screen_rect.height()
        
        # 根据屏幕分辨率设置窗口大小
        if self.screen_width >= 3840:  # 4K
            self.resize(1600, 1000)
        elif self.screen_width >= 2560:  # 2K
            self.resize(1400, 900)
        else:  # 1080p
            self.resize(1200, 800)
            
        # 居中显示
        self.move((screen_rect.width() - self.width()) // 2, 
                 (screen_rect.height() - self.height()) // 2)
        
        self.setStyleSheet(STYLESHEET)

        # 初始化变量
        self.music_folder = ""
        self.current_collection = "" 
        self.collections = [] 
        self.playlist = [] 
        self.history = []
        self.lyrics = []
        self.current_index = -1
        self.offset = 0.0
        self.volume = 50
        
        self.saved_offsets = {}
        self.metadata = {} 

        self.mode = 0
        self.rate = 1.0 
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
        self.desktop_lyric = DesktopLyricWindow()
        
        self.init_ui()
        self.load_config()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === 现代化侧边栏 ===
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # logo区域
        logo = QLabel("🎵 汽水音乐 2025")
        logo.setObjectName("Logo")
        sidebar_layout.addWidget(logo)
        
        # 功能按钮区域
        function_container = QWidget()
        function_layout = QVBoxLayout(function_container)
        function_layout.setContentsMargins(15, 0, 15, 0)
        function_layout.setSpacing(8)
        
        self.btn_bili = QPushButton("📥 B站音频下载")
        self.btn_bili.setObjectName("DownloadBtn")
        self.btn_bili.clicked.connect(self.download_from_bilibili)
        function_layout.addWidget(self.btn_bili)
        
        btn_refresh = QPushButton("🔄 刷新音乐库")
        btn_refresh.setProperty("NavBtn", True)
        btn_refresh.clicked.connect(self.full_scan)
        function_layout.addWidget(btn_refresh)
        
        btn_smart_rename = QPushButton("🔤 智能重命名")
        btn_smart_rename.setProperty("NavBtn", True)
        btn_smart_rename.clicked.connect(self.open_smart_rename)
        function_layout.addWidget(btn_smart_rename)
        
        sidebar_layout.addWidget(function_container)
        
        # 音乐库导航
        sidebar_layout.addWidget(QLabel("音乐库", objectName="SectionTitle"))
        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 20px;
                border: none;
                background: transparent;
                color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
            }
            QListWidget::item:selected {
                background: rgba(0, 210, 255, 0.2);
                color: #00d2ff;
                border-left: 3px solid #00d2ff;
                font-weight: 600;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        self.nav_list.itemClicked.connect(self.switch_collection)
        sidebar_layout.addWidget(self.nav_list)
        
        # 底部按钮组
        sidebar_layout.addStretch()
        btn_group = QWidget()
        btn_group.setStyleSheet("background: rgba(255, 255, 255, 0.05); border-top: 1px solid rgba(255, 255, 255, 0.1);")
        btn_group_layout = QVBoxLayout(btn_group)
        btn_group_layout.setContentsMargins(15, 15, 15, 15)
        btn_group_layout.setSpacing(8)
        
        btn_folder = QPushButton("📁 设置根目录")
        btn_folder.setProperty("NavBtn", True)
        btn_folder.clicked.connect(self.select_folder)
        btn_group_layout.addWidget(btn_folder)
        
        btn_lyric = QPushButton("💬 桌面歌词")
        btn_lyric.setProperty("NavBtn", True)
        btn_lyric.clicked.connect(self.toggle_lyric)
        btn_group_layout.addWidget(btn_lyric)
        
        sidebar_layout.addWidget(btn_group)
        layout.addWidget(sidebar)

        # === 右侧主区域 ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # 现代化标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(70)
        title_bar.setStyleSheet("background: rgba(255,255,255,0.08); border-bottom: 1px solid rgba(255,255,255,0.1);")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(25, 0, 25, 0)
        
        self.lbl_collection_title = QLabel("全部音乐")
        self.lbl_collection_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        title_layout.addWidget(self.lbl_collection_title)
        title_layout.addStretch()
        
        # 现代化搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 搜索歌曲、歌手或专辑...")
        self.search_box.setFixedWidth(280)
        self.search_box.setMinimumHeight(36)
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 8px 16px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 18px;
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #00d2ff;
                background: rgba(255, 255, 255, 0.12);
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.4);
            }
        """)
        self.search_box.textChanged.connect(self.search_songs)
        title_layout.addWidget(self.search_box)
        
        right_layout.addWidget(title_bar)

        # 内容区域
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 现代化歌曲列表
        list_container = QWidget()
        list_container.setStyleSheet("background: transparent;")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["歌曲标题", "歌手", "专辑", "时长"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(self.play_selected)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        list_layout.addWidget(self.table)
        
        content_layout.addWidget(list_container, stretch=6)
        
        # 现代化歌词面板
        lyric_container = QWidget()
        lyric_container.setFixedWidth(320)
        lyric_container.setStyleSheet("background: rgba(255,255,255,0.05); border-left: 1px solid rgba(255,255,255,0.1);")
        lyric_layout = QVBoxLayout(lyric_container)
        lyric_layout.setContentsMargins(0, 0, 0, 0)
        
        lyric_title = QLabel("🎤 歌词")
        lyric_title.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            color: #ffffff; 
            padding: 20px; 
            border-bottom: 1px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.08);
        """)
        lyric_layout.addWidget(lyric_title)
        
        self.panel_lyric = QListWidget()
        self.panel_lyric.setObjectName("LyricPanel")
        self.panel_lyric.setFocusPolicy(Qt.NoFocus)
        self.panel_lyric.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        lyric_layout.addWidget(self.panel_lyric)
        
        content_layout.addWidget(lyric_container)
        right_layout.addWidget(content, stretch=1)

        # === 现代化播放控制栏 ===
        player_bar = QFrame()
        player_bar.setObjectName("PlayerBar")
        player_bar.setFixedHeight(120)
        player_layout = QVBoxLayout(player_bar)
        player_layout.setContentsMargins(30, 15, 30, 15)
        
        # 进度条
        progress_layout = QHBoxLayout()
        self.lbl_curr_time = QLabel("00:00")
        self.lbl_curr_time.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px; min-width: 45px;")
        self.lbl_total_time = QLabel("00:00")
        self.lbl_total_time.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px; min-width: 45px;")
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderPressed.connect(self.slider_pressed)
        self.slider.sliderReleased.connect(self.slider_released)
        self.slider.valueChanged.connect(self.slider_moved)
        
        progress_layout.addWidget(self.lbl_curr_time)
        progress_layout.addWidget(self.slider, stretch=1)
        progress_layout.addWidget(self.lbl_total_time)
        player_layout.addLayout(progress_layout)
        
        # 控制按钮区域
        ctrl_container = QWidget()
        ctrl_layout = QHBoxLayout(ctrl_container)
        ctrl_layout.setContentsMargins(0, 10, 0, 10)
        
        # 左侧：播放模式
        self.btn_mode = QPushButton("🔁")
        self.btn_mode.setProperty("CtrlBtn", True)
        self.btn_mode.setToolTip("播放模式")
        self.btn_mode.clicked.connect(self.toggle_mode)
        ctrl_layout.addWidget(self.btn_mode)
        
        ctrl_layout.addSpacing(10)
        
        # 中间：播放控制
        btn_prev = QPushButton("⏮")
        btn_prev.setProperty("CtrlBtn", True)
        btn_prev.setToolTip("上一首")
        btn_prev.clicked.connect(self.play_prev)
        
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("PlayBtn")
        self.btn_play.setToolTip("播放/暂停")
        self.btn_play.clicked.connect(self.toggle_play)
        
        btn_next = QPushButton("⏭")
        btn_next.setProperty("CtrlBtn", True)
        btn_next.setToolTip("下一首")
        btn_next.clicked.connect(self.play_next)
        
        ctrl_layout.addWidget(btn_prev)
        ctrl_layout.addSpacing(5)
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addSpacing(5)
        ctrl_layout.addWidget(btn_next)
        
        ctrl_layout.addSpacing(20)
        
        # 右侧：音量和速度
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(8)
        
        btn_volume = QPushButton("🔊")
        btn_volume.setProperty("CtrlBtn", True)
        btn_volume.setToolTip("音量")
        btn_volume.setFixedSize(32, 32)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setObjectName("VolumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.volume)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        
        self.lbl_volume = QLabel(f"{self.volume}%")
        self.lbl_volume.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11px; min-width: 35px;")
        
        volume_layout.addWidget(btn_volume)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.lbl_volume)
        
        ctrl_layout.addLayout(volume_layout)
        
        ctrl_layout.addSpacing(15)
        
        self.btn_rate = QPushButton("1.0x")
        self.btn_rate.setProperty("CtrlBtn", True)
        self.btn_rate.setToolTip("播放速度")
        self.btn_rate.clicked.connect(self.toggle_rate)
        ctrl_layout.addWidget(self.btn_rate)
        
        ctrl_layout.addStretch()
        player_layout.addWidget(ctrl_container)
        
        # 偏移调整
        offset_layout = QHBoxLayout()
        offset_layout.addStretch()
        
        btn_slow = QPushButton("⏪ -0.5s")
        btn_slow.setProperty("OffsetBtn", True)
        btn_slow.clicked.connect(lambda: self.adjust_offset(-0.5))
        
        self.lbl_offset = QLabel("0.0s")
        self.lbl_offset.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11px; padding: 6px 12px; background: rgba(255, 255, 255, 0.1); border-radius: 12px;")
        
        btn_fast = QPushButton("+0.5s ⏩")
        btn_fast.setProperty("OffsetBtn", True)
        btn_fast.clicked.connect(lambda: self.adjust_offset(0.5))
        
        offset_layout.addWidget(btn_slow)
        offset_layout.addWidget(self.lbl_offset)
        offset_layout.addWidget(btn_fast)
        offset_layout.addStretch()
        
        player_layout.addLayout(offset_layout)
        right_layout.addWidget(player_bar)
        
        layout.addWidget(right_panel)

    # === 播放器控制方法 ===
    def on_volume_changed(self, value):
        """音量改变"""
        self.volume = value
        self.player.setVolume(value)
        self.lbl_volume.setText(f"{value}%")

    def on_position_changed(self, pos):
        """播放位置改变"""
        if not self.is_slider_pressed:
            self.slider.setValue(pos)
            
        self.lbl_curr_time.setText(ms_to_str(pos))
        
        current_sec = pos / 1000 + self.offset
        
        if self.lyrics:
            current_lyric_index = -1
            
            for i, lyric in enumerate(self.lyrics):
                if current_sec >= lyric["t"]:
                    current_lyric_index = i
                else:
                    break
            
            if current_lyric_index >= 0:
                if current_lyric_index < self.panel_lyric.count():
                    self.panel_lyric.setCurrentRow(current_lyric_index)
                    
                    self.panel_lyric.scrollToItem(
                        self.panel_lyric.item(current_lyric_index),
                        QAbstractItemView.PositionAtCenter
                    )
                
                prev_text = self.lyrics[current_lyric_index - 1]["txt"] if current_lyric_index > 0 else ""
                current_text = self.lyrics[current_lyric_index]["txt"]
                next_text = self.lyrics[current_lyric_index + 1]["txt"] if current_lyric_index < len(self.lyrics) - 1 else ""
                
                self.desktop_lyric.set_lyrics(prev_text, current_text, next_text)

    def on_duration_changed(self, duration):
        """歌曲时长改变"""
        self.slider.setRange(0, duration)
        self.lbl_total_time.setText(ms_to_str(duration))
        
        if self.current_index >= 0:
            self.table.setItem(self.current_index, 3, QTableWidgetItem(ms_to_str(duration)))
            self.playlist[self.current_index]["duration"] = ms_to_str(duration)

    def on_state_changed(self, state):
        """播放状态改变"""
        self.btn_play.setText("⏸" if state == QMediaPlayer.PlayingState else "▶")

    def on_media_status_changed(self, status):
        """媒体状态改变"""
        if status == QMediaPlayer.EndOfMedia:
            if self.mode == 1:
                self.player.play()
            else:
                self.play_next()

    def handle_player_error(self):
        """处理播放器错误"""
        error_msg = self.player.errorString()
        if error_msg:
            print(f"播放器错误: {error_msg}")
            self.show_modern_message("播放错误", f"无法播放当前文件: {error_msg}")
            QTimer.singleShot(1000, self.play_next)

    def slider_pressed(self):
        """进度条按下"""
        self.is_slider_pressed = True

    def slider_released(self):
        """进度条释放"""
        self.is_slider_pressed = False
        self.player.setPosition(self.slider.value())

    def slider_moved(self, value):
        """进度条移动"""
        if self.is_slider_pressed:
            self.lbl_curr_time.setText(ms_to_str(value))

    # === 播放控制方法 ===
    def toggle_play(self):
        """切换播放/暂停"""
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶")
        else:
            self.player.play()
            self.btn_play.setText("⏸")

    def toggle_mode(self):
        """切换播放模式"""
        self.mode = (self.mode + 1) % 3
        modes = ["🔁 顺序", "🔂 单曲", "🔀 随机"]
        self.btn_mode.setText(modes[self.mode])

    def toggle_rate(self):
        """切换播放速度"""
        rates = [1.0, 1.25, 1.5, 2.0, 0.5]
        try:
            current_index = rates.index(self.rate)
        except ValueError:
            current_index = 0
            
        self.rate = rates[(current_index + 1) % len(rates)]
        self.player.setPlaybackRate(self.rate)
        self.btn_rate.setText(f"{self.rate}x")

    def play_next(self):
        """播放下一首"""
        if not self.playlist:
            return
            
        if self.mode == 2:
            next_index = random.randint(0, len(self.playlist) - 1)
        else:
            next_index = (self.current_index + 1) % len(self.playlist)
            
        self.play_index(next_index)

    def play_prev(self):
        """播放上一首"""
        if not self.playlist:
            return
            
        if self.mode == 2:
            prev_index = random.randint(0, len(self.playlist) - 1)
        else:
            prev_index = (self.current_index - 1) % len(self.playlist)
            
        self.play_index(prev_index)

    def adjust_offset(self, value):
        """调整歌词偏移"""
        self.offset += value
        self.update_offset_label()
        if self.current_index >= 0:
            song_name = self.playlist[self.current_index]["name"]
            self.saved_offsets[song_name] = self.offset
            self.save_offsets()

    def update_offset_label(self):
        """更新偏移量显示"""
        sign = "+" if self.offset >= 0 else ""
        self.lbl_offset.setText(f"偏移: {sign}{self.offset:.1f}s")

    # === 文件管理方法 ===
    def search_songs(self, text):
        """搜索歌曲"""
        if not text.strip():
            if hasattr(self, '_original_playlist'):
                self.playlist = self._original_playlist.copy()
                self.refresh_table()
            return
            
        if not hasattr(self, '_original_playlist'):
            self._original_playlist = self.playlist.copy()
            
        search_text = text.lower()
        filtered_playlist = []
        
        for song in self._original_playlist:
            song_name = os.path.splitext(song["name"])[0].lower()
            artist = song.get("artist", "").lower()
            album = song.get("album", "").lower()
            
            if (search_text in song_name or 
                search_text in artist or 
                search_text in album):
                filtered_playlist.append(song)
                
        self.playlist = filtered_playlist
        self.refresh_table()

    def refresh_table(self):
        """刷新表格显示"""
        self.table.setRowCount(len(self.playlist))
        for row, song in enumerate(self.playlist):
            self.table.setItem(row, 0, QTableWidgetItem(os.path.splitext(song["name"])[0]))
            self.table.setItem(row, 1, QTableWidgetItem(song.get("artist", "未知")))
            self.table.setItem(row, 2, QTableWidgetItem(song.get("album", "未知")))
            self.table.setItem(row, 3, QTableWidgetItem(song.get("duration", "-")))

    def full_scan(self):
        """扫描音乐文件夹"""
        if not self.music_folder or not os.path.exists(self.music_folder):
            return
            
        self.collections = []
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4')
        
        for item in os.listdir(self.music_folder):
            full_path = os.path.join(self.music_folder, item)
            if os.path.isdir(full_path):
                files = [x for x in os.listdir(full_path) if x.lower().endswith(exts)]
                if len(files) > 1:
                    self.collections.append(item)
        
        self.nav_list.clear()
        self.nav_list.addItem("💿 全部音乐")
        self.nav_list.addItem("🕒 最近播放")
        for c in self.collections:
            self.nav_list.addItem(f"📁 {c}")
        
        if self.current_collection == "HISTORY":
            self.load_history_view()
        elif not self.current_collection or self.current_collection not in self.collections:
            self.current_collection = ""
            self.load_songs_for_collection()
        else:
            self.load_songs_for_collection()

    def switch_collection(self, item):
        """切换合集"""
        text = item.text()
        if "全部音乐" in text:
            self.current_collection = ""
            self.lbl_collection_title.setText("全部音乐")
            self.load_songs_for_collection()
        elif "最近播放" in text:
            self.current_collection = "HISTORY"
            self.lbl_collection_title.setText("最近播放")
            self.load_history_view()
        else:
            self.current_collection = text.replace("📁 ", "")
            self.lbl_collection_title.setText(f"合集：{self.current_collection}")
            self.load_songs_for_collection()

    def load_songs_for_collection(self):
        """加载指定合集的歌曲"""
        self.playlist = []
        self.table.setRowCount(0)
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4')
        
        target_dirs = []
        if self.current_collection:
            target_dirs = [os.path.join(self.music_folder, self.current_collection)]
        else:
            target_dirs = [self.music_folder]
            for item in os.listdir(self.music_folder):
                p = os.path.join(self.music_folder, item)
                if os.path.isdir(p) and item in self.collections:
                    target_dirs.append(p)

        row = 0
        for d in target_dirs:
            if not os.path.exists(d):
                continue
                
            for f in os.listdir(d):
                if f.lower().endswith(exts):
                    full_path = os.path.abspath(os.path.join(d, f))
                    meta = self.metadata.get(f, {
                        "artist": "未知歌手", 
                        "album": self.current_collection if self.current_collection else "默认专辑"
                    })
                    
                    song_data = {
                        "path": full_path,
                        "name": f,
                        "artist": meta.get("artist"),
                        "album": meta.get("album"),
                        "duration": "-"
                    }
                    self.playlist.append(song_data)
                    
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(os.path.splitext(f)[0]))
                    self.table.setItem(row, 1, QTableWidgetItem(meta.get("artist", "")))
                    self.table.setItem(row, 2, QTableWidgetItem(meta.get("album", "")))
                    self.table.setItem(row, 3, QTableWidgetItem("-"))
                    row += 1
        
        self._original_playlist = self.playlist.copy()

    def load_history_view(self):
        """加载历史播放记录"""
        self.playlist = []
        self.table.setRowCount(0)
        
        for song in self.history:
            if os.path.exists(song["path"]):
                self.playlist.append(song)
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(os.path.splitext(song["name"])[0]))
                self.table.setItem(row, 1, QTableWidgetItem(song.get("artist", "")))
                self.table.setItem(row, 2, QTableWidgetItem(song.get("album", "")))
                self.table.setItem(row, 3, QTableWidgetItem(song.get("duration", "-")))

    def show_context_menu(self, pos):
        """显示右键菜单"""
        items = self.table.selectedItems()
        if not items:
            return
            
        selected_rows = sorted(list(set(i.row() for i in items)))
        menu = QMenu(self)
        
        if len(selected_rows) == 1:
            menu.addAction("▶ 播放", lambda: self.play_index(selected_rows[0]))
            menu.addSeparator()
        
        if len(selected_rows) > 0:
            rename_menu = menu.addMenu("🔤 重命名")
            rename_menu.addAction("智能重命名选中", lambda: self.batch_smart_rename(selected_rows))
        
        if len(selected_rows) > 0:
            menu.addAction(f"🗑️ 删除选中歌曲 ({len(selected_rows)}首)", 
                          lambda: self.delete_songs(selected_rows))
        
        menu.exec_(self.table.mapToGlobal(pos))

    def batch_smart_rename(self, rows):
        """批量智能重命名选中文件"""
        selected_files = [self.playlist[i] for i in rows]
        dialog = ModernBatchRenameDialog(selected_files, self)
        if dialog.exec_() == QDialog.Accepted:
            self.full_scan()

    def open_smart_rename(self):
        """打开现代化智能重命名对话框"""
        if not self.playlist:
            self.show_modern_message("提示", "当前没有可重命名的歌曲")
            return
            
        dialog = ModernBatchRenameDialog(self.playlist, self)
        if dialog.exec_() == QDialog.Accepted:
            self.full_scan()

    def download_from_bilibili(self):
        """从B站下载音频"""
        if not self.music_folder:
            self.show_modern_message("提示", "请先设置音乐根目录")
            return
            
        url, ok = QInputDialog.getText(self, "B站下载", "请输入B站视频链接:")
        if not ok or not url:
            return
            
        p_num = 1
        match = re.search(r'[?&]p=(\d+)', url)
        if match:
            p_num = int(match.group(1))
            
        save_path = os.path.join(self.music_folder, "B站下载")
        if not os.path.exists(save_path):
            os.makedirs(save_path)
            
        self.downloader = BilibiliDownloader(url, save_path, "single", p_num)
        self.downloader.progress_signal.connect(
            lambda s: self.lbl_collection_title.setText(s)
        )
        self.downloader.finished_signal.connect(self.on_download_finished)
        self.downloader.error_signal.connect(
            lambda e: self.show_modern_message("下载错误", e)
        )
        self.downloader.start()
        
        self.lbl_collection_title.setText("⏳ 开始下载...")

    def on_download_finished(self, folder_path, file_list):
        """下载完成处理"""
        self.full_scan()
        self.show_modern_message("完成", f"下载完成！共下载 {len(file_list)} 个文件")

    def play_selected(self, item):
        """播放选中的歌曲"""
        self.play_index(item.row())

    def play_index(self, idx):
        """播放指定索引的歌曲"""
        if not self.playlist or idx >= len(self.playlist):
            return
            
        self.current_index = idx
        song = self.playlist[idx]
        
        if song not in self.history:
            self.history.insert(0, song)
            if len(self.history) > 100:
                self.history.pop()
            self.save_history()
        
        try:
            media_content = QMediaContent(QUrl.fromLocalFile(song["path"]))
            self.player.setMedia(media_content)
            self.player.setPlaybackRate(self.rate)
            self.player.play()
            
            self.btn_play.setText("⏸")
            
            self.offset = self.saved_offsets.get(song["name"], 0.0)
            self.update_offset_label()
            
            lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
            if os.path.exists(lrc_path):
                self.parse_lrc_file(lrc_path)
            else:
                self.panel_lyric.clear()
                self.panel_lyric.addItem("🎵 正在播放...")
                
        except Exception as e:
            print(f"播放失败: {e}")
            self.show_modern_message("播放错误", f"无法播放文件: {e}")

    def parse_lrc_file(self, path):
        """解析歌词文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.parse_lrc_content(content)
        except UnicodeDecodeError:
            try:
                with open(path, 'r', encoding='gbk') as f:
                    content = f.read()
                    self.parse_lrc_content(content)
            except Exception as e:
                print(f"解析歌词文件失败: {e}")
                self.panel_lyric.clear()
                self.panel_lyric.addItem("❌ 歌词文件解析失败")

    def parse_lrc_content(self, content):
        """解析歌词内容"""
        self.lyrics = []
        self.panel_lyric.clear()
        
        if not content:
            self.panel_lyric.addItem("🎵 纯音乐，请欣赏")
            return
            
        pattern = re.compile(r'\[(\d+):(\d+)\.(\d+)\](.*)')
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            match = pattern.match(line)
            if match:
                minutes, seconds, milliseconds, text = match.groups()
                if text.strip():
                    time_sec = int(minutes) * 60 + int(seconds) + int(milliseconds) / 100
                    self.lyrics.append({"t": time_sec, "txt": text.strip()})
                    self.panel_lyric.addItem(text.strip())
        
        if not self.lyrics:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('['):
                    self.panel_lyric.addItem(line)
        
        if self.panel_lyric.count() == 0:
            self.panel_lyric.addItem("🎵 暂无歌词")

    def select_folder(self):
        """选择音乐文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择音乐根目录")
        if folder:
            self.music_folder = folder
            self.full_scan()
            self.save_config()
            self.show_modern_message("成功", f"已设置音乐根目录: {folder}")

    def toggle_lyric(self):
        """切换桌面歌词显示"""
        if self.desktop_lyric.isVisible():
            self.desktop_lyric.hide()
        else:
            self.desktop_lyric.show()

    def delete_songs(self, rows):
        """删除歌曲"""
        if not rows:
            return
            
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 {len(rows)} 首歌曲吗？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        if self.current_index in rows:
            self.player.stop()
            self.current_index = -1
            
        deleted_count = 0
        for row in sorted(rows, reverse=True):
            if row < len(self.playlist):
                song = self.playlist[row]
                try:
                    if os.path.exists(song["path"]):
                        os.remove(song["path"])
                    
                    lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
                    if os.path.exists(lrc_path):
                        os.remove(lrc_path)
                    
                    self.playlist.pop(row)
                    deleted_count += 1
                    
                except Exception as e:
                    print(f"删除文件失败: {e}")
        
        self.refresh_table()
        self.show_modern_message("完成", f"已删除 {deleted_count} 首歌曲")

    def show_modern_message(self, title, message):
        """显示现代化消息框"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStyleSheet(STYLESHEET)
        msg.exec_()

    # === 配置管理 ===
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.music_folder = config.get("music_folder", "")
                    self.volume = config.get("volume", 50)
                    
                    lyric_geo = config.get("lyric_geometry")
                    if lyric_geo:
                        self.desktop_lyric.setGeometry(*lyric_geo)
                    
                    lyric_color = config.get("lyric_color")
                    if lyric_color:
                        self.desktop_lyric.font_color = QColor(*lyric_color)
                        self.desktop_lyric.update_styles()
            
            for file_name, target_var in [
                (OFFSET_FILE, "saved_offsets"),
                (METADATA_FILE, "metadata"), 
                (HISTORY_FILE, "history")
            ]:
                if os.path.exists(file_name):
                    with open(file_name, 'r', encoding='utf-8') as f:
                        setattr(self, target_var, json.load(f))
            
            self.volume_slider.setValue(self.volume)
            self.player.setVolume(self.volume)
            self.lbl_volume.setText(f"{self.volume}%")
            
            if self.music_folder:
                self.full_scan()
                
        except Exception as e:
            print(f"加载配置失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            config = {
                "music_folder": self.music_folder,
                "volume": self.volume,
                "lyric_geometry": self.desktop_lyric.geometry().getRect(),
                "lyric_color": self.desktop_lyric.font_color.getRgb()[:3]
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def save_offsets(self):
        """保存偏移量"""
        try:
            with open(OFFSET_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.saved_offsets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存偏移量失败: {e}")

    def save_metadata(self):
        """保存元数据"""
        try:
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存元数据失败: {e}")

    def save_history(self):
        """保存历史记录"""
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史记录失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        self.save_config()
        self.save_offsets()
        self.save_metadata()
        self.save_history()
        event.accept()

if __name__ == "__main__":
    # 设置高DPI支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("汽水音乐 2025")
    app.setApplicationVersion("4.0")
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    player = ModernSodaPlayer()
    player.show()
    
    sys.exit(app.exec_())

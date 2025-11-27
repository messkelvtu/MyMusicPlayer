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

# 设置多媒体插件环境变量 - 必须在导入PyQt5之前
os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"

from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QCoreApplication, QTimer, QPropertyAnimation, QEasingCurve, QRect, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QIcon, QPixmap, QCursor, QFontDatabase, QLinearGradient
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QFileDialog, QFrame, QAbstractItemView, QCheckBox,
                             QGraphicsDropShadowEffect, QInputDialog, QMessageBox, 
                             QFontDialog, QMenu, QAction, QSlider, QDialog, QRadioButton, 
                             QComboBox, QLineEdit, QTabWidget, QSpinBox, QColorDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget, 
                             QSplitter, QGroupBox, QScrollArea, QProgressBar)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent  # 确保这行存在

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
        policy.GradientColor = 0xCCF5F7FA
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = POINTER(ACCENT_POLICY)(policy)
        data.SizeOfData = sizeof(policy)
        windll.user32.SetWindowCompositionAttribute(int(hwnd), byref(data))
    except: 
        pass

# --- 现代化主题系统 ---
class ModernTheme:
    def __init__(self):
        self.colors = {
            'primary': '#4361EE',
            'primary_light': '#6A8BFF',
            'primary_dark': '#3A56D4',
            'secondary': '#3A86FF',
            'success': '#1ECD97',
            'warning': '#FF9F1C',
            'error': '#E94560',
            
            'background': '#F8FAFC',
            'surface': '#FFFFFF',
            'card': '#FFFFFF',
            'dialog': '#FFFFFF',
            
            'text_primary': '#2D3748',
            'text_secondary': '#718096',
            'text_tertiary': '#A0AEC0',
            'text_disabled': '#CBD5E0',
            
            'border_light': '#E2E8F0',
            'border_medium': '#CBD5E0',
            'border_dark': '#A0AEC0',
            
            'hover_light': 'rgba(67, 97, 238, 0.08)',
            'hover_medium': 'rgba(67, 97, 238, 0.12)',
            'selected': 'rgba(67, 97, 238, 0.15)',
            
            'overlay': 'rgba(0, 0, 0, 0.4)',
            'shadow': 'rgba(0, 0, 0, 0.1)'
        }
        
        self.shadows = {
            'small': '0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)',
            'medium': '0 4px 6px rgba(0,0,0,0.12), 0 2px 4px rgba(0,0,0,0.08)',
            'large': '0 10px 15px rgba(0,0,0,0.12), 0 4px 6px rgba(0,0,0,0.08)',
            'xlarge': '0 20px 25px rgba(0,0,0,0.12), 0 10px 10px rgba(0,0,0,0.08)'
        }
        
        self.radius = {
            'small': '8px',
            'medium': '12px',
            'large': '16px',
            'xlarge': '24px'
        }
        
        self.spacing = {
            'xs': '4px',
            'sm': '8px',
            'md': '16px',
            'lg': '24px',
            'xl': '32px'
        }

# --- 现代化样式表 ---
def generate_modern_stylesheet(theme):
    return f"""
    /* ===== 全局样式 ===== */
    QMainWindow {{
        background: {theme.colors['background']};
        color: {theme.colors['text_primary']};
        font-family: "Segoe UI", "Microsoft YaHei UI", -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    
    QWidget {{
        background: transparent;
        color: {theme.colors['text_primary']};
        font-family: "Segoe UI", "Microsoft YaHei UI", -apple-system, BlinkMacSystemFont, sans-serif;
        outline: none;
    }}
    
    /* ===== 侧边栏样式 ===== */
    QFrame#Sidebar {{
        background: {theme.colors['surface']};
        border: none;
        border-right: 1px solid {theme.colors['border_light']};
    }}
    
    QLabel#Logo {{
        background: transparent;
        color: {theme.colors['primary']};
        font-size: 24px;
        font-weight: 900;
        padding: {theme.spacing['xl']} {theme.spacing['lg']};
        border-bottom: 1px solid {theme.colors['border_light']};
        letter-spacing: 1px;
    }}
    
    QLabel#SectionTitle {{
        background: transparent;
        color: {theme.colors['text_secondary']};
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: {theme.spacing['lg']} {theme.spacing['lg']} {theme.spacing['sm']} {theme.spacing['lg']};
    }}
    
    /* ===== 现代化按钮样式 ===== */
    QPushButton {{
        border: none;
        border-radius: {theme.radius['medium']};
        padding: {theme.spacing['sm']} {theme.spacing['md']};
        font-weight: 600;
        font-size: 14px;
        transition: all 0.2s ease;
        outline: none;
    }}
    
    /* 主按钮 - 渐变填充 */
    QPushButton[class="primary"] {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                  stop:0 {theme.colors['primary']}, 
                                  stop:1 {theme.colors['primary_light']});
        color: white;
        border-radius: {theme.radius['large']};
        padding: {theme.spacing['md']} {theme.spacing['xl']};
        font-weight: 700;
    }}
    
    QPushButton[class="primary"]:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                  stop:0 {theme.colors['primary_dark']}, 
                                  stop:1 {theme.colors['primary']});
    }}
    
    /* 次要按钮 - 边框样式 */
    QPushButton[class="secondary"] {{
        background: transparent;
        color: {theme.colors['primary']};
        border: 2px solid {theme.colors['primary']};
        font-weight: 600;
    }}
    
    QPushButton[class="secondary"]:hover {{
        background: {theme.colors['primary']};
        color: white;
    }}
    
    /* 文本按钮 */
    QPushButton[class="text"] {{
        background: transparent;
        color: {theme.colors['text_secondary']};
        padding: {theme.spacing['sm']} {theme.spacing['md']};
        border-radius: {theme.radius['medium']};
    }}
    
    QPushButton[class="text"]:hover {{
        background: {theme.colors['hover_light']};
        color: {theme.colors['primary']};
    }}
    
    /* 图标按钮 */
    QPushButton[class="icon"] {{
        background: transparent;
        color: {theme.colors['text_secondary']};
        border-radius: {theme.radius['medium']};
        padding: {theme.spacing['sm']};
        min-width: 40px;
        min-height: 40px;
    }}
    
    QPushButton[class="icon"]:hover {{
        background: {theme.colors['hover_light']};
        color: {theme.colors['primary']};
    }}
    
    /* 导航按钮 */
    QPushButton[class="nav"] {{
        background: transparent;
        color: {theme.colors['text_secondary']};
        text-align: left;
        padding: {theme.spacing['md']} {theme.spacing['lg']};
        border-radius: {theme.radius['medium']};
        margin: 2px {theme.spacing['md']};
        border-left: 3px solid transparent;
        font-weight: 500;
    }}
    
    QPushButton[class="nav"]:hover {{
        background: {theme.colors['hover_light']};
        color: {theme.colors['primary']};
        border-left: 3px solid {theme.colors['primary']};
    }}
    
    QPushButton[class="nav"]:checked {{
        background: {theme.colors['selected']};
        color: {theme.colors['primary']};
        font-weight: 600;
        border-left: 3px solid {theme.colors['primary']};
    }}
    
    /* ===== 输入框样式 ===== */
    QLineEdit {{
        background: {theme.colors['surface']};
        border: 2px solid {theme.colors['border_light']};
        border-radius: {theme.radius['large']};
        padding: {theme.spacing['md']} {theme.spacing['lg']};
        font-size: 14px;
        color: {theme.colors['text_primary']};
        selection-background-color: {theme.colors['primary']};
    }}
    
    QLineEdit:focus {{
        border: 2px solid {theme.colors['primary']};
        background: {theme.colors['surface']};
    }}
    
    QLineEdit[class="search"] {{
        padding-left: {theme.spacing['xl']};
        background: {theme.colors['surface']};
        border: 2px solid {theme.colors['border_light']};
    }}
    
    QLineEdit[class="search"]:focus {{
        border: 2px solid {theme.colors['primary']};
        background: {theme.colors['surface']};
    }}
    
    /* ===== 表格样式 ===== */
    QTableWidget {{
        background: {theme.colors['surface']};
        border: 1px solid {theme.colors['border_light']};
        border-radius: {theme.radius['large']};
        gridline-color: transparent;
        outline: none;
        selection-background-color: transparent;
    }}
    
    QTableWidget::item {{
        padding: {theme.spacing['md']} {theme.spacing['lg']};
        border-bottom: 1px solid {theme.colors['border_light']};
        color: {theme.colors['text_primary']};
        background: transparent;
    }}
    
    QTableWidget::item:hover {{
        background: {theme.colors['hover_light']};
    }}
    
    QTableWidget::item:selected {{
        background: {theme.colors['selected']};
        color: {theme.colors['primary']};
        font-weight: 600;
    }}
    
    QHeaderView::section {{
        background: {theme.colors['background']};
        border: none;
        border-bottom: 1px solid {theme.colors['border_light']};
        padding: {theme.spacing['md']} {theme.spacing['lg']};
        font-weight: 700;
        color: {theme.colors['text_secondary']};
        font-size: 13px;
    }}
    
    /* ===== 列表样式 ===== */
    QListWidget {{
        background: {theme.colors['surface']};
        border: 1px solid {theme.colors['border_light']};
        border-radius: {theme.radius['large']};
        outline: none;
        padding: 4px;
    }}
    
    QListWidget::item {{
        background: transparent;
        border: none;
        border-radius: {theme.radius['medium']};
        padding: {theme.spacing['md']} {theme.spacing['lg']};
        margin: 2px;
        color: {theme.colors['text_secondary']};
    }}
    
    QListWidget::item:hover {{
        background: {theme.colors['hover_light']};
        color: {theme.colors['primary']};
    }}
    
    QListWidget::item:selected {{
        background: {theme.colors['selected']};
        color: {theme.colors['primary']};
        font-weight: 600;
    }}
    
    /* ===== 进度条样式 ===== */
    QSlider::groove:horizontal {{
        background: {theme.colors['border_light']};
        height: 6px;
        border-radius: 3px;
    }}
    
    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                  stop:0 {theme.colors['primary']}, 
                                  stop:1 {theme.colors['primary_light']});
        border-radius: 3px;
    }}
    
    QSlider::handle:horizontal {{
        background: {theme.colors['primary']};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}
    
    QSlider::handle:horizontal:hover {{
        background: {theme.colors['primary_dark']};
        width: 18px;
        height: 18px;
        margin: -6px 0;
    }}
    
    /* ===== 播放按钮特殊样式 ===== */
    QPushButton#PlayBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                  stop:0 {theme.colors['primary']}, 
                                  stop:1 {theme.colors['primary_light']});
        color: white;
        border: none;
        border-radius: 50%;
        min-width: 60px;
        min-height: 60px;
        font-size: 20px;
    }}
    
    QPushButton#PlayBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                  stop:0 {theme.colors['primary_dark']}, 
                                  stop:1 {theme.colors['primary']});
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

# --- 图标系统 ---
class IconSystem:
    @staticmethod
    def get_icon(name, size=16):
        icons = {
            "music": "🎵",
            "play": "▶️",
            "pause": "⏸️",
            "next": "⏭️",
            "prev": "⏮️",
            "volume": "🔊",
            "search": "🔍",
            "download": "📥",
            "folder": "📁",
            "heart": "❤️",
            "settings": "⚙️",
            "user": "👤",
            "star": "⭐",
            "time": "⏰",
            "edit": "✏️",
            "delete": "🗑️",
            "add": "➕",
            "check": "✅",
            "close": "❌"
        }
        return icons.get(name, "⚫")

# --- 现代化对话框 ---
class ModernDialog(QDialog):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        
        self.theme = ModernTheme()
        self.setStyleSheet(generate_modern_stylesheet(self.theme))

# --- 下载对话框 ---
class ModernDownloadDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__("下载音乐", parent)
        self.resize(500, 400)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)
        
        title = QLabel("下载音乐")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {self.theme.colors['text_primary']};")
        layout.addWidget(title)
        
        url_group = QGroupBox("视频链接")
        url_layout = QVBoxLayout(url_group)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入B站视频链接...")
        
        url_layout.addWidget(self.url_input)
        layout.addWidget(url_group)
        
        settings_group = QGroupBox("下载设置")
        settings_layout = QVBoxLayout(settings_group)
        
        self.single_radio = QRadioButton("单曲下载")
        self.playlist_radio = QRadioButton("合集下载")
        self.single_radio.setChecked(True)
        
        settings_layout.addWidget(self.single_radio)
        settings_layout.addWidget(self.playlist_radio)
        layout.addWidget(settings_group)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "text")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.download_btn = QPushButton(f"{IconSystem.get_icon('download')} 开始下载")
        self.download_btn.setProperty("class", "primary")
        self.download_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.download_btn)
        layout.addLayout(button_layout)

# --- 主程序 ---
class ModernMusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 · 现代版")
        self.resize(1400, 900)
        
        # 初始化主题
        self.theme = ModernTheme()
        
        # 应用样式表
        self.setStyleSheet(generate_modern_stylesheet(self.theme))
        
        # Windows毛玻璃效果
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
        self.mode = 0
        self.rate = 1.0
        self.volume = 80
        self.is_slider_pressed = False
        
        # 初始化播放器 - 添加错误处理
        self.player = None
        self.audio_enabled = True
        
        try:
            self.player = QMediaPlayer()
            self.player.positionChanged.connect(self.on_position_changed)
            self.player.durationChanged.connect(self.on_duration_changed)
            self.player.stateChanged.connect(self.on_state_changed)
            self.player.setVolume(self.volume)
        except Exception as e:
            print(f"音频播放器初始化失败: {e}")
            self.audio_enabled = False
        
        # 初始化界面
        self.setup_modern_ui()
        self.load_config()
    
    def setup_modern_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        sidebar = self.create_modern_sidebar()
        main_layout.addWidget(sidebar)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        top_bar = self.create_top_bar()
        content_layout.addWidget(top_bar)
        
        self.stacked_widget = QStackedWidget()
        
        home_page = self.create_home_page()
        self.stacked_widget.addWidget(home_page)
        
        lyrics_page = self.create_lyrics_page()
        self.stacked_widget.addWidget(lyrics_page)
        
        content_layout.addWidget(self.stacked_widget)
        
        player_bar = self.create_player_bar()
        content_layout.addWidget(player_bar)
        
        main_layout.addWidget(content_widget)
    
    def create_modern_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        brand = QLabel(f"{IconSystem.get_icon('music')} 汽水音乐")
        brand.setObjectName("Logo")
        layout.addWidget(brand)
        
        download_btn = QPushButton(f"{IconSystem.get_icon('download')} B站音频下载")
        download_btn.setProperty("class", "primary")
        download_btn.clicked.connect(self.download_bilibili)
        layout.addWidget(download_btn)
        
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setSpacing(8)
        nav_layout.setContentsMargins(16, 24, 16, 24)
        
        self.all_music_btn = QPushButton(f"{IconSystem.get_icon('music')} 全部音乐")
        self.all_music_btn.setProperty("class", "nav")
        self.all_music_btn.setCheckable(True)
        self.all_music_btn.setChecked(True)
        
        self.history_btn = QPushButton(f"{IconSystem.get_icon('time')} 最近播放")
        self.history_btn.setProperty("class", "nav")
        self.history_btn.setCheckable(True)
        
        nav_layout.addWidget(self.all_music_btn)
        nav_layout.addWidget(self.history_btn)
        nav_layout.addSpacing(16)
        
        collection_title = QLabel("我的歌单")
        collection_title.setObjectName("SectionTitle")
        nav_layout.addWidget(collection_title)
        
        self.collection_list = QListWidget()
        self.collection_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 12px 16px;
                margin: 4px 8px;
                border-radius: {self.theme.radius['medium']};
                color: {self.theme.colors['text_secondary']};
            }}
            QListWidget::item:hover {{
                background: {self.theme.colors['hover_light']};
                color: {self.theme.colors['primary']};
            }}
            QListWidget::item:selected {{
                background: {self.theme.colors['selected']};
                color: {self.theme.colors['primary']};
                font-weight: 600;
            }}
        """)
        
        collections = [
            f"{IconSystem.get_icon('heart')} 我的收藏",
            f"{IconSystem.get_icon('star')} 精选推荐", 
            f"{IconSystem.get_icon('user')} 私人FM",
            f"{IconSystem.get_icon('time')} 最近添加"
        ]
        
        for collection in collections:
            item = QListWidgetItem(collection)
            self.collection_list.addItem(item)
        
        nav_layout.addWidget(self.collection_list)
        nav_layout.addStretch()
        
        tools_title = QLabel("工具")
        tools_title.setObjectName("SectionTitle")
        nav_layout.addWidget(tools_title)
        
        refresh_btn = QPushButton(f"{IconSystem.get_icon('refresh')} 刷新库")
        refresh_btn.setProperty("class", "nav")
        
        settings_btn = QPushButton(f"{IconSystem.get_icon('settings')} 设置")
        settings_btn.setProperty("class", "nav")
        
        nav_layout.addWidget(refresh_btn)
        nav_layout.addWidget(settings_btn)
        
        layout.addWidget(nav_widget)
        
        return sidebar
    
    def create_top_bar(self):
        top_bar = QWidget()
        top_bar.setFixedHeight(80)
        top_bar.setStyleSheet(f"""
            background: {self.theme.colors['surface']};
            border-bottom: 1px solid {self.theme.colors['border_light']};
        """)
        
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(32, 0, 32, 0)
        
        self.page_title = QLabel("全部音乐")
        self.page_title.setStyleSheet(f"""
            font-size: 24px; 
            font-weight: 700; 
            color: {self.theme.colors['text_primary']};
        """)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索歌曲、歌手或专辑...")
        self.search_input.setProperty("class", "search")
        self.search_input.setFixedWidth(300)
        
        user_widget = QWidget()
        user_layout = QHBoxLayout(user_widget)
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(16)
        
        theme_btn = QPushButton(IconSystem.get_icon('settings'))
        theme_btn.setProperty("class", "icon")
        
        user_btn = QPushButton(IconSystem.get_icon('user'))
        user_btn.setProperty("class", "icon")
        
        user_layout.addWidget(theme_btn)
        user_layout.addWidget(user_btn)
        
        layout.addWidget(self.page_title)
        layout.addStretch()
        layout.addWidget(self.search_input)
        layout.addSpacing(16)
        layout.addWidget(user_widget)
        
        return top_bar
    
    def create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)
        
        action_bar = QWidget()
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        
        action_title = QLabel("歌曲列表")
        action_title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: {self.theme.colors['text_primary']};
        """)
        
        batch_edit_btn = QPushButton(f"{IconSystem.get_icon('edit')} 批量编辑")
        batch_edit_btn.setProperty("class", "secondary")
        
        random_play_btn = QPushButton(f"{IconSystem.get_icon('play')} 随机播放")
        random_play_btn.setProperty("class", "secondary")
        
        action_layout.addWidget(action_title)
        action_layout.addStretch()
        action_layout.addWidget(batch_edit_btn)
        action_layout.addWidget(random_play_btn)
        
        layout.addWidget(action_bar)
        
        self.song_table = QTableWidget()
        self.song_table.setColumnCount(5)
        self.song_table.setHorizontalHeaderLabels(["标题", "歌手", "专辑", "时长", "操作"])
        self.song_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.song_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        self.song_table.setRowCount(8)
        example_songs = [
            ["晴天", "周杰伦", "叶惠美", "04:29"],
            ["七里香", "周杰伦", "七里香", "04:56"],
            ["青花瓷", "周杰伦", "我很忙", "03:59"],
            ["简单爱", "周杰伦", "范特西", "04:30"],
            ["夜曲", "周杰伦", "十一月的萧邦", "03:46"],
            ["以父之名", "周杰伦", "叶惠美", "05:42"],
            ["东风破", "周杰伦", "叶惠美", "05:15"],
            ["发如雪", "周杰伦", "十一月的萧邦", "04:59"]
        ]
        
        for i, song in enumerate(example_songs):
            for j in range(4):
                self.song_table.setItem(i, j, QTableWidgetItem(song[j]))
            
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(4)
            
            play_btn = QPushButton(IconSystem.get_icon('play'))
            play_btn.setProperty("class", "icon")
            play_btn.setFixedSize(32, 32)
            
            more_btn = QPushButton(IconSystem.get_icon('settings'))
            more_btn.setProperty("class", "icon")
            more_btn.setFixedSize(32, 32)
            
            action_layout.addWidget(play_btn)
            action_layout.addWidget(more_btn)
            action_layout.addStretch()
            
            self.song_table.setCellWidget(i, 4, action_widget)
        
        layout.addWidget(self.song_table)
        
        return page
    
    def create_lyrics_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lyrics_display = QWidget()
        lyrics_layout = QHBoxLayout(lyrics_display)
        lyrics_layout.setContentsMargins(80, 80, 80, 80)
        
        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignCenter)
        
        album_cover = QLabel()
        album_cover.setFixedSize(240, 240)
        album_cover.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                      stop:0 {self.theme.colors['primary']}, 
                                      stop:1 {self.theme.colors['primary_light']});
            border-radius: {self.theme.radius['large']};
        """)
        
        song_title = QLabel("晴天")
        song_title.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 700;
            color: {self.theme.colors['text_primary']};
            margin-top: 24px;
        """)
        
        artist_name = QLabel("周杰伦")
        artist_name.setStyleSheet(f"""
            font-size: 18px;
            color: {self.theme.colors['text_secondary']};
            margin-top: 8px;
        """)
        
        left_layout.addWidget(album_cover)
        left_layout.addWidget(song_title)
        left_layout.addWidget(artist_name)
        left_layout.addStretch()
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.lyrics_display = QListWidget()
        self.lyrics_display.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                font-size: 20px;
                color: #718096;
            }
            QListWidget::item {
                padding: 16px;
                text-align: center;
                background: transparent;
                border: none;
            }
            QListWidget::item:selected {
                background: transparent;
                color: #4361EE;
                font-size: 24px;
                font-weight: 700;
            }
        """)
        
        example_lyrics = [
            "故事的小黄花",
            "从出生那年就飘着",
            "童年的荡秋千",
            "随记忆一直晃到现在",
            "Re So So Si Do Si La",
            "So La Si Si Si Si La Si La So"
        ]
        
        for lyric in example_lyrics:
            item = QListWidgetItem(lyric)
            item.setTextAlignment(Qt.AlignCenter)
            self.lyrics_display.addItem(item)
        
        right_layout.addWidget(self.lyrics_display)
        
        lyrics_layout.addWidget(left_panel)
        lyrics_layout.addWidget(right_panel, 1)
        
        layout.addWidget(lyrics_display)
        
        return page
    
    def create_player_bar(self):
        player_bar = QWidget()
        player_bar.setFixedHeight(120)
        player_bar.setStyleSheet(f"""
            background: {self.theme.colors['surface']};
            border-top: 1px solid {self.theme.colors['border_light']};
        """)
        
        layout = QVBoxLayout(player_bar)
        layout.setContentsMargins(32, 16, 32, 16)
        layout.setSpacing(12)
        
        progress_layout = QHBoxLayout()
        
        self.current_time = QLabel("00:00")
        self.current_time.setStyleSheet(f"color: {self.theme.colors['text_secondary']}; font-size: 12px;")
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(30)
        
        self.total_time = QLabel("04:30")
        self.total_time.setStyleSheet(f"color: {self.theme.colors['text_secondary']}; font-size: 12px;")
        
        progress_layout.addWidget(self.current_time)
        progress_layout.addWidget(self.progress_slider, 1)
        progress_layout.addWidget(self.total_time)
        
        control_layout = QHBoxLayout()
        
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(12)
        
        cover = QLabel()
        cover.setFixedSize(48, 48)
        cover.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                      stop:0 {self.theme.colors['primary']}, 
                                      stop:1 {self.theme.colors['primary_light']});
            border-radius: {self.theme.radius['medium']};
        """)
        
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        
        self.current_song = QLabel("晴天")
        self.current_song.setStyleSheet(f"""
            font-weight: 600;
            color: {self.theme.colors['text_primary']};
        """)
        
        self.current_artist = QLabel("周杰伦")
        self.current_artist.setStyleSheet(f"color: {self.theme.colors['text_secondary']};")
        
        text_layout.addWidget(self.current_song)
        text_layout.addWidget(self.current_artist)
        
        info_layout.addWidget(cover)
        info_layout.addWidget(text_widget)
        
        control_layout.addWidget(info_widget)
        control_layout.addStretch()
        
        self.play_mode_btn = QPushButton(IconSystem.get_icon('shuffle'))
        self.play_mode_btn.setProperty("class", "icon")
        self.prev_btn = QPushButton(IconSystem.get_icon('prev'))
        self.prev_btn.setProperty("class", "icon")
        self.play_btn = QPushButton(IconSystem.get_icon('play'))
        self.play_btn.setObjectName("PlayBtn")
        self.next_btn = QPushButton(IconSystem.get_icon('next'))
        self.next_btn.setProperty("class", "icon")
        self.rate_btn = QPushButton("1.0x")
        self.rate_btn.setProperty("class", "icon")
        
        control_layout.addWidget(self.play_mode_btn)
        control_layout.addSpacing(8)
        control_layout.addWidget(self.prev_btn)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.next_btn)
        control_layout.addSpacing(8)
        control_layout.addWidget(self.rate_btn)
        control_layout.addStretch()
        
        volume_widget = QWidget()
        volume_layout = QHBoxLayout(volume_widget)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(8)
        
        volume_icon = QPushButton(IconSystem.get_icon('volume'))
        volume_icon.setProperty("class", "icon")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setValue(80)
        
        volume_layout.addWidget(volume_icon)
        volume_layout.addWidget(self.volume_slider)
        
        control_layout.addWidget(volume_widget)
        
        layout.addLayout(progress_layout)
        layout.addLayout(control_layout)
        
        return player_bar
    
    def download_bilibili(self):
        dialog = ModernDownloadDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "下载", "开始下载...")
    
    def on_position_changed(self, position):
        self.current_time.setText(ms_to_str(position))
    
    def on_duration_changed(self, duration):
        self.total_time.setText(ms_to_str(duration))
        self.progress_slider.setRange(0, duration)
    
    def on_state_changed(self, state):
        icon = IconSystem.get_icon('pause') if state == QMediaPlayer.PlayingState else IconSystem.get_icon('play')
        self.play_btn.setText(icon)
    
    def load_config(self):
        pass

# === 主程序入口 ===
if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(app_path, 'PyQt5', 'Qt', 'plugins')
        QCoreApplication.addLibraryPath(os.path.join(app_path, 'PyQt5', 'Qt', 'plugins'))
    
    app = QApplication(sys.argv)
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    player = ModernMusicPlayer()
    player.show()
    
    sys.exit(app.exec_())

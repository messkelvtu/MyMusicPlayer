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

# 设置多媒体插件环境变量
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
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# 导入 qt-material
from qt_material import apply_stylesheet

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
        policy.GradientColor = 0xCCF5F7FA  # 浅色主题
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = POINTER(ACCENT_POLICY)(policy)
        data.SizeOfData = sizeof(policy)
        windll.user32.SetWindowCompositionAttribute(int(hwnd), byref(data))
    except: 
        pass

# --- 清新简约的白天样式 ---
def get_light_stylesheet():
    return """
    /* 清新简约的白天样式 */
    QMainWindow {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f8fafc, stop:1 #e2e8f0);
    }
    
    QFrame#Sidebar {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #f7fafc);
        border: none;
        border-right: 1px solid #e2e8f0;
    }
    
    QLabel#Logo {
        background: transparent;
        color: #4361ee;
        font-size: 22px;
        font-weight: bold;
        padding: 25px 20px;
        border-bottom: 1px solid #e2e8f0;
    }
    
    /* 播放按钮特殊样式 */
    QPushButton#PlayBtn {
        background: qradialgradient(cx:0.5, cy:0.5, radius: 0.8, fx:0.5, fy:0.5, stop:0 #4361ee, stop:1 #3a56d4);
        color: white;
        border: none;
        border-radius: 30px;
        min-width: 60px;
        min-height: 60px;
        font-size: 18px;
    }
    
    QPushButton#PlayBtn:hover {
        background: qradialgradient(cx:0.5, cy:0.5, radius: 0.8, fx:0.5, fy:0.5, stop:0 #6a8bff, stop:1 #4361ee);
    }
    
    /* 进度条美化 */
    QSlider::groove:horizontal {
        border: none;
        height: 6px;
        background: #e2e8f0;
        border-radius: 3px;
    }
    
    QSlider::sub-page:horizontal {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #6a8bff);
        border-radius: 3px;
    }
    
    QSlider::handle:horizontal {
        background: #ffffff;
        border: 2px solid #4361ee;
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }
    
    /* 表格美化 */
    QTableWidget {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        gridline-color: #e2e8f0;
    }
    
    QTableWidget::item {
        padding: 12px 16px;
        border-bottom: 1px solid #e2e8f0;
        color: #2d3748;
    }
    
    QTableWidget::item:selected {
        background: rgba(67, 97, 238, 0.1);
        color: #4361ee;
    }
    
    QHeaderView::section {
        background: #f7fafc;
        color: #718096;
        padding: 12px 16px;
        border: none;
        border-bottom: 1px solid #e2e8f0;
        font-weight: bold;
    }
    
    /* 歌词显示 */
    QListWidget#LyricsDisplay {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        font-size: 16px;
        color: #718096;
    }
    
    QListWidget#LyricsDisplay::item {
        padding: 15px;
        text-align: center;
        background: transparent;
        border: none;
    }
    
    QListWidget#LyricsDisplay::item:selected {
        background: transparent;
        color: #4361ee;
        font-size: 20px;
        font-weight: bold;
    }
    
    /* 导航按钮样式 */
    QPushButton[class="nav"] {
        background: transparent;
        color: #718096;
        text-align: left;
        padding: 12px 20px;
        border-radius: 8px;
        margin: 2px 12px;
        border-left: 3px solid transparent;
        font-weight: 500;
    }
    
    QPushButton[class="nav"]:hover {
        background: rgba(67, 97, 238, 0.08);
        color: #4361ee;
        border-left: 3px solid #4361ee;
    }
    
    QPushButton[class="nav"]:checked {
        background: rgba(67, 97, 238, 0.15);
        color: #4361ee;
        font-weight: 600;
        border-left: 3px solid #4361ee;
    }
    
    /* 主按钮样式 */
    QPushButton[class="primary"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4361ee, stop:1 #6a8bff);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
    }
    
    QPushButton[class="primary"]:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3a56d4, stop:1 #4361ee);
    }
    
    /* 搜索框样式 */
    QLineEdit[class="search"] {
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 20px;
        padding: 10px 20px;
        color: #2d3748;
        font-size: 14px;
    }
    
    QLineEdit[class="search"]:focus {
        border: 2px solid #4361ee;
    }
    """

# --- 辅助函数 ---
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def ms_to_str(ms):
    if not ms: 
        return "00:00"
    s = ms // 1000
    return f"{s//60:02}:{s%60:02}"

# --- 图标系统 ---
class LightIcons:
    @staticmethod
    def get_icon(name):
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
            "close": "❌",
            "home": "🏠",
            "library": "📚",
            "playlist": "🎼",
            "history": "🕒",
            "lyrics": "📝",
            "equalizer": "🎚️"
        }
        return icons.get(name, "⚫")

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

# --- 对话框类 ---
class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载音乐")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title = QLabel("下载音乐")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2d3748;")
        layout.addWidget(title)
        
        # URL输入
        url_group = QGroupBox("视频链接")
        url_layout = QVBoxLayout(url_group)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入B站视频链接...")
        url_layout.addWidget(self.url_input)
        layout.addWidget(url_group)
        
        # 下载设置
        settings_group = QGroupBox("下载设置")
        settings_layout = QVBoxLayout(settings_group)
        
        self.single_radio = QRadioButton("单曲下载")
        self.playlist_radio = QRadioButton("合集下载")
        self.single_radio.setChecked(True)
        
        settings_layout.addWidget(self.single_radio)
        settings_layout.addWidget(self.playlist_radio)
        layout.addWidget(settings_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "text")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.download_btn = QPushButton(f"{LightIcons.get_icon('download')} 开始下载")
        self.download_btn.setProperty("class", "primary")
        self.download_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.download_btn)
        layout.addLayout(button_layout)

# --- 主程序 ---
class LightMusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 · 清新版")
        self.resize(1400, 900)
        
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
        
        # 初始化播放器
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
        self.setup_light_ui()
        self.load_config()
        
        # Windows毛玻璃效果
        if os.name == 'nt':
            try:
                enable_acrylic(int(self.winId()))
            except:
                pass
    
    def setup_light_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 侧边栏
        sidebar = self.create_light_sidebar()
        main_layout.addWidget(sidebar)
        
        # 主内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 顶部栏
        top_bar = self.create_top_bar()
        content_layout.addWidget(top_bar)
        
        # 内容堆叠
        self.stacked_widget = QStackedWidget()
        
        # 主页
        home_page = self.create_home_page()
        self.stacked_widget.addWidget(home_page)
        
        # 发现页
        discover_page = self.create_discover_page()
        self.stacked_widget.addWidget(discover_page)
        
        # 歌词页
        lyrics_page = self.create_lyrics_page()
        self.stacked_widget.addWidget(lyrics_page)
        
        content_layout.addWidget(self.stacked_widget)
        
        # 播放控制栏
        player_bar = self.create_player_bar()
        content_layout.addWidget(player_bar)
        
        main_layout.addWidget(content_widget)
    
    def create_light_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Logo
        logo = QLabel(f"{LightIcons.get_icon('music')} 汽水音乐")
        logo.setObjectName("Logo")
        layout.addWidget(logo)
        
        # 导航区域
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setSpacing(8)
        nav_layout.setContentsMargins(16, 24, 16, 24)
        
        # 主要导航
        self.home_btn = QPushButton(f"{LightIcons.get_icon('home')} 首页")
        self.home_btn.setProperty("class", "nav")
        self.home_btn.setCheckable(True)
        self.home_btn.setChecked(True)
        self.home_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        
        self.discover_btn = QPushButton(f"{LightIcons.get_icon('search')} 发现音乐")
        self.discover_btn.setProperty("class", "nav")
        self.discover_btn.setCheckable(True)
        self.discover_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        
        self.lyrics_btn = QPushButton(f"{LightIcons.get_icon('lyrics')} 歌词页面")
        self.lyrics_btn.setProperty("class", "nav")
        self.lyrics_btn.setCheckable(True)
        self.lyrics_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        
        nav_layout.addWidget(self.home_btn)
        nav_layout.addWidget(self.discover_btn)
        nav_layout.addWidget(self.lyrics_btn)
        nav_layout.addSpacing(20)
        
        # 我的歌单标题
        playlist_title = QLabel("我的歌单")
        playlist_title.setStyleSheet("color: #718096; font-weight: bold; font-size: 12px; padding: 8px 16px;")
        nav_layout.addWidget(playlist_title)
        
        # 歌单列表
        self.collection_list = QListWidget()
        self.collection_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 16px;
                margin: 2px 8px;
                border-radius: 6px;
                color: #718096;
                border-left: 3px solid transparent;
            }
            QListWidget::item:hover {
                background: rgba(67, 97, 238, 0.08);
                color: #4361ee;
                border-left: 3px solid #4361ee;
            }
            QListWidget::item:selected {
                background: rgba(67, 97, 238, 0.15);
                color: #4361ee;
                font-weight: 600;
                border-left: 3px solid #4361ee;
            }
        """)
        
        # 添加歌单
        playlists = [
            f"{LightIcons.get_icon('heart')} 我喜欢的音乐",
            f"{LightIcons.get_icon('star')} 收藏列表",
            f"{LightIcons.get_icon('time')} 最近播放",
            f"{LightIcons.get_icon('playlist')} 默认歌单"
        ]
        
        for playlist in playlists:
            item = QListWidgetItem(playlist)
            self.collection_list.addItem(item)
        
        nav_layout.addWidget(self.collection_list)
        nav_layout.addStretch()
        
        # 下载按钮
        download_btn = QPushButton(f"{LightIcons.get_icon('download')} B站音频下载")
        download_btn.setProperty("class", "primary")
        download_btn.clicked.connect(self.download_bilibili)
        nav_layout.addWidget(download_btn)
        
        # 工具按钮
        tools_title = QLabel("工具")
        tools_title.setStyleSheet("color: #718096; font-weight: bold; font-size: 12px; padding: 16px 16px 8px 16px;")
        nav_layout.addWidget(tools_title)
        
        settings_btn = QPushButton(f"{LightIcons.get_icon('settings')} 设置")
        settings_btn.setProperty("class", "nav")
        nav_layout.addWidget(settings_btn)
        
        layout.addWidget(nav_widget)
        
        return sidebar
    
    def create_top_bar(self):
        top_bar = QWidget()
        top_bar.setFixedHeight(70)
        top_bar.setStyleSheet("background: white; border-bottom: 1px solid #e2e8f0;")
        
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(24, 0, 24, 0)
        
        # 页面标题
        self.page_title = QLabel("首页")
        self.page_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2d3748;")
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索音乐、歌手、专辑...")
        self.search_input.setProperty("class", "search")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self.filter_music)
        
        layout.addWidget(self.page_title)
        layout.addStretch()
        layout.addWidget(self.search_input)
        
        return top_bar
    
    def create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)
        
        # 欢迎标题
        welcome_title = QLabel("欢迎回来 👋")
        welcome_title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2d3748;")
        layout.addWidget(welcome_title)
        
        # 快速操作
        quick_actions = QWidget()
        actions_layout = QHBoxLayout(quick_actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        actions = [
            {"icon": "play", "text": "播放全部", "color": "#4361ee"},
            {"icon": "shuffle", "text": "随机播放", "color": "#1ecd97"},
            {"icon": "download", "text": "下载音乐", "color": "#ff9f1c"},
            {"icon": "equalizer", "text": "音效设置", "color": "#e94560"}
        ]
        
        for action in actions:
            btn = QPushButton(f"{LightIcons.get_icon(action['icon'])} {action['text']}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {action['color']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 16px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {action['color']}dd;
                }}
            """)
            actions_layout.addWidget(btn)
        
        layout.addWidget(quick_actions)
        
        # 最近播放
        recent_group = QGroupBox("最近播放")
        recent_group.setStyleSheet("""
            QGroupBox {
                color: #2d3748;
                font-size: 18px;
                font-weight: bold;
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        
        recent_layout = QVBoxLayout(recent_group)
        
        # 最近播放表格
        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(["标题", "歌手", "专辑", "时长", "操作"])
        self.recent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.recent_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # 加载最近播放数据
        self.load_recent_music()
        
        recent_layout.addWidget(self.recent_table)
        layout.addWidget(recent_group)
        
        return page
    
    def create_discover_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)
        
        title = QLabel("发现音乐 🎵")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2d3748;")
        layout.addWidget(title)
        
        # 音乐库表格
        self.music_table = QTableWidget()
        self.music_table.setColumnCount(5)
        self.music_table.setHorizontalHeaderLabels(["标题", "歌手", "专辑", "时长", "操作"])
        self.music_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.music_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.music_table.itemDoubleClicked.connect(self.play_selected_music)
        
        # 加载音乐库数据
        self.load_music_library()
        
        layout.addWidget(self.music_table)
        
        return page
    
    def create_lyrics_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # 歌词显示区域
        lyrics_container = QWidget()
        lyrics_layout = QHBoxLayout(lyrics_container)
        
        # 左侧专辑信息
        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignCenter)
        
        # 专辑封面
        self.album_cover = QLabel()
        self.album_cover.setFixedSize(240, 240)
        self.album_cover.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4361ee, stop:1 #6a8bff);
            border-radius: 16px;
        """)
        
        # 歌曲信息
        self.song_title = QLabel("选择歌曲")
        self.song_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2d3748; margin-top: 20px;")
        
        self.artist_name = QLabel("未知歌手")
        self.artist_name.setStyleSheet("font-size: 16px; color: #718096; margin-top: 8px;")
        
        left_layout.addWidget(self.album_cover)
        left_layout.addWidget(self.song_title)
        left_layout.addWidget(self.artist_name)
        left_layout.addStretch()
        
        # 右侧歌词
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.lyrics_display = QListWidget()
        self.lyrics_display.setObjectName("LyricsDisplay")
        
        right_layout.addWidget(self.lyrics_display)
        
        lyrics_layout.addWidget(left_panel)
        lyrics_layout.addWidget(right_panel, 1)
        
        layout.addWidget(lyrics_container)
        
        return page
    
    def create_player_bar(self):
        player_bar = QWidget()
        player_bar.setFixedHeight(100)
        player_bar.setStyleSheet("background: white; border-top: 1px solid #e2e8f0;")
        
        layout = QVBoxLayout(player_bar)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(8)
        
        # 进度条
        progress_layout = QHBoxLayout()
        
        self.current_time = QLabel("0:00")
        self.current_time.setStyleSheet("color: #718096; font-size: 12px;")
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(0)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        
        self.total_time = QLabel("0:00")
        self.total_time.setStyleSheet("color: #718096; font-size: 12px;")
        
        progress_layout.addWidget(self.current_time)
        progress_layout.addWidget(self.progress_slider, 1)
        progress_layout.addWidget(self.total_time)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        # 歌曲信息
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(12)
        
        # 专辑封面
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(48, 48)
        self.cover_label.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4361ee, stop:1 #6a8bff);
            border-radius: 8px;
        """)
        
        # 文字信息
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        
        self.current_song = QLabel("选择歌曲")
        self.current_song.setStyleSheet("font-weight: bold; color: #2d3748; font-size: 14px;")
        
        self.current_artist = QLabel("未知歌手")
        self.current_artist.setStyleSheet("color: #718096; font-size: 12px;")
        
        text_layout.addWidget(self.current_song)
        text_layout.addWidget(self.current_artist)
        
        info_layout.addWidget(self.cover_label)
        info_layout.addWidget(text_widget)
        
        control_layout.addWidget(info_widget)
        control_layout.addStretch()
        
        # 播放控制
        self.mode_btn = QPushButton(LightIcons.get_icon('shuffle'))
        self.mode_btn.setFixedSize(40, 40)
        self.mode_btn.setProperty("class", "icon")
        self.mode_btn.clicked.connect(self.toggle_play_mode)
        
        self.prev_btn = QPushButton(LightIcons.get_icon('prev'))
        self.prev_btn.setFixedSize(40, 40)
        self.prev_btn.setProperty("class", "icon")
        self.prev_btn.clicked.connect(self.play_previous)
        
        self.play_btn = QPushButton(LightIcons.get_icon('play'))
        self.play_btn.setObjectName("PlayBtn")
        self.play_btn.setFixedSize(60, 60)
        self.play_btn.clicked.connect(self.toggle_play)
        
        self.next_btn = QPushButton(LightIcons.get_icon('next'))
        self.next_btn.setFixedSize(40, 40)
        self.next_btn.setProperty("class", "icon")
        self.next_btn.clicked.connect(self.play_next)
        
        self.rate_btn = QPushButton("1.0x")
        self.rate_btn.setFixedSize(40, 40)
        self.rate_btn.setProperty("class", "icon")
        self.rate_btn.clicked.connect(self.toggle_playback_rate)
        
        control_layout.addWidget(self.mode_btn)
        control_layout.addSpacing(8)
        control_layout.addWidget(self.prev_btn)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.next_btn)
        control_layout.addSpacing(8)
        control_layout.addWidget(self.rate_btn)
        control_layout.addStretch()
        
        # 音量控制
        volume_widget = QWidget()
        volume_layout = QHBoxLayout(volume_widget)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(8)
        
        self.volume_icon = QPushButton(LightIcons.get_icon('volume'))
        self.volume_icon.setFixedSize(32, 32)
        self.volume_icon.setProperty("class", "icon")
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setValue(80)
        self.volume_slider.valueChanged.connect(self.set_volume)
        
        volume_layout.addWidget(self.volume_icon)
        volume_layout.addWidget(self.volume_slider)
        
        control_layout.addWidget(volume_widget)
        
        layout.addLayout(progress_layout)
        layout.addLayout(control_layout)
        
        return player_bar
    
    # === 核心功能方法 ===
    def load_recent_music(self):
        """加载最近播放的音乐"""
        self.recent_table.setRowCount(5)
        recent_songs = [
            ["Blinding Lights", "The Weeknd", "After Hours", "3:20"],
            ["Shape of You", "Ed Sheeran", "÷", "3:53"],
            ["Dance Monkey", "Tones and I", "The Kids Are Coming", "3:29"],
            ["Someone You Loved", "Lewis Capaldi", "Divinely Uninspired", "3:02"],
            ["Bad Guy", "Billie Eilish", "When We All Fall Asleep", "3:14"]
        ]
        
        for i, song in enumerate(recent_songs):
            for j in range(4):
                self.recent_table.setItem(i, j, QTableWidgetItem(song[j]))
            
            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            play_btn = QPushButton(LightIcons.get_icon('play'))
            play_btn.setFixedSize(32, 32)
            play_btn.setProperty("class", "icon")
            play_btn.clicked.connect(lambda checked, row=i: self.play_music(row))
            
            action_layout.addWidget(play_btn)
            action_layout.addStretch()
            
            self.recent_table.setCellWidget(i, 4, action_widget)
    
    def load_music_library(self):
        """加载音乐库"""
        self.music_table.setRowCount(8)
        songs = [
            ["晴天", "周杰伦", "叶惠美", "4:29"],
            ["七里香", "周杰伦", "七里香", "4:56"],
            ["青花瓷", "周杰伦", "我很忙", "3:59"],
            ["简单爱", "周杰伦", "范特西", "4:30"],
            ["夜曲", "周杰伦", "十一月的萧邦", "3:46"],
            ["以父之名", "周杰伦", "叶惠美", "5:42"],
            ["东风破", "周杰伦", "叶惠美", "5:15"],
            ["发如雪", "周杰伦", "十一月的萧邦", "4:59"]
        ]
        
        for i, song in enumerate(songs):
            for j in range(4):
                self.music_table.setItem(i, j, QTableWidgetItem(song[j]))
            
            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            play_btn = QPushButton(LightIcons.get_icon('play'))
            play_btn.setFixedSize(32, 32)
            play_btn.setProperty("class", "icon")
            play_btn.clicked.connect(lambda checked, row=i: self.play_music(row))
            
            action_layout.addWidget(play_btn)
            action_layout.addStretch()
            
            self.music_table.setCellWidget(i, 4, action_widget)
    
    def play_music(self, index):
        """播放音乐"""
        if not self.audio_enabled:
            QMessageBox.warning(self, "错误", "音频播放功能不可用")
            return
        
        # 模拟播放逻辑
        songs = [
            {"title": "晴天", "artist": "周杰伦", "album": "叶惠美"},
            {"title": "七里香", "artist": "周杰伦", "album": "七里香"},
            {"title": "青花瓷", "artist": "周杰伦", "album": "我很忙"},
            {"title": "简单爱", "artist": "周杰伦", "album": "范特西"},
            {"title": "夜曲", "artist": "周杰伦", "album": "十一月的萧邦"}
        ]
        
        if index < len(songs):
            song = songs[index]
            self.current_song.setText(song["title"])
            self.current_artist.setText(song["artist"])
            self.song_title.setText(song["title"])
            self.artist_name.setText(song["artist"])
            
            # 更新播放状态
            self.play_btn.setText(LightIcons.get_icon('pause'))
            
            # 模拟播放进度
            self.progress_slider.setValue(30)
            self.current_time.setText("1:30")
            self.total_time.setText("4:29")
            
            # 加载示例歌词
            self.load_sample_lyrics()
    
    def play_selected_music(self, item):
        """双击播放音乐"""
        self.play_music(item.row())
    
    def toggle_play(self):
        """切换播放/暂停"""
        if self.play_btn.text() == LightIcons.get_icon('play'):
            self.play_btn.setText(LightIcons.get_icon('pause'))
            # 开始播放逻辑
        else:
            self.play_btn.setText(LightIcons.get_icon('play'))
            # 暂停播放逻辑
    
    def play_previous(self):
        """播放上一首"""
        # 上一首逻辑
        pass
    
    def play_next(self):
        """播放下一首"""
        # 下一首逻辑
        pass
    
    def toggle_play_mode(self):
        """切换播放模式"""
        modes = [LightIcons.get_icon('shuffle'), LightIcons.get_icon('repeat'), LightIcons.get_icon('repeat-one')]
        current_index = modes.index(self.mode_btn.text()) if self.mode_btn.text() in modes else 0
        next_index = (current_index + 1) % len(modes)
        self.mode_btn.setText(modes[next_index])
    
    def toggle_playback_rate(self):
        """切换播放速率"""
        rates = ["1.0x", "1.25x", "1.5x", "2.0x"]
        current_index = rates.index(self.rate_btn.text()) if self.rate_btn.text() in rates else 0
        next_index = (current_index + 1) % len(rates)
        self.rate_btn.setText(rates[next_index])
    
    def set_volume(self, value):
        """设置音量"""
        if self.audio_enabled and self.player:
            self.player.setVolume(value)
    
    def on_slider_pressed(self):
        """进度条按下"""
        self.is_slider_pressed = True
    
    def on_slider_released(self):
        """进度条释放"""
        self.is_slider_pressed = False
        # 设置播放位置逻辑
    
    def filter_music(self, text):
        """过滤音乐"""
        # 搜索过滤逻辑
        pass
    
    def load_sample_lyrics(self):
        """加载示例歌词"""
        self.lyrics_display.clear()
        lyrics = [
            "故事的小黄花",
            "从出生那年就飘着",
            "童年的荡秋千",
            "随记忆一直晃到现在",
            "Re So So Si Do Si La",
            "So La Si Si Si Si La Si La So",
            "吹着前奏望着天空",
            "我想起花瓣试着掉落"
        ]
        for lyric in lyrics:
            item = QListWidgetItem(lyric)
            item.setTextAlignment(Qt.AlignCenter)
            self.lyrics_display.addItem(item)
    
    def download_bilibili(self):
        """B站音频下载"""
        dialog = DownloadDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "下载", "开始下载B站音频...")
            # 这里添加实际的下载逻辑
    
    def on_position_changed(self, position):
        """播放位置改变"""
        if not self.is_slider_pressed:
            self.progress_slider.setValue(position)
        self.current_time.setText(ms_to_str(position))
    
    def on_duration_changed(self, duration):
        """总时长改变"""
        self.progress_slider.setRange(0, duration)
        self.total_time.setText(ms_to_str(duration))
    
    def on_state_changed(self, state):
        """播放状态改变"""
        icon = LightIcons.get_icon('pause') if state == QMediaPlayer.PlayingState else LightIcons.get_icon('play')
        self.play_btn.setText(icon)
    
    def load_config(self):
        """加载配置"""
        # 配置加载逻辑
        pass

# === 主程序入口 ===
if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(app_path, 'PyQt5', 'Qt', 'plugins')
        QCoreApplication.addLibraryPath(os.path.join(app_path, 'PyQt5', 'Qt', 'plugins'))
    
    app = QApplication(sys.argv)
    
    # 应用 qt-material 浅色主题
    apply_stylesheet(app, theme='light_blue.xml')
    
    # 应用自定义清新样式
    app.setStyleSheet(app.styleSheet() + get_light_stylesheet())
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    player = LightMusicPlayer()
    player.show()
    
    sys.exit(app.exec_())

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
        policy.GradientColor = 0xCC1E1E1E
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = POINTER(ACCENT_POLICY)(policy)
        data.SizeOfData = sizeof(policy)
        windll.user32.SetWindowCompositionAttribute(int(hwnd), byref(data))
    except: 
        pass

# --- 现代化样式 ---
def get_material_stylesheet():
    return """
    /* 自定义样式增强 */
    QMainWindow {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1a1a, stop:1 #2d2d2d);
    }
    
    QFrame#Sidebar {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2b2b2b, stop:1 #3a3a3a);
        border: none;
    }
    
    QLabel#Logo {
        background: transparent;
        color: #ffffff;
        font-size: 24px;
        font-weight: bold;
        padding: 25px 20px;
        border-bottom: 1px solid #404040;
    }
    
    /* 播放按钮特殊样式 */
    QPushButton#PlayBtn {
        background: qradialgradient(cx:0.5, cy:0.5, radius: 0.8, fx:0.5, fy:0.5, stop:0 #ff4081, stop:1 #f50057);
        color: white;
        border: none;
        border-radius: 30px;
        min-width: 60px;
        min-height: 60px;
        font-size: 18px;
    }
    
    QPushButton#PlayBtn:hover {
        background: qradialgradient(cx:0.5, cy:0.5, radius: 0.8, fx:0.5, fy:0.5, stop:0 #ff79b0, stop:1 #ff4081);
    }
    
    /* 进度条美化 */
    QSlider::groove:horizontal {
        border: none;
        height: 6px;
        background: #404040;
        border-radius: 3px;
    }
    
    QSlider::sub-page:horizontal {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4081, stop:1 #f50057);
        border-radius: 3px;
    }
    
    QSlider::handle:horizontal {
        background: #ffffff;
        border: 2px solid #ff4081;
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }
    
    /* 表格美化 */
    QTableWidget {
        background: transparent;
        border: 1px solid #404040;
        border-radius: 8px;
        gridline-color: #404040;
    }
    
    QTableWidget::item {
        padding: 12px 16px;
        border-bottom: 1px solid #404040;
        color: #e0e0e0;
    }
    
    QTableWidget::item:selected {
        background: rgba(255, 64, 129, 0.2);
        color: #ffffff;
    }
    
    QHeaderView::section {
        background: #2b2b2b;
        color: #b0b0b0;
        padding: 12px 16px;
        border: none;
        border-bottom: 1px solid #404040;
        font-weight: bold;
    }
    
    /* 歌词显示 */
    QListWidget#LyricsDisplay {
        background: transparent;
        border: 1px solid #404040;
        border-radius: 8px;
        font-size: 16px;
        color: #b0b0b0;
    }
    
    QListWidget#LyricsDisplay::item {
        padding: 15px;
        text-align: center;
        background: transparent;
        border: none;
    }
    
    QListWidget#LyricsDisplay::item:selected {
        background: transparent;
        color: #ff4081;
        font-size: 20px;
        font-weight: bold;
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
class MaterialIcons:
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
            "history": "🕒"
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

# --- 主程序 ---
class MaterialMusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Material Music Player")
        self.resize(1200, 800)
        
        # 初始化数据
        self.music_folder = ""
        self.playlist = []
        self.current_index = -1
        self.volume = 80
        
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
        self.setup_material_ui()
        
        # Windows毛玻璃效果
        if os.name == 'nt':
            try:
                enable_acrylic(int(self.winId()))
            except:
                pass
    
    def setup_material_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 侧边栏
        sidebar = self.create_material_sidebar()
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
    
    def create_material_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Logo
        logo = QLabel(f"{MaterialIcons.get_icon('music')} Material Music")
        logo.setObjectName("Logo")
        layout.addWidget(logo)
        
        # 导航区域
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setSpacing(8)
        nav_layout.setContentsMargins(16, 24, 16, 24)
        
        # 主要导航
        home_btn = QPushButton(f"{MaterialIcons.get_icon('home')} 首页")
        home_btn.setProperty("class", "nav")
        home_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        
        discover_btn = QPushButton(f"{MaterialIcons.get_icon('search')} 发现音乐")
        discover_btn.setProperty("class", "nav")
        discover_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        
        library_btn = QPushButton(f"{MaterialIcons.get_icon('library')} 音乐库")
        library_btn.setProperty("class", "nav")
        
        nav_layout.addWidget(home_btn)
        nav_layout.addWidget(discover_btn)
        nav_layout.addWidget(library_btn)
        nav_layout.addSpacing(20)
        
        # 我的歌单标题
        playlist_title = QLabel("我的歌单")
        playlist_title.setStyleSheet("color: #b0b0b0; font-weight: bold; font-size: 12px; padding: 8px 16px;")
        nav_layout.addWidget(playlist_title)
        
        # 歌单列表
        playlists = [
            f"{MaterialIcons.get_icon('heart')} 我喜欢的音乐",
            f"{MaterialIcons.get_icon('star')} 收藏列表",
            f"{MaterialIcons.get_icon('time')} 最近播放",
            f"{MaterialIcons.get_icon('playlist')} 默认歌单"
        ]
        
        for playlist in playlists:
            playlist_btn = QPushButton(playlist)
            playlist_btn.setProperty("class", "nav")
            playlist_btn.setStyleSheet("text-align: left; padding: 10px 16px;")
            nav_layout.addWidget(playlist_btn)
        
        nav_layout.addStretch()
        
        # 下载按钮
        download_btn = QPushButton(f"{MaterialIcons.get_icon('download')} B站音频下载")
        download_btn.setProperty("class", "primary")
        download_btn.clicked.connect(self.download_bilibili)
        nav_layout.addWidget(download_btn)
        
        layout.addWidget(nav_widget)
        
        return sidebar
    
    def create_top_bar(self):
        top_bar = QWidget()
        top_bar.setFixedHeight(70)
        top_bar.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2b2b2b, stop:1 #3a3a3a);")
        
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(24, 0, 24, 0)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索音乐、歌手、专辑...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #404040;
                border: 2px solid #555555;
                border-radius: 20px;
                padding: 10px 20px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #ff4081;
            }
        """)
        self.search_input.setFixedWidth(300)
        
        layout.addStretch()
        layout.addWidget(self.search_input)
        layout.addStretch()
        
        return top_bar
    
    def create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)
        
        # 欢迎标题
        welcome_title = QLabel("欢迎回来 👋")
        welcome_title.setStyleSheet("font-size: 32px; font-weight: bold; color: white;")
        layout.addWidget(welcome_title)
        
        # 最近播放卡片
        recent_group = QGroupBox("最近播放")
        recent_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-size: 18px;
                font-weight: bold;
                border: 2px solid #404040;
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
        recent_table = QTableWidget()
        recent_table.setColumnCount(4)
        recent_table.setHorizontalHeaderLabels(["标题", "歌手", "专辑", "时长"])
        recent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        recent_table.setRowCount(5)
        
        # 示例数据
        recent_songs = [
            ["Blinding Lights", "The Weeknd", "After Hours", "3:20"],
            ["Shape of You", "Ed Sheeran", "÷", "3:53"],
            ["Dance Monkey", "Tones and I", "The Kids Are Coming", "3:29"],
            ["Someone You Loved", "Lewis Capaldi", "Divinely Uninspired", "3:02"],
            ["Bad Guy", "Billie Eilish", "When We All Fall Asleep", "3:14"]
        ]
        
        for i, song in enumerate(recent_songs):
            for j in range(4):
                recent_table.setItem(i, j, QTableWidgetItem(song[j]))
        
        recent_layout.addWidget(recent_table)
        layout.addWidget(recent_group)
        
        # 推荐歌单
        playlist_group = QGroupBox("推荐歌单")
        playlist_group.setStyleSheet(recent_group.styleSheet())
        
        playlist_layout = QHBoxLayout(playlist_group)
        
        # 歌单卡片
        playlists = [
            {"name": "热门推荐", "songs": "125首"},
            {"name": "新歌速递", "songs": "89首"},
            {"name": "私人雷达", "songs": "∞"},
            {"name": "学习专注", "songs": "76首"}
        ]
        
        for playlist in playlists:
            card = QFrame()
            card.setFixedSize(180, 200)
            card.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff4081, stop:1 #f50057);
                    border-radius: 12px;
                }
            """)
            
            card_layout = QVBoxLayout(card)
            card_layout.setAlignment(Qt.AlignBottom)
            card_layout.setContentsMargins(16, 16, 16, 16)
            
            name_label = QLabel(playlist["name"])
            name_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
            
            songs_label = QLabel(playlist["songs"])
            songs_label.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px;")
            
            card_layout.addWidget(name_label)
            card_layout.addWidget(songs_label)
            
            playlist_layout.addWidget(card)
        
        layout.addWidget(playlist_group)
        
        return page
    
    def create_discover_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)
        
        title = QLabel("发现音乐 🎵")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        layout.addWidget(title)
        
        # 音乐库表格
        music_table = QTableWidget()
        music_table.setColumnCount(5)
        music_table.setHorizontalHeaderLabels(["标题", "歌手", "专辑", "时长", "操作"])
        music_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        music_table.setRowCount(8)
        
        # 示例数据
        songs = [
            ["Blinding Lights", "The Weeknd", "After Hours", "3:20"],
            ["Shape of You", "Ed Sheeran", "÷", "3:53"],
            ["Dance Monkey", "Tones and I", "The Kids Are Coming", "3:29"],
            ["Someone You Loved", "Lewis Capaldi", "Divinely Uninspired", "3:02"],
            ["Bad Guy", "Billie Eilish", "When We All Fall Asleep", "3:14"],
            ["Watermelon Sugar", "Harry Styles", "Fine Line", "2:54"],
            ["Don't Start Now", "Dua Lipa", "Future Nostalgia", "3:03"],
            ["Circles", "Post Malone", "Hollywood's Bleeding", "3:35"]
        ]
        
        for i, song in enumerate(songs):
            for j in range(4):
                music_table.setItem(i, j, QTableWidgetItem(song[j]))
            
            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            play_btn = QPushButton(MaterialIcons.get_icon('play'))
            play_btn.setFixedSize(32, 32)
            play_btn.setStyleSheet("QPushButton { background: #ff4081; color: white; border-radius: 16px; }")
            
            action_layout.addWidget(play_btn)
            action_layout.addStretch()
            
            music_table.setCellWidget(i, 4, action_widget)
        
        layout.addWidget(music_table)
        
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
        album_cover = QLabel()
        album_cover.setFixedSize(240, 240)
        album_cover.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff4081, stop:1 #f50057);
            border-radius: 16px;
        """)
        
        # 歌曲信息
        song_title = QLabel("Blinding Lights")
        song_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white; margin-top: 20px;")
        
        artist_name = QLabel("The Weeknd")
        artist_name.setStyleSheet("font-size: 16px; color: #b0b0b0; margin-top: 8px;")
        
        left_layout.addWidget(album_cover)
        left_layout.addWidget(song_title)
        left_layout.addWidget(artist_name)
        left_layout.addStretch()
        
        # 右侧歌词
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.lyrics_display = QListWidget()
        self.lyrics_display.setObjectName("LyricsDisplay")
        
        # 示例歌词
        example_lyrics = [
            "I've been tryna call",
            "I've been on my own for long enough",
            "Maybe you can show me how to love, maybe",
            "I'm going through withdrawals",
            "You don't even have to do too much",
            "You can turn me on with just a touch, baby"
        ]
        
        for lyric in example_lyrics:
            item = QListWidgetItem(lyric)
            item.setTextAlignment(Qt.AlignCenter)
            self.lyrics_display.addItem(item)
        
        right_layout.addWidget(self.lyrics_display)
        
        lyrics_layout.addWidget(left_panel)
        lyrics_layout.addWidget(right_panel, 1)
        
        layout.addWidget(lyrics_container)
        
        return page
    
    def create_player_bar(self):
        player_bar = QWidget()
        player_bar.setFixedHeight(100)
        player_bar.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2b2b2b, stop:1 #3a3a3a); border-top: 1px solid #404040;")
        
        layout = QVBoxLayout(player_bar)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(8)
        
        # 进度条
        progress_layout = QHBoxLayout()
        
        self.current_time = QLabel("0:00")
        self.current_time.setStyleSheet("color: #b0b0b0; font-size: 12px;")
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(35)
        
        self.total_time = QLabel("3:20")
        self.total_time.setStyleSheet("color: #b0b0b0; font-size: 12px;")
        
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
        cover = QLabel()
        cover.setFixedSize(48, 48)
        cover.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff4081, stop:1 #f50057);
            border-radius: 8px;
        """)
        
        # 文字信息
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        
        self.current_song = QLabel("Blinding Lights")
        self.current_song.setStyleSheet("font-weight: bold; color: white; font-size: 14px;")
        
        self.current_artist = QLabel("The Weeknd")
        self.current_artist.setStyleSheet("color: #b0b0b0; font-size: 12px;")
        
        text_layout.addWidget(self.current_song)
        text_layout.addWidget(self.current_artist)
        
        info_layout.addWidget(cover)
        info_layout.addWidget(text_widget)
        
        control_layout.addWidget(info_widget)
        control_layout.addStretch()
        
        # 播放控制
        self.prev_btn = QPushButton(MaterialIcons.get_icon('prev'))
        self.prev_btn.setFixedSize(40, 40)
        
        self.play_btn = QPushButton(MaterialIcons.get_icon('play'))
        self.play_btn.setObjectName("PlayBtn")
        self.play_btn.setFixedSize(60, 60)
        
        self.next_btn = QPushButton(MaterialIcons.get_icon('next'))
        self.next_btn.setFixedSize(40, 40)
        
        control_layout.addWidget(self.prev_btn)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.next_btn)
        control_layout.addStretch()
        
        # 音量控制
        volume_widget = QWidget()
        volume_layout = QHBoxLayout(volume_widget)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(8)
        
        volume_icon = QPushButton(MaterialIcons.get_icon('volume'))
        volume_icon.setFixedSize(32, 32)
        
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
        QMessageBox.information(self, "下载", "B站音频下载功能")
    
    def on_position_changed(self, position):
        self.current_time.setText(ms_to_str(position))
    
    def on_duration_changed(self, duration):
        self.total_time.setText(ms_to_str(duration))
        self.progress_slider.setRange(0, duration)
    
    def on_state_changed(self, state):
        icon = MaterialIcons.get_icon('pause') if state == QMediaPlayer.PlayingState else MaterialIcons.get_icon('play')
        self.play_btn.setText(icon)

# === 主程序入口 ===
if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(app_path, 'PyQt5', 'Qt', 'plugins')
        QCoreApplication.addLibraryPath(os.path.join(app_path, 'PyQt5', 'Qt', 'plugins'))
    
    app = QApplication(sys.argv)
    
    # 应用 qt-material 主题
    apply_stylesheet(app, theme='dark_teal.xml')
    
    # 应用自定义样式增强
    app.setStyleSheet(app.styleSheet() + get_material_stylesheet())
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    player = MaterialMusicPlayer()
    player.show()
    
    sys.exit(app.exec_())

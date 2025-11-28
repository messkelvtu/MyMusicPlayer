import sys
import os
import json
import shutil
import random
import re
import urllib.request
import urllib.parse
import time

# 添加当前目录到 Python 路径，确保可以找到自定义模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
                           QFileDialog, QFrame, QAbstractItemView, QCheckBox, QGraphicsDropShadowEffect, 
                           QInputDialog, QMessageBox, QFontDialog, QMenu, QAction, QSlider, QDialog, 
                           QRadioButton, QComboBox, QLineEdit, QTabWidget, QSpinBox, QColorDialog,
                           QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget,
                           QSplitter, QGroupBox, QScrollArea, QSizePolicy, QProgressBar)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QCoreApplication, QTimer, QPropertyAnimation, QEasingCurve, QRect, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QIcon, QPixmap, QCursor, QFontDatabase
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# 导入自定义模块
from ui_scale_manager import UIScaleManager
from theme_manager import ThemeManager
from style_generator import generate_stylesheet
from utils import sanitize_filename, ms_to_str, LyricListSearchWorker, LyricDownloader, ICONS
from dialogs import LyricSearchDialog, BatchInfoDialog, DownloadDialog, SyncLyricsDialog
from desktop_lyric import DesktopLyricWindow
from windows_effects import enable_acrylic
from bilibili_downloader import BilibiliDownloader

# --- 核心配置 ---
os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"

CONFIG_FILE = "config.json"
METADATA_FILE = "metadata.json"
HISTORY_FILE = "history.json"
OFFSET_FILE = "offsets.json"

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
        self.setStyleSheet(generate_stylesheet(
            self.theme_manager.get_theme(),
            self.scale_manager, 
            screen_size.width(), 
            screen_size.height())
        )
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

        # B 站下载按钮
        download_button = QPushButton(f"{ICONS['youtube']} B 站音频下载")
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

        # == 右侧内容区域 ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 堆叠窗口
        self.stacked_widget = QStackedWidget()

        # 页面 0: 歌曲列表
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

        # 页面 1: 歌词页面
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

        # == 底部播放控制栏 ==
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
        self.cover_button.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4CAF50, stop:1 #81C784); border-radius: 8px; border:none;")
        self.cover_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(12, 0, 0, 0)

        self.song_title_mini = QLabel("--")
        self.song_title_mini.setStyleSheet("font-weight: bold; color: #185E20; font-size: 13px;")
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

    # == 核心功能 ==
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
        extensions = {'.mp3', '.wav', '.m4a', '.flac', '.mp4'}
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
                            "artist": metadata.get("artist", "未知"),
                            "album": metadata.get("album", "未知")
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
            # 只保留最近 50 首
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
            self.song_title_mini.setText(song_name[:15] + "..." if len(song_name) > 15 else song_name)
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
            self.lyric_downloader = LyricDownloader(results[0]["id"], lyric_path)
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
            match = re.match(r'^\[(\d+):(\d+)\.(\d+)\](.*)', line)
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

    # == 歌词控制功能 ==
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
            self.theme_manager.themes["light"]['primary'] = color.name()
            self.theme_manager.themes["light"]['primary-light'] = color.lighter(120).name()
            self.theme_manager.themes["light"]['primary-dark'] = color.darker(120).name()
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

    # == 文件操作 ==
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
        move_menu = menu.addMenu("  移动到...")
        move_menu.addAction("根目录", lambda: self.move_songs(selected_rows, ""))
        for collection in self.collections:
            move_menu.addAction(collection, lambda c=collection: self.move_songs(selected_rows, c))

        menu.addAction("  批量重命名", lambda: self.batch_rename(selected_rows))
        menu.addAction("  编辑信息", lambda: self.batch_edit_dialog())
        menu.addSeparator()

        if len(selected_rows) == 1:
            index = selected_rows[0]
            menu.addAction("  绑定/整理", lambda: self.bind_song(index))
            menu.addAction("  搜索歌词", lambda: self.manual_search_lyrics())
            menu.addAction("✗删除歌词", lambda: self.delete_lyrics(index))

        menu.addAction("  删除", lambda: self.delete_songs(selected_rows))
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
                    song_name = self.playlist[row]['name']
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
        file_path, _ = QFileDialog.getOpenFileName(self, "选择歌词文件", "", "歌词文件(*.lrc)")

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
        lyric_path = os.path.splitext(self.playlist[index]['path'])[0] + ".lrc"
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
                        song_path = self.playlist[row]['path']
                        os.remove(song_path)

                        lyric_path = os.path.splitext(song_path)[0] + ".lrc"
                        if os.path.exists(lyric_path):
                            os.remove(lyric_path)

                        deleted_count += 1
                    except Exception as e:
                        print(f"删除文件错误: {e}")

            self.full_scan()
            QMessageBox.information(self, "完成", f"成功删除 {deleted_count} 首歌曲")

    # == B 站下载 ==
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

            self.title_label.setText("下载中...")

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
                    self.metadata[file] = {"artist": artist or "未知", "album": album or "未知"}

        self.save_metadata()

        self.full_scan()
        self.title_label.setText("下载完成")

    def on_download_error(self, error):
        QMessageBox.warning(self, "下载错误", error)
        self.title_label.setText("下载失败")

    # == 其他功能 ==
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
            screen_size.height())
        )

    # == 配置管理 ==
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

# == 主程序入口 ==
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

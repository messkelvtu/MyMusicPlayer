import sys
import os
import json
import shutil
import random
import re
import urllib.request
import urllib.parse
import time

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
        lyrics_controls

import os
import json
import shutil
import random
import re
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QLabel, QListWidget, QListWidgetItem,
                           QFileDialog, QFrame, QAbstractItemView, QMessageBox,
                           QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget,
                           QSplitter, QGroupBox, QLineEdit, QSlider, QApplication)
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

from ui_scale_manager import UIScaleManager
from theme_manager import ThemeManager
from style_generator import generate_stylesheet
from utils import sanitize_filename, ms_to_str, ICONS
from dialogs import LyricSearchDialog, BatchInfoDialog, DownloadDialog, SyncLyricsDialog
from desktop_lyric import DesktopLyricWindow
from windows_effects import enable_acrylic
from bilibili_downloader import BilibiliDownloader
from lyric_manager import LyricManager

CONFIG_FILE = "config.json"
METADATA_FILE = "metadata.json"
HISTORY_FILE = "history.json"
OFFSET_FILE = "offsets.json"

class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 2025 - 自然清新版")

        # 初始化管理器
        self.scale_manager = UIScaleManager()
        self.theme_manager = ThemeManager()
        self.lyric_manager = LyricManager()

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

        # 初始化右侧内容区域
        self.init_right_panel(main_layout)

        # 初始化歌单列表
        self.init_collection_list()

    def init_right_panel(self, main_layout):
        """初始化右侧内容区域"""
        from ui_builder import UIBuilder
        ui_builder = UIBuilder(self.scale_manager, self.theme_manager)
        right_widget = ui_builder.build_right_panel(self)
        main_layout.addWidget(right_widget)

    # 这里只保留核心方法，其他方法可以进一步拆分...
    # 由于代码量限制，这里只展示核心结构

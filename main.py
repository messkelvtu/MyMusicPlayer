import sys
import os
import re
import random
import json
import shutil
import urllib.request
import urllib.parse
from ctypes import windll, c_int, byref, sizeof, Structure, POINTER

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QFileDialog, QFrame, QAbstractItemView, QSlider, QDialog,
                             QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QStackedWidget, QSplitter, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QCoreApplication, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QCursor, QIcon
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# --- 核心配置 ---
os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"
CONFIG_FILE = "config.json"

# --- 1:1 复刻 HTML CSS 的配色方案 ---
THEME = {
    'primary': '#4CAF50',
    'primary-light': '#81C784',
    'primary-dark': '#388E3C',
    'secondary': '#8BC34A',
    'background': '#F1F8E9',
    'surface': '#FFFFFF',
    'text-primary': '#1B5E20',
    'text-secondary': '#4CAF50',
    'text-tertiary': '#81C784',
    'border': '#C8E6C9',
    'hover': 'rgba(76, 175, 80, 0.08)',
    'selected': 'rgba(76, 175, 80, 0.15)'
}

# --- 样式表生成 (精确对应 CSS) ---
def get_stylesheet():
    return f"""
    /* 全局重置 */
    QMainWindow, QWidget {{
        background-color: {THEME['background']};
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-size: 13px;
        color: {THEME['text-primary']};
        outline: none;
    }}

    /* 侧边栏 Sidebar */
    QFrame#Sidebar {{
        background-color: {THEME['surface']};
        border-right: 1px solid {THEME['border']};
        min-width: 240px;
        max-width: 240px;
    }}

    QLabel#Logo {{
        padding: 30px 20px;
        font-size: 24px;
        font-weight: 900;
        color: {THEME['primary']};
        border-bottom: 1px solid {THEME['border']};
        letter-spacing: 1px;
        background: transparent;
    }}

    QLabel#SectionTitle {{
        font-size: 11px;
        color: {THEME['text-secondary']};
        padding: 20px 25px 10px 25px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        background: transparent;
    }}

    /* 侧边栏按钮 - NavBtn & ToolBtn */
    QPushButton.NavBtn, QPushButton.ToolBtn {{
        background: transparent;
        border: none;
        text-align: left;
        padding: 12px 25px;
        font-size: 13px;
        color: {THEME['text-secondary']};
        border-radius: 8px;
        margin: 2px 12px;
        border-left: 3px solid transparent;
    }}

    QPushButton.NavBtn:hover, QPushButton.ToolBtn:hover {{
        background-color: {THEME['hover']};
        color: {THEME['primary']};
        border-left: 3px solid {THEME['primary']};
    }}

    QPushButton.NavBtn:checked {{
        background-color: {THEME['selected']};
        font-weight: 600;
        border-left: 3px solid {THEME['primary']};
    }}

    /* 下载按钮 (复刻 HTML .download-btn) */
    QPushButton#DownloadBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['primary']}, stop:1 {THEME['primary-light']});
        color: white;
        border: none;
        border-radius: 20px;
        padding: 12px;
        margin: 15px 20px;
        font-weight: bold;
        text-align: center;
        font-size: 13px;
    }}
    QPushButton#DownloadBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['primary-dark']}, stop:1 {THEME['primary']});
    }}

    /* 歌单列表 (QListWidget 模拟 HTML .collection-list) */
    QListWidget#CollectionList {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QListWidget#CollectionList::item {{
        padding: 10px 15px;
        border-left: 2px solid transparent;
        margin: 0 10px;
        border-radius: 8px;
        color: {THEME['text-secondary']};
        font-size: 13px;
    }}
    QListWidget#CollectionList::item:hover {{
        background: {THEME['hover']};
        color: {THEME['primary']};
        border-left: 2px solid {THEME['primary']};
    }}
    QListWidget#CollectionList::item:selected {{
        background: {THEME['selected']};
        color: {THEME['primary']};
        font-weight: 600;
        border-left: 2px solid {THEME['primary']};
    }}

    /* 顶部栏 TopBar */
    QFrame#TopBar {{
        background: {THEME['surface']};
        border-bottom: 1px solid {THEME['border']};
        min-height: 70px;
        max-height: 70px;
    }}
    
    QLabel#PageTitle {{
        font-size: 26px;
        font-weight: bold;
        color: {THEME['primary']};
        background: transparent;
    }}

    /* 搜索框 (复刻 HTML .search-box) */
    QLineEdit#SearchBox {{
        background: {THEME['background']};
        border: 1px solid {THEME['border']};
        border-radius: 20px;
        color: {THEME['text-primary']};
        padding: 10px 20px;
        font-size: 13px;
        min-width: 280px;
    }}
    QLineEdit#SearchBox:focus {{
        border: 1px solid {THEME['primary']};
        background: white;
    }}

    /* 内容区 Song List Header */
    QLabel#SongListTitle {{
        font-size: 18px;
        font-weight: bold;
        color: {THEME['text-primary']};
        background: transparent;
    }}

    /* 操作按钮 (复刻 HTML .action-btn) */
    QPushButton.ActionBtn {{
        background: transparent;
        border: 1px solid {THEME['border']};
        color: {THEME['text-secondary']};
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 12px;
    }}
    QPushButton.ActionBtn:hover {{
        border-color: {THEME['primary']};
        color: {THEME['primary']};
        background: {THEME['hover']};
    }}

    /* 表格样式 (复刻 HTML .song-table) */
    QTableWidget {{
        background: {THEME['surface']};
        border: 1px solid {THEME['border']};
        border-radius: 12px;
        gridline-color: transparent;
        outline: none;
    }}
    QHeaderView::section {{
        background: {THEME['background']};
        border: none;
        border-bottom: 1px solid {THEME['border']};
        padding: 15px;
        font-weight: bold;
        color: {THEME['text-secondary']};
        text-align: left;
        font-size: 13px;
    }}
    QTableWidget::item {{
        padding-left: 10px;
        border-bottom: 1px solid {THEME['border']};
        color: {THEME['text-primary']};
    }}
    QTableWidget::item:selected {{
        background: {THEME['selected']};
        color: {THEME['primary']};
    }}
    
    /* 歌曲行内操作按钮 */
    QPushButton.SongInlineBtn {{
        background: transparent;
        border: none;
        color: {THEME['text-secondary']};
        font-size: 14px;
        max-width: 30px;
    }}
    QPushButton.SongInlineBtn:hover {{
        background: {THEME['hover']};
        color: {THEME['primary']};
        border-radius: 4px;
    }}

    /* 歌词面板 (Right Panel) */
    QFrame#LyricPanel {{
        min-width: 320px;
        max-width: 320px;
        background: transparent;
    }}
    QLabel#LyricTitle {{
        font-size: 16px;
        font-weight: bold;
        color: {THEME['text-primary']};
        background: transparent;
    }}
    QPushButton.LyricCtrlBtn {{
        background: transparent;
        border: 1px solid {THEME['border']};
        color: {THEME['text-secondary']};
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 11px;
    }}
    QPushButton.LyricCtrlBtn:hover {{
        border-color: {THEME['primary']};
        color: {THEME['primary']};
        background: {THEME['hover']};
    }}
    QListWidget#LyricContent {{
        background: {THEME['surface']};
        border: 1px solid {THEME['border']};
        border-radius: 12px;
        padding: 10px;
        font-size: 13px;
        color: {THEME['text-secondary']};
        outline: none;
    }}
    QListWidget#LyricContent::item {{
        padding: 8px 0;
        text-align: center;
    }}
    QListWidget#LyricContent::item:selected {{
        color: {THEME['primary']};
        font-size: 16px;
        font-weight: bold;
        background: transparent;
    }}

    /* 播放控制栏 Player Bar */
    QFrame#PlayerBar {{
        background: {THEME['surface']};
        border-top: 1px solid {THEME['border']};
        min-height: 100px;
        max-height: 100px;
    }}
    
    /* 进度条 & 音量条 (QSlider 模拟 HTML Range) */
    QSlider::groove:horizontal {{
        height: 5px;
        background: {THEME['border']};
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {THEME['primary']};
        width: 14px;
        height: 14px;
        margin: -5px 0; /* center on groove */
        border-radius: 7px;
    }}
    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['primary']}, stop:1 {THEME['primary-light']});
        border-radius: 3px;
    }}

    /* 播放控制按钮 */
    QPushButton.PlayerCtrlBtn {{
        background: transparent;
        border: none;
        color: {THEME['text-secondary']};
        font-size: 18px;
        border-radius: 6px;
        width: 40px; 
        height: 40px;
    }}
    QPushButton.PlayerCtrlBtn:hover {{
        background: {THEME['hover']};
        color: {THEME['primary']};
    }}
    
    /* 大播放按钮 */
    QPushButton#BigPlayBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {THEME['primary']}, stop:1 {THEME['primary-light']});
        color: white;
        border: none;
        border-radius: 28px;
        font-size: 24px;
        width: 56px;
        height: 56px;
    }}
    QPushButton#BigPlayBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {THEME['primary-dark']}, stop:1 {THEME['primary']});
    }}
    
    /* 滚动条美化 */
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {THEME['border']};
        min-height: 20px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {THEME['text-tertiary']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    """

# --- 辅助类：Windows 毛玻璃 ---
class ACCENT_POLICY(Structure):
    _fields_ = [("AccentState", c_int), ("AccentFlags", c_int), ("GradientColor", c_int), ("AnimationId", c_int)]

class WINDOWCOMPOSITIONATTRIBDATA(Structure):
    _fields_ = [("Attribute", c_int), ("Data", POINTER(ACCENT_POLICY)), ("SizeOfData", c_int)]

def enable_acrylic(hwnd):
    try:
        policy = ACCENT_POLICY()
        policy.AccentState = 4
        policy.GradientColor = 0xCCF1F8E9 
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = POINTER(ACCENT_POLICY)(policy)
        data.SizeOfData = sizeof(policy)
        windll.user32.SetWindowCompositionAttribute(int(hwnd), byref(data))
    except:
        pass

# --- 主程序类 ---
class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 2025 - 自然清新版")
        self.resize(1280, 800)  # 默认尺寸
        
        # 应用样式表
        self.setStyleSheet(get_stylesheet())
        
        if os.name == 'nt':
            try:
                enable_acrylic(int(self.winId()))
            except:
                pass

        self.init_ui()
        self.load_mock_data() # 加载演示数据以匹配截图

    def init_ui(self):
        # 根容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局：水平 (左侧边栏 + 右侧主内容)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ================= 左侧边栏 (240px) =================
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo
        logo = QLabel("🎵 汽水音乐")
        logo.setObjectName("Logo")
        sidebar_layout.addWidget(logo)

        # 下载按钮
        dl_btn = QPushButton("📺 B站音频下载")
        dl_btn.setObjectName("DownloadBtn")
        dl_btn.setCursor(Qt.PointingHandCursor)
        sidebar_layout.addWidget(dl_btn)

        # 导航按钮
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 10, 0, 10)
        nav_layout.setSpacing(2)
        
        self.btn_all_music = QPushButton("💿 全部音乐")
        self.btn_all_music.setProperty("class", "NavBtn")
        self.btn_all_music.setCheckable(True)
        self.btn_all_music.setChecked(True)
        self.btn_all_music.setCursor(Qt.PointingHandCursor)
        
        btn_history = QPushButton("🕒 最近播放")
        btn_history.setProperty("class", "NavBtn")
        btn_history.setCheckable(True)
        btn_history.setCursor(Qt.PointingHandCursor)
        
        nav_layout.addWidget(self.btn_all_music)
        nav_layout.addWidget(btn_history)
        sidebar_layout.addWidget(nav_container)

        # 歌单标题
        lbl_collection = QLabel("歌单宝藏库")
        lbl_collection.setObjectName("SectionTitle")
        sidebar_layout.addWidget(lbl_collection)

        # 歌单列表
        self.collection_list = QListWidget()
        self.collection_list.setObjectName("CollectionList")
        self.collection_list.setCursor(Qt.PointingHandCursor)
        # 添加演示歌单
        collections = ["❤️ 我的收藏", "🔥 流行音乐", "⭐ 经典老歌", "🎧 学习专注", "🚗 驾车音乐", "🏃 运动节奏"]
        for c in collections:
            self.collection_list.addItem(QListWidgetItem(c))
        sidebar_layout.addWidget(self.collection_list)

        # 底部工具栏
        tool_container = QWidget()
        tool_layout = QVBoxLayout(tool_container)
        tool_layout.setContentsMargins(0, 10, 0, 10)
        tool_layout.setSpacing(2)
        
        tools = ["🔄 刷新库", "📁+ 新建合集", "🚚 批量移动", "📂 根目录", "🎤 桌面歌词"]
        for t in tools:
            btn = QPushButton(t)
            btn.setProperty("class", "ToolBtn")
            btn.setCursor(Qt.PointingHandCursor)
            tool_layout.addWidget(btn)
        
        sidebar_layout.addWidget(tool_container)
        main_layout.addWidget(sidebar)

        # ================= 右侧区域 (垂直布局：Top + Content + Player) =================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 1. 顶部栏 (TopBar)
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(30, 0, 30, 0)
        
        page_title = QLabel("全部音乐")
        page_title.setObjectName("PageTitle")
        
        search_box = QLineEdit()
        search_box.setObjectName("SearchBox")
        search_box.setPlaceholderText("🔍 搜索歌曲、歌手或专辑...")
        
        top_layout.addWidget(page_title)
        top_layout.addStretch()
        top_layout.addWidget(search_box)
        right_layout.addWidget(top_bar)

        # 2. 中间内容区 (水平布局：歌曲列表 + 歌词面板)
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # ---> 左侧：歌曲列表容器
        song_list_container = QWidget()
        song_list_layout = QVBoxLayout(song_list_container)
        song_list_layout.setContentsMargins(0, 0, 0, 0)
        song_list_layout.setSpacing(15)

        # 列表头：标题 + 按钮
        list_header = QWidget()
        list_header_layout = QHBoxLayout(list_header)
        list_header_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_list_title = QLabel("歌曲列表")
        lbl_list_title.setObjectName("SongListTitle")
        
        action_box = QHBoxLayout()
        action_box.setSpacing(10)
        btn_batch = QPushButton("✏️ 批量编辑")
        btn_batch.setProperty("class", "ActionBtn")
        btn_batch.setCursor(Qt.PointingHandCursor)
        btn_random = QPushButton("🔀 随机播放")
        btn_random.setProperty("class", "ActionBtn")
        btn_random.setCursor(Qt.PointingHandCursor)
        action_box.addWidget(btn_batch)
        action_box.addWidget(btn_random)
        
        list_header_layout.addWidget(lbl_list_title)
        list_header_layout.addStretch()
        list_header_layout.addLayout(action_box)
        song_list_layout.addWidget(list_header)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["标题", "歌手", "专辑", "时长", "操作"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setFocusPolicy(Qt.NoFocus) # 去除选中虚线框
        self.table.setAlternatingRowColors(False)
        
        # 设置列宽比例 (40%, 20%, 20%, 10%, 10%)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)       # 标题
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # 歌手 (Stretch looks better usually but mimics HTML %)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 80)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 100)
        
        song_list_layout.addWidget(self.table)
        content_layout.addWidget(song_list_container)

        # ---> 右侧：歌词面板
        lyric_panel = QFrame()
        lyric_panel.setObjectName("LyricPanel")
        lyric_layout = QVBoxLayout(lyric_panel)
        lyric_layout.setContentsMargins(0, 0, 0, 0)
        lyric_layout.setSpacing(15)

        # 歌词头部
        lyric_header = QWidget()
        lyric_header_layout = QHBoxLayout(lyric_header)
        lyric_header_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_lyric = QLabel("歌词")
        lbl_lyric.setObjectName("LyricTitle")
        
        lyric_ctrls = QHBoxLayout()
        lyric_ctrls.setSpacing(8)
        btn_sync = QPushButton("🔄 同步")
        btn_sync.setProperty("class", "LyricCtrlBtn")
        btn_sync.setCursor(Qt.PointingHandCursor)
        btn_search = QPushButton("🔍 搜索")
        btn_search.setProperty("class", "LyricCtrlBtn")
        btn_search.setCursor(Qt.PointingHandCursor)
        lyric_ctrls.addWidget(btn_sync)
        lyric_ctrls.addWidget(btn_search)
        
        lyric_header_layout.addWidget(lbl_lyric)
        lyric_header_layout.addStretch()
        lyric_header_layout.addLayout(lyric_ctrls)
        lyric_layout.addWidget(lyric_header)

        # 歌词内容
        self.lyric_content = QListWidget()
        self.lyric_content.setObjectName("LyricContent")
        self.lyric_content.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.lyric_content.setFocusPolicy(Qt.NoFocus)
        lyric_layout.addWidget(self.lyric_content)
        
        content_layout.addWidget(lyric_panel)
        right_layout.addWidget(content_area)

        # 3. 播放控制栏 (PlayerBar)
        player_bar = QFrame()
        player_bar.setObjectName("PlayerBar")
        player_layout = QVBoxLayout(player_bar)
        player_layout.setContentsMargins(25, 15, 25, 15)
        player_layout.setSpacing(5)

        # 进度条区
        progress_box = QHBoxLayout()
        lbl_curr_time = QLabel("01:30")
        lbl_curr_time.setStyleSheet(f"color: {THEME['text-secondary']}; font-size: 11px;")
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setCursor(Qt.PointingHandCursor)
        
        lbl_total_time = QLabel("04:29")
        lbl_total_time.setStyleSheet(f"color: {THEME['text-secondary']}; font-size: 11px;")
        
        progress_box.addWidget(lbl_curr_time)
        progress_box.addWidget(self.slider)
        progress_box.addWidget(lbl_total_time)
        player_layout.addLayout(progress_box)

        # 控制区
        controls_box = QHBoxLayout()
        
        # 左：歌曲信息
        info_box = QHBoxLayout()
        cover = QLabel()
        cover.setFixedSize(50, 50)
        cover.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {THEME['primary']}, stop:1 {THEME['primary-light']}); border-radius: 8px;")
        
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        text_box.setAlignment(Qt.AlignVCenter)
        lbl_song = QLabel("晴天")
        lbl_song.setStyleSheet(f"font-weight: bold; color: {THEME['text-primary']}; font-size: 13px;")
        lbl_artist = QLabel("周杰伦")
        lbl_artist.setStyleSheet(f"color: {THEME['text-secondary']}; font-size: 12px;")
        text_box.addWidget(lbl_song)
        text_box.addWidget(lbl_artist)
        
        info_box.addWidget(cover)
        info_box.addSpacing(10)
        info_box.addLayout(text_box)
        controls_box.addLayout(info_box)
        controls_box.addStretch()

        # 中：播放按钮
        play_ctrls = QHBoxLayout()
        play_ctrls.setSpacing(15)
        
        btn_mode = QPushButton("🔁")
        btn_mode.setProperty("class", "PlayerCtrlBtn")
        btn_mode.setCursor(Qt.PointingHandCursor)
        
        btn_prev = QPushButton("⏮")
        btn_prev.setProperty("class", "PlayerCtrlBtn")
        btn_prev.setCursor(Qt.PointingHandCursor)
        
        self.btn_play = QPushButton("⏸")
        self.btn_play.setObjectName("BigPlayBtn")
        self.btn_play.setCursor(Qt.PointingHandCursor)
        
        btn_next = QPushButton("⏭")
        btn_next.setProperty("class", "PlayerCtrlBtn")
        btn_next.setCursor(Qt.PointingHandCursor)
        
        btn_rate = QPushButton("1.0x")
        btn_rate.setProperty("class", "PlayerCtrlBtn")
        btn_rate.setCursor(Qt.PointingHandCursor)
        
        play_ctrls.addWidget(btn_mode)
        play_ctrls.addWidget(btn_prev)
        play_ctrls.addWidget(self.btn_play)
        play_ctrls.addWidget(btn_next)
        play_ctrls.addWidget(btn_rate)
        
        controls_box.addLayout(play_ctrls)
        controls_box.addStretch()

        # 右：音量
        vol_box = QHBoxLayout()
        vol_box.setSpacing(10)
        
        btn_vol = QPushButton("🔊")
        btn_vol.setProperty("class", "PlayerCtrlBtn")
        
        vol_slider = QSlider(Qt.Horizontal)
        vol_slider.setFixedWidth(80)
        vol_slider.setValue(80)
        vol_slider.setCursor(Qt.PointingHandCursor)
        
        btn_offset = QPushButton("🎚️ 微调")
        btn_offset.setProperty("class", "ActionBtn") # Reuse style
        btn_offset.setCursor(Qt.PointingHandCursor)

        vol_box.addWidget(btn_vol)
        vol_box.addWidget(vol_slider)
        vol_box.addWidget(btn_offset)
        controls_box.addLayout(vol_box)

        player_layout.addLayout(controls_box)
        right_layout.addWidget(player_bar)

        main_layout.addWidget(right_widget)

    def load_mock_data(self):
        # 填充演示数据 (来自 HTML)
        songs = [
            ("晴天", "周杰伦", "叶惠美", "04:29"),
            ("七里香", "周杰伦", "七里香", "04:56"),
            ("青花瓷", "周杰伦", "我很忙", "03:59"),
            ("简单爱", "周杰伦", "范特西", "04:30"),
            ("夜曲", "周杰伦", "十一月的萧邦", "03:46"),
            ("以父之名", "周杰伦", "叶惠美", "05:42"),
            ("东风破", "周杰伦", "叶惠美", "05:15"),
            ("发如雪", "周杰伦", "十一月的萧邦", "04:59")
        ]

        self.table.setRowCount(len(songs))
        for r, (title, artist, album, duration) in enumerate(songs):
            self.table.setItem(r, 0, QTableWidgetItem(title))
            self.table.setItem(r, 1, QTableWidgetItem(artist))
            self.table.setItem(r, 2, QTableWidgetItem(album))
            self.table.setItem(r, 3, QTableWidgetItem(duration))
            
            # 操作按钮容器
            cell_widget = QWidget()
            layout = QHBoxLayout(cell_widget)
            layout.setContentsMargins(0,0,0,0)
            layout.setSpacing(5)
            layout.setAlignment(Qt.AlignLeft)
            
            b1 = QPushButton("▶")
            b1.setProperty("class", "SongInlineBtn")
            b1.setCursor(Qt.PointingHandCursor)
            
            b2 = QPushButton("✏️")
            b2.setProperty("class", "SongInlineBtn")
            b2.setCursor(Qt.PointingHandCursor)
            
            b3 = QPushButton("⋯")
            b3.setProperty("class", "SongInlineBtn")
            b3.setCursor(Qt.PointingHandCursor)
            
            layout.addWidget(b1)
            layout.addWidget(b2)
            layout.addWidget(b3)
            self.table.setCellWidget(r, 4, cell_widget)

        # 选中第一行
        self.table.selectRow(0)

        # 填充歌词
        lyrics = [
            "故事的小黄花", "从出生那年就飘着", "童年的荡秋千", 
            "随记忆一直晃到现在", "Re So So Si Do Si La", 
            "So La Si Si Si Si La Si La So", "吹着前奏望着天空", 
            "我想起花瓣试着掉落", "为你翘课的那一天", "花落的那一天",
            "教室的那一间", "我怎么看不见", "消失的下雨天", "我好想再淋一遍"
        ]
        for l in lyrics:
            item = QListWidgetItem(l)
            self.lyric_content.addItem(item)
        
        # 选中一行模拟高亮
        self.lyric_content.setCurrentRow(2)

if __name__ == "__main__":
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont("Segoe UI", 10) # 10pt approx 13px
    app.setFont(font)
    
    player = SodaPlayer()
    player.show()
    sys.exit(app.exec_())

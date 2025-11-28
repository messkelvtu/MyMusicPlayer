import sys
import os
import re
import json
import shutil
import random
import urllib.request
import urllib.parse
from datetime import datetime
from ctypes import windll, c_int, byref, sizeof, Structure, POINTER

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QFileDialog, QFrame, QAbstractItemView, QSlider, QDialog,
                             QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QStackedWidget, QSplitter, QGraphicsDropShadowEffect, QMenu,
                             QMessageBox, QRadioButton, QComboBox, QGroupBox, QInputDialog)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QTimer, QSize, QPoint
from PyQt5.QtGui import QFont, QColor, QCursor, QIcon
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# ================= 配置区 =================
SCALE = 1.25  # 全局缩放比例，解决125%缩放问题
CONFIG_FILE = "config.json"
HISTORY_FILE = "history.json"

# 自然清新主题色
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
    'selected': 'rgba(76, 175, 80, 0.15)',
    'error': '#E57373'
}

# 图标映射
ICONS = {
    "music": "🎵", "download": "📺", "disc": "💿", "history": "🕒",
    "heart": "❤️", "fire": "🔥", "star": "⭐", "sync": "🔄",
    "folder_plus": "📁+", "truck": "🚚", "folder_open": "📂", "mic": "🎤",
    "search": "🔍", "edit": "✏️", "random": "🔀", "play": "▶",
    "pause": "⏸", "prev": "⏮", "next": "⏭", "loop": "🔁",
    "single": "🔂", "shuffle": "🔀", "vol": "🔊", "offset": "🎚️",
    "back": "⌄"
}

# ================= 辅助工具 =================
def px(value):
    """根据缩放比例转换像素值，返回QSS字符串，例如 '15px'"""
    return f"{int(value * SCALE)}px"

def p_int(value):
    """根据缩放比例转换像素值，返回整数，用于Qt布局方法 (setContentsMargins, setFixedWidth等)"""
    return int(value * SCALE)

def ms_to_str(ms):
    """毫秒转时间字符串 00:00"""
    if not ms: return "00:00"
    s = int(ms / 1000)
    return f"{s//60:02}:{s%60:02}"

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

# ================= 线程工作类 =================
class BilibiliDownloader(QThread):
    """B站下载线程"""
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, url, path, mode):
        super().__init__()
        self.url = url
        self.path = path
        self.mode = mode 

    def run(self):
        try:
            import yt_dlp
        except ImportError:
            self.error_signal.emit("请先安装 yt-dlp: pip install yt-dlp")
            return

        if not os.path.exists(self.path):
            os.makedirs(self.path, exist_ok=True)

        def progress_hook(d):
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', '0%')
                self.progress_signal.emit(f"⬇️ 下载中: {percent}")

        opts = {
            'format': 'bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': os.path.join(self.path, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'noplaylist': self.mode == 'single',
            'ignoreerrors': True,
            'nocheckcertificate': True,
            'quiet': True,
        }

        try:
            self.progress_signal.emit("⏳ 解析链接中...")
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])
            self.finished_signal.emit(self.path)
        except Exception as e:
            self.error_signal.emit(str(e))

class LyricSearchWorker(QThread):
    """网易云歌词搜索线程"""
    search_finished = pyqtSignal(list)

    def __init__(self, keyword):
        super().__init__()
        self.keyword = keyword

    def run(self):
        try:
            import requests
            url = "http://music.163.com/api/search/get/web?csrf_token="
            headers = {'User-Agent': 'Mozilla/5.0'}
            data = urllib.parse.urlencode({
                's': self.keyword, 'type': 1, 'offset': 0, 'total': 'true', 'limit': 10
            }).encode('utf-8')
            
            res = requests.post(url, data=data, headers=headers, timeout=5).json()
            
            songs = []
            if res.get('result') and res['result'].get('songs'):
                for s in res['result']['songs']:
                    artist = s['artists'][0]['name'] if s['artists'] else "未知"
                    songs.append({
                        'name': s['name'],
                        'artist': artist,
                        'id': s['id'],
                        'dt': s.get('duration', 0)
                    })
            self.search_finished.emit(songs)
        except Exception as e:
            print(f"Search Error: {e}")
            self.search_finished.emit([])

class LyricDownloadWorker(QThread):
    """歌词下载线程"""
    finished_signal = pyqtSignal(str)

    def __init__(self, song_id, save_path):
        super().__init__()
        self.sid = song_id
        self.path = save_path

    def run(self):
        try:
            import requests
            url = f"http://music.163.com/api/song/lyric?os=pc&id={self.sid}&lv=-1&kv=-1&tv=-1"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
            
            lrc = res.get('lrc', {}).get('lyric', '')
            if lrc:
                with open(self.path, 'w', encoding='utf-8') as f:
                    f.write(lrc)
                self.finished_signal.emit(lrc)
            else:
                self.finished_signal.emit("")
        except Exception:
            self.finished_signal.emit("")

# ================= 自定义弹窗 =================
class ModernDialog(QDialog):
    """通用弹窗基类"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self.resize(p_int(500), p_int(400))
        self.setStyleSheet(f"""
            QDialog {{ background: {THEME['surface']}; }}
            QLabel {{ color: {THEME['text-primary']}; font-size: {px(14)}; }}
            QLineEdit {{
                border: 1px solid {THEME['border']}; border-radius: {px(8)};
                padding: {px(8)}; background: {THEME['background']}; font-size: {px(14)};
            }}
            QLineEdit:focus {{ border: 1px solid {THEME['primary']}; background: white; }}
            QGroupBox {{ 
                border: 1px solid {THEME['border']}; border-radius: {px(8)}; 
                margin-top: {px(20)}; font-weight: bold; color: {THEME['text-secondary']};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: {px(10)}; padding: 0 {px(5)}; }}
            QPushButton {{
                border-radius: {px(8)}; padding: {px(8)} {px(16)}; font-weight: bold; font-size: {px(14)};
            }}
            QPushButton[class="primary"] {{
                background: {THEME['primary']}; color: white; border: none;
            }}
            QPushButton[class="primary"]:hover {{ background: {THEME['primary-dark']}; }}
            QPushButton[class="outline"] {{
                background: transparent; border: 1px solid {THEME['border']}; color: {THEME['text-secondary']};
            }}
            QPushButton[class="outline"]:hover {{ border-color: {THEME['primary']}; color: {THEME['primary']}; }}
        """)

class DownloadDialog(ModernDialog):
    """下载弹窗"""
    def __init__(self, parent=None, collections=[]):
        super().__init__("下载音频", parent)
        layout = QVBoxLayout(self)
        
        # URL
        layout.addWidget(QLabel("视频链接:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("粘贴 Bilibili 视频链接...")
        layout.addWidget(self.url_input)

        # 模式
        gbox = QGroupBox("下载模式")
        g_layout = QHBoxLayout(gbox)
        self.rb_single = QRadioButton("单曲")
        self.rb_list = QRadioButton("合集/列表")
        self.rb_single.setChecked(True)
        g_layout.addWidget(self.rb_single)
        g_layout.addWidget(self.rb_list)
        layout.addWidget(gbox)

        # 文件夹
        layout.addWidget(QLabel("保存位置:"))
        self.combo_folder = QComboBox()
        self.combo_folder.addItem(f"{ICONS['folder_open']} 根目录", "")
        for c in collections:
            self.combo_folder.addItem(f"{ICONS['folder_plus']} {c}", c)
        self.combo_folder.setStyleSheet(f"""
            QComboBox {{ border: 1px solid {THEME['border']}; padding: {px(5)}; border-radius: {px(5)}; }}
        """)
        layout.addWidget(self.combo_folder)

        layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("取消")
        btn_cancel.setProperty("class", "outline")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("开始下载")
        btn_ok.setProperty("class", "primary")
        btn_ok.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def get_data(self):
        mode = 'single' if self.rb_single.isChecked() else 'playlist'
        folder = self.combo_folder.currentData()
        return self.url_input.text().strip(), mode, folder

class LyricSearchDialog(ModernDialog):
    """歌词搜索弹窗"""
    def __init__(self, keyword, parent=None):
        super().__init__("搜索歌词", parent)
        self.resize(p_int(600), p_int(500))
        self.result_id = None
        
        layout = QVBoxLayout(self)
        
        # 搜索栏
        h = QHBoxLayout()
        self.input = QLineEdit(keyword)
        btn_search = QPushButton("搜索")
        btn_search.setProperty("class", "primary")
        btn_search.clicked.connect(self.do_search)
        h.addWidget(self.input)
        h.addWidget(btn_search)
        layout.addLayout(h)

        # 列表
        self.list_widget = QTableWidget()
        self.list_widget.setColumnCount(3)
        self.list_widget.setHorizontalHeaderLabels(["歌名", "歌手", "时长"])
        self.list_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.list_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.list_widget.setShowGrid(False)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemDoubleClicked.connect(self.on_select)
        layout.addWidget(self.list_widget)

        self.status = QLabel("输入关键词搜索...")
        layout.addWidget(self.status)

    def do_search(self):
        kw = self.input.text()
        if not kw: return
        self.status.setText("搜索中...")
        self.worker = LyricSearchWorker(kw)
        self.worker.search_finished.connect(self.show_results)
        self.worker.start()

    def show_results(self, songs):
        self.list_widget.setRowCount(0)
        self.status.setText(f"找到 {len(songs)} 个结果")
        for i, s in enumerate(songs):
            self.list_widget.insertRow(i)
            self.list_widget.setItem(i, 0, QTableWidgetItem(s['name']))
            self.list_widget.setItem(i, 1, QTableWidgetItem(s['artist']))
            self.list_widget.setItem(i, 2, QTableWidgetItem(ms_to_str(s['dt'])))
            self.list_widget.item(i, 0).setData(Qt.UserRole, s['id'])

    def on_select(self, item):
        row = item.row()
        self.result_id = self.list_widget.item(row, 0).data(Qt.UserRole)
        self.accept()

# ================= 主程序 =================
class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 2025 - 自然清新版")
        self.resize(p_int(1280), p_int(800))
        
        # 样式与毛玻璃
        self.setStyleSheet(self.get_stylesheet())
        if os.name == 'nt':
            try:
                self.enable_acrylic()
            except: pass

        # 数据初始化
        self.music_folder = ""
        self.collections = []
        self.playlist = []
        self.history = []
        self.lyrics = [] 
        self.current_index = -1
        self.current_collection = None
        self.is_seeking = False # 拖动进度条标志
        
        # 播放器核心
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        
        # 初始化界面
        self.init_ui()
        self.load_config()
        
    def enable_acrylic(self):
        class ACCENT_POLICY(Structure):
            _fields_ = [("AccentState", c_int), ("AccentFlags", c_int), ("GradientColor", c_int), ("AnimationId", c_int)]
        class WINDOWCOMPOSITIONATTRIBDATA(Structure):
            _fields_ = [("Attribute", c_int), ("Data", POINTER(ACCENT_POLICY)), ("SizeOfData", c_int)]
        
        policy = ACCENT_POLICY()
        policy.AccentState = 4
        policy.GradientColor = 0xCCF1F8E9
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = POINTER(ACCENT_POLICY)(policy)
        data.SizeOfData = sizeof(policy)
        windll.user32.SetWindowCompositionAttribute(int(self.winId()), byref(data))

    def get_stylesheet(self):
        """生成支持缩放的QSS"""
        return f"""
        QMainWindow, QWidget {{
            background-color: {THEME['background']};
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            font-size: {px(14)}; color: {THEME['text-primary']}; outline: none;
        }}
        /* 侧边栏 */
        QFrame#Sidebar {{
            background-color: {THEME['surface']}; border-right: 1px solid {THEME['border']};
            min-width: {px(240)}; max-width: {px(240)};
        }}
        QLabel#Logo {{
            padding: {px(30)} {px(20)}; font-size: {px(24)}; font-weight: 900;
            color: {THEME['primary']}; border-bottom: 1px solid {THEME['border']};
        }}
        /* 按钮通用 */
        QPushButton.NavBtn, QPushButton.ToolBtn {{
            background: transparent; border: none; text-align: left;
            padding: {px(12)} {px(25)}; font-size: {px(14)}; color: {THEME['text-secondary']};
            border-radius: {px(8)}; margin: {px(2)} {px(12)}; border-left: {px(3)} solid transparent;
        }}
        QPushButton.NavBtn:hover, QPushButton.ToolBtn:hover {{
            background-color: {THEME['hover']}; color: {THEME['primary']}; border-left-color: {THEME['primary']};
        }}
        QPushButton.NavBtn:checked {{
            background-color: {THEME['selected']}; font-weight: bold; border-left-color: {THEME['primary']};
        }}
        /* 重点按钮 */
        QPushButton#DownloadBtn {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['primary']}, stop:1 {THEME['primary-light']});
            color: white; border-radius: {px(20)}; padding: {px(12)}; margin: {px(15)} {px(20)};
            font-weight: bold; font-size: {px(14)};
        }}
        QPushButton#DownloadBtn:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['primary-dark']}, stop:1 {THEME['primary']});
        }}
        /* 歌单列表 */
        QListWidget#CollectionList {{ background: transparent; border: none; }}
        QListWidget#CollectionList::item {{
            padding: {px(10)} {px(15)}; border-left: {px(2)} solid transparent;
            margin: 0 {px(10)}; border-radius: {px(8)}; color: {THEME['text-secondary']};
        }}
        QListWidget#CollectionList::item:selected {{
            background: {THEME['selected']}; color: {THEME['primary']}; font-weight: bold;
            border-left-color: {THEME['primary']};
        }}
        /* 搜索框 */
        QLineEdit#SearchBox {{
            background: {THEME['background']}; border: 1px solid {THEME['border']};
            border-radius: {px(20)}; padding: {px(10)} {px(20)}; min-width: {px(280)};
        }}
        QLineEdit#SearchBox:focus {{ border-color: {THEME['primary']}; background: white; }}
        /* 表格 */
        QTableWidget {{
            background: {THEME['surface']}; border: 1px solid {THEME['border']}; border-radius: {px(12)};
        }}
        QHeaderView::section {{
            background: {THEME['background']}; border: none; border-bottom: 1px solid {THEME['border']};
            padding: {px(15)}; font-weight: bold; color: {THEME['text-secondary']}; font-size: {px(13)};
        }}
        QTableWidget::item {{ padding-left: {px(10)}; border-bottom: 1px solid {THEME['border']}; }}
        QTableWidget::item:selected {{ background: {THEME['selected']}; color: {THEME['primary']}; }}
        /* 歌词页 */
        QListWidget#LyricContent, QListWidget#BigLyric {{
            background: transparent; border: none; font-size: {px(14)}; color: {THEME['text-secondary']};
        }}
        QListWidget#LyricContent::item:selected, QListWidget#BigLyric::item:selected {{
            color: {THEME['primary']}; font-size: {px(18)}; font-weight: bold;
        }}
        /* 底部播放栏 */
        QFrame#PlayerBar {{
            background: {THEME['surface']}; border-top: 1px solid {THEME['border']}; min-height: {px(100)};
        }}
        QSlider::groove:horizontal {{ height: {px(5)}; background: {THEME['border']}; border-radius: {px(3)}; }}
        QSlider::handle:horizontal {{
            background: {THEME['primary']}; width: {px(14)}; height: {px(14)}; margin: -{px(5)} 0; border-radius: {px(7)};
        }}
        QSlider::sub-page:horizontal {{ background: {THEME['primary']}; border-radius: {px(3)}; }}
        /* 控制按钮 */
        QPushButton.PlayerCtrlBtn {{
            background: transparent; border: none; font-size: {px(20)}; border-radius: {px(6)}; width: {px(40)}; height: {px(40)};
        }}
        QPushButton.PlayerCtrlBtn:hover {{ background: {THEME['hover']}; color: {THEME['primary']}; }}
        QPushButton#BigPlayBtn {{
            background: {THEME['primary']}; color: white; border-radius: {px(28)}; width: {px(56)}; height: {px(56)}; font-size: {px(24)};
        }}
        QPushButton#BigPlayBtn:hover {{ background: {THEME['primary-dark']}; }}
        /* 菜单 */
        QMenu {{ background: {THEME['surface']}; border: 1px solid {THEME['border']}; }}
        QMenu::item {{ padding: {px(8)} {px(20)}; }}
        QMenu::item:selected {{ background: {THEME['selected']}; color: {THEME['primary']}; }}
        """

    def init_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        main_h = QHBoxLayout(cw)
        main_h.setContentsMargins(0, 0, 0, 0); main_h.setSpacing(0)

        # 1. 侧边栏
        sidebar = QFrame(); sidebar.setObjectName("Sidebar")
        sb_layout = QVBoxLayout(sidebar); sb_layout.setContentsMargins(0, 0, 0, 0); sb_layout.setSpacing(0)
        
        sb_layout.addWidget(QLabel("🎵 汽水音乐", objectName="Logo"))
        
        btn_dl = QPushButton(f"{ICONS['download']} B站音频下载", objectName="DownloadBtn")
        btn_dl.setCursor(Qt.PointingHandCursor)
        btn_dl.clicked.connect(self.show_download_dialog)
        sb_layout.addWidget(btn_dl)

        nav_box = QVBoxLayout()
        # FIX: 使用 p_int() 代替 px()
        nav_box.setContentsMargins(0, p_int(10), 0, p_int(10))
        
        self.btn_all = QPushButton(f"{ICONS['disc']} 全部音乐", objectName="NavBtn")
        self.btn_all.setProperty("class", "NavBtn"); self.btn_all.setCheckable(True); self.btn_all.setChecked(True)
        self.btn_all.clicked.connect(lambda: self.switch_collection(None))
        
        self.btn_hist = QPushButton(f"{ICONS['history']} 最近播放", objectName="NavBtn")
        self.btn_hist.setProperty("class", "NavBtn"); self.btn_hist.setCheckable(True)
        self.btn_hist.clicked.connect(lambda: self.switch_collection("HISTORY"))
        
        nav_box.addWidget(self.btn_all); nav_box.addWidget(self.btn_hist)
        sb_layout.addLayout(nav_box)

        sb_layout.addWidget(QLabel("  歌单宝藏库", styleSheet=f"color:{THEME['text-secondary']}; font-weight:bold; font-size:{px(12)}; padding:{px(10)};"))
        
        self.list_coll = QListWidget(objectName="CollectionList")
        self.list_coll.setCursor(Qt.PointingHandCursor)
        self.list_coll.itemClicked.connect(self.on_collection_click)
        sb_layout.addWidget(self.list_coll)

        tool_box = QVBoxLayout()
        tool_box.setContentsMargins(0, p_int(10), 0, p_int(10)) # FIX: 使用 p_int()
        tools = [
            (f"{ICONS['sync']} 刷新库", self.full_scan),
            (f"{ICONS['folder_plus']} 新建合集", self.new_collection),
            (f"{ICONS['truck']} 批量移动", self.batch_move),
            (f"{ICONS['folder_open']} 根目录", self.select_root_folder)
        ]
        for txt, func in tools:
            b = QPushButton(txt); b.setProperty("class", "ToolBtn"); b.clicked.connect(func)
            b.setCursor(Qt.PointingHandCursor)
            tool_box.addWidget(b)
        sb_layout.addLayout(tool_box)
        main_h.addWidget(sidebar)

        # 2. 右侧区域
        right_widget = QWidget()
        r_layout = QVBoxLayout(right_widget); r_layout.setContentsMargins(0, 0, 0, 0); r_layout.setSpacing(0)

        # 顶部栏
        top_bar = QFrame(objectName="TopBar"); top_bar.setFixedHeight(p_int(70))
        top_bar.setStyleSheet(f"background:{THEME['surface']}; border-bottom:1px solid {THEME['border']};")
        tb_layout = QHBoxLayout(top_bar)
        # FIX: 使用 p_int() 代替 px()
        tb_layout.setContentsMargins(p_int(30), 0, p_int(30), 0)
        self.lbl_title = QLabel("全部音乐", styleSheet=f"font-size:{px(24)}; font-weight:bold; color:{THEME['primary']};")
        self.search_box = QLineEdit(objectName="SearchBox"); self.search_box.setPlaceholderText(f"{ICONS['search']} 搜索本地歌曲...")
        self.search_box.textChanged.connect(self.filter_song_list)
        tb_layout.addWidget(self.lbl_title); tb_layout.addStretch(); tb_layout.addWidget(self.search_box)
        r_layout.addWidget(top_bar)

        # 核心堆叠页 (Page 0: 列表+小歌词, Page 1: 大歌词页)
        self.stack = QStackedWidget()
        
        # Page 0: 列表模式
        page0 = QWidget()
        p0_layout = QHBoxLayout(page0)
        # FIX: 使用 p_int() 代替 px()
        p0_layout.setContentsMargins(p_int(20), p_int(20), p_int(20), p_int(20))
        
        # 左侧表格
        list_container = QWidget()
        lc_layout = QVBoxLayout(list_container); lc_layout.setContentsMargins(0,0,0,0)
        
        header_h = QHBoxLayout()
        header_h.addWidget(QLabel("歌曲列表", styleSheet=f"font-size:{px(18)}; font-weight:bold;"))
        btn_rand = QPushButton(f"{ICONS['random']} 随机播放")
        btn_rand.setStyleSheet(f"border:1px solid {THEME['border']}; padding:{px(5)} {px(10)}; border-radius:{px(5)};")
        btn_rand.clicked.connect(self.play_random)
        header_h.addStretch(); header_h.addWidget(btn_rand)
        lc_layout.addLayout(header_h)

        self.table = QTableWidget(columnCount=4)
        self.table.setHorizontalHeaderLabels(["标题", "歌手", "专辑", "时长"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False); self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setAlternatingRowColors(False)
        self.table.itemDoubleClicked.connect(self.play_from_table)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        lc_layout.addWidget(self.table)
        
        # 右侧小歌词
        lyric_mini = QFrame(); lyric_mini.setFixedWidth(p_int(320))
        lm_layout = QVBoxLayout(lyric_mini)
        lm_header = QHBoxLayout()
        lm_header.addWidget(QLabel("歌词", styleSheet="font-weight:bold;"))
        btn_sync = QPushButton(f"{ICONS['sync']} 手动匹配"); btn_sync.clicked.connect(self.manual_search_lyric)
        btn_sync.setStyleSheet(f"border:1px solid {THEME['border']}; border-radius:{px(5)}; padding:{px(4)}; font-size:{px(12)};")
        lm_header.addStretch(); lm_header.addWidget(btn_sync)
        lm_layout.addLayout(lm_header)
        
        self.list_lyric_mini = QListWidget(objectName="LyricContent")
        self.list_lyric_mini.setFocusPolicy(Qt.NoFocus); self.list_lyric_mini.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        lm_layout.addWidget(self.list_lyric_mini)

        p0_layout.addWidget(list_container, stretch=7)
        p0_layout.addWidget(lyric_mini, stretch=3)
        self.stack.addWidget(page0)

        # Page 1: 大歌词页
        page1 = QWidget(objectName="LyricPage")
        p1_layout = QHBoxLayout(page1)
        # FIX: 使用 p_int() 代替 px()
        p1_layout.setContentsMargins(p_int(50), p_int(50), p_int(50), p_int(50))
        
        # 左侧信息区
        info_area = QVBoxLayout(); info_area.setAlignment(Qt.AlignCenter)
        self.big_cover = QLabel()
        self.big_cover.setFixedSize(p_int(280), p_int(280))
        self.big_cover.setStyleSheet(f"background:qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {THEME['primary']}, stop:1 {THEME['primary-light']}); border-radius:{px(20)};")
        
        self.big_title = QLabel("歌曲标题", styleSheet=f"font-size:{px(28)}; font-weight:bold; color:{THEME['text-primary']}; margin-top:{px(20)};")
        self.big_artist = QLabel("歌手", styleSheet=f"font-size:{px(18)}; color:{THEME['text-secondary']};")
        
        btn_back = QPushButton(f"{ICONS['back']} 返回列表")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet(f"background:transparent; border:1px solid {THEME['border']}; border-radius:{px(20)}; padding:{px(8)} {px(20)}; margin-top:{px(30)}; color:{THEME['primary']};")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        info_area.addWidget(self.big_cover); info_area.addWidget(self.big_title); info_area.addWidget(self.big_artist); info_area.addWidget(btn_back)
        
        # 右侧大歌词
        self.list_lyric_big = QListWidget(objectName="BigLyric")
        self.list_lyric_big.setFocusPolicy(Qt.NoFocus); self.list_lyric_big.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # self.list_lyric_big.setAlignment(Qt.AlignCenter) # <--- 移除此行，因为它会导致报错

        p1_layout.addLayout(info_area, stretch=4)
        p1_layout.addWidget(self.list_lyric_big, stretch=6)
        self.stack.addWidget(page1)

        r_layout.addWidget(self.stack)

        # 3. 底部播放栏
        player_bar = QFrame(objectName="PlayerBar")
        pb_layout = QVBoxLayout(player_bar)
        # FIX: 使用 p_int() 代替 px()
        pb_layout.setContentsMargins(p_int(25), p_int(10), p_int(25), p_int(10))
        
        # 进度条
        prog_h = QHBoxLayout()
        self.lbl_curr = QLabel("00:00", styleSheet=f"color:{THEME['text-secondary']}; font-size:{px(12)};")
        self.slider = QSlider(Qt.Horizontal); self.slider.setCursor(Qt.PointingHandCursor)
        self.slider.sliderPressed.connect(self.on_slider_press)
        self.slider.sliderReleased.connect(self.on_slider_release)
        self.slider.valueChanged.connect(self.on_slider_move)
        self.lbl_total = QLabel("00:00", styleSheet=f"color:{THEME['text-secondary']}; font-size:{px(12)};")
        prog_h.addWidget(self.lbl_curr); prog_h.addWidget(self.slider); prog_h.addWidget(self.lbl_total)
        pb_layout.addLayout(prog_h)

        # 控制区
        ctrl_h = QHBoxLayout()
        
        # 左：歌曲信息 (点击跳转歌词页)
        self.btn_cover = QPushButton()
        self.btn_cover.setFixedSize(p_int(50), p_int(50))
        self.btn_cover.setStyleSheet(f"background:qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {THEME['primary']}, stop:1 {THEME['primary-light']}); border-radius:{px(8)}; border:none;")
        self.btn_cover.setCursor(Qt.PointingHandCursor)
        self.btn_cover.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        info_v = QVBoxLayout(); info_v.setSpacing(0); info_v.setAlignment(Qt.AlignVCenter)
        self.mini_title = QLabel("暂无播放", styleSheet=f"font-weight:bold; color:{THEME['text-primary']};")
        self.mini_artist = QLabel("--", styleSheet=f"color:{THEME['text-secondary']}; font-size:{px(12)};")
        info_v.addWidget(self.mini_title); info_v.addWidget(self.mini_artist)
        
        info_w = QWidget(); info_w.setCursor(Qt.PointingHandCursor) 
        info_w.mousePressEvent = lambda e: self.stack.setCurrentIndex(1) if e.button() == Qt.LeftButton else None
        info_l = QHBoxLayout(info_w); info_l.setContentsMargins(0,0,0,0)
        info_l.addWidget(self.btn_cover); info_l.addSpacing(p_int(10)); info_l.addLayout(info_v)
        ctrl_h.addWidget(info_w)
        
        ctrl_h.addStretch()

        # 中：播放控制
        self.btn_mode = QPushButton(ICONS['loop']); self.btn_mode.setProperty("class", "PlayerCtrlBtn"); self.btn_mode.clicked.connect(self.toggle_mode)
        btn_prev = QPushButton(ICONS['prev']); btn_prev.setProperty("class", "PlayerCtrlBtn"); btn_prev.clicked.connect(self.play_prev)
        self.btn_play = QPushButton(ICONS['play'], objectName="BigPlayBtn"); self.btn_play.setCursor(Qt.PointingHandCursor); self.btn_play.clicked.connect(self.toggle_play)
        btn_next = QPushButton(ICONS['next']); btn_next.setProperty("class", "PlayerCtrlBtn"); btn_next.clicked.connect(self.play_next)
        
        ctrl_h.addWidget(self.btn_mode); ctrl_h.addSpacing(p_int(10))
        ctrl_h.addWidget(btn_prev); ctrl_h.addWidget(self.btn_play); ctrl_h.addWidget(btn_next)
        ctrl_h.addStretch()

        # 右：音量
        ctrl_h.addWidget(QLabel(ICONS['vol']))
        self.vol_slider = QSlider(Qt.Horizontal); self.vol_slider.setRange(0, 100); self.vol_slider.setValue(80); self.vol_slider.setFixedWidth(p_int(80))
        self.vol_slider.valueChanged.connect(self.player.setVolume)
        ctrl_h.addWidget(self.vol_slider)

        pb_layout.addLayout(ctrl_h)
        r_layout.addWidget(player_bar)
        main_h.addWidget(right_widget)

    # ================= 逻辑功能 =================
    
    # --- 1. 数据与文件 ---
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    self.music_folder = cfg.get('folder', '')
            except: pass
        
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except: pass

        if self.music_folder:
            self.full_scan()

    def select_root_folder(self):
        d = QFileDialog.getExistingDirectory(self, "选择音乐根目录")
        if d:
            self.music_folder = d
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({'folder': d}, f)
            self.full_scan()

    def full_scan(self):
        if not self.music_folder: return
        self.collections = []
        exts = ('.mp3', '.flac', '.wav', '.m4a')
        
        # 扫描一级子文件夹作为歌单
        for name in os.listdir(self.music_folder):
            path = os.path.join(self.music_folder, name)
            if os.path.isdir(path):
                # 检查是否有音乐文件
                has_music = any(f.lower().endswith(exts) for f in os.listdir(path))
                if has_music:
                    self.collections.append(name)
        
        self.update_collection_list()
        self.switch_collection(None)

    def update_collection_list(self):
        self.list_coll.clear()
        defaults = ["❤️ 我的收藏", "🔥 流行音乐", "⭐ 经典老歌", "🎧 学习专注", "🚗 驾车音乐", "🏃 运动节奏"]
        for c in defaults:
            self.list_coll.addItem(QListWidgetItem(c))
        
        for c in self.collections:
            self.list_coll.addItem(QListWidgetItem(f"{ICONS['folder_open']} {c}"))

    def switch_collection(self, coll_name):
        self.current_collection = coll_name
        self.btn_all.setChecked(coll_name is None)
        self.btn_hist.setChecked(coll_name == "HISTORY")
        
        # 取消其他导航按钮选中状态
        for i in range(self.list_coll.count()):
            item = self.list_coll.item(i)
            # 这里是 QListWidget，不能用 setChecked，用setSelected来模拟
            if item.text().split(' ', 1)[-1] == coll_name:
                 item.setSelected(True)
            else:
                 item.setSelected(False)


        if coll_name is None:
            self.lbl_title.setText("全部音乐")
            self.scan_songs(self.music_folder, recursive=True)
        elif coll_name == "HISTORY":
            self.lbl_title.setText("最近播放")
            self.playlist = self.history
            self.update_table()
        else:
            # 去掉图标前缀
            real_name = coll_name.split(' ', 1)[-1] if ' ' in coll_name else coll_name
            self.lbl_title.setText(real_name)
            self.scan_songs(os.path.join(self.music_folder, real_name), recursive=False)
            
    def on_collection_click(self, item):
        # 取消导航按钮选中状态
        self.btn_all.setChecked(False)
        self.btn_hist.setChecked(False)
        
        txt = item.text()
        # 处理图标前缀
        if ' ' in txt:
            txt = txt.split(' ', 1)[1]
        
        # 检查是否为实际的文件夹合集
        if txt in self.collections:
            self.switch_collection(txt)
        else:
            # 默认歌单（只是占位逻辑，实际可以创建文件夹）
            self.lbl_title.setText(txt)
            # 模拟空列表
            self.playlist = []
            self.update_table()
            QMessageBox.information(self, "提示", f"这是默认歌单分类 '{txt}'，请通过新建合集来添加自定义文件夹。")

    def scan_songs(self, path, recursive=False):
        self.playlist = []
        exts = ('.mp3', '.flac', '.wav', '.m4a')
        if not os.path.exists(path): 
             self.update_table()
             return
        
        for root, dirs, files in os.walk(path):
            if not recursive and root != path: continue # 非递归模式只扫描当前目录
            
            for f in files:
                if f.lower().endswith(exts):
                    self.playlist.append(self._make_song_obj(root, f))
            
            if not recursive and root == path: break
        
        self.update_table()

    def _make_song_obj(self, folder, filename):
        # 简单解析文件名 "Artist - Title.mp3" 或默认
        name_no_ext = os.path.splitext(filename)[0]
        if ' - ' in name_no_ext:
            parts = name_no_ext.split(' - ')
            artist = parts[0]
            title = parts[1]
        else:
            artist = "未知歌手"
            title = name_no_ext
        
        return {
            'name': title, 'artist': artist, 'album': '未知专辑',
            'path': os.path.join(folder, filename),
            'filename': filename,
            'duration': '--:--' 
        }

    def update_table(self):
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.playlist))
        for i, s in enumerate(self.playlist):
            self.table.setItem(i, 0, QTableWidgetItem(s['name']))
            self.table.setItem(i, 1, QTableWidgetItem(s['artist']))
            self.table.setItem(i, 2, QTableWidgetItem(s['album']))
            self.table.setItem(i, 3, QTableWidgetItem(s['duration']))

    def filter_song_list(self, text):
        for i in range(self.table.rowCount()):
            match = False
            for j in range(3):
                item = self.table.item(i, j)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(i, not match)

    def new_collection(self):
        if not self.music_folder: return
        
        name, ok = QInputDialog.getText(self, "新建合集", "请输入合集名称:")
        if ok and name:
            safe = sanitize_filename(name)
            p = os.path.join(self.music_folder, safe)
            if not os.path.exists(p):
                os.makedirs(p, exist_ok=True)
                self.full_scan()
            else:
                 QMessageBox.warning(self, "错误", "合集已存在。")

    def batch_move(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if not rows: return
        
        if not self.collections:
            QMessageBox.warning(self, "提示", "没有合集可移动，请先新建合集")
            return
            
        menu = QMenu(self)
        for c in self.collections:
            action = menu.addAction(f"移动到: {c}")
            action.triggered.connect(lambda ch, col=c: self._do_move(rows, col))
        menu.exec_(QCursor.pos())

    def _do_move(self, rows, target_coll):
        target_dir = os.path.join(self.music_folder, target_coll)
        count = 0
        # 倒序处理防止索引错乱
        for r in reversed(rows):
            if r < len(self.playlist):
                song = self.playlist[r]
                src = song['path']
                dst = os.path.join(target_dir, song['filename'])
                try:
                    shutil.move(src, dst)
                    # 移动同名歌词
                    lrc = os.path.splitext(src)[0] + ".lrc"
                    if os.path.exists(lrc):
                        shutil.move(lrc, os.path.join(target_dir, os.path.splitext(song['filename'])[0]+".lrc"))
                    count += 1
                except Exception as e:
                    print(e)
        
        QMessageBox.information(self, "完成", f"成功移动 {count} 首歌曲")
        self.full_scan() # 刷新

    # --- 2. 播放控制 ---
    def play_from_table(self, item):
        self.play_index(item.row())

    def play_index(self, index):
        if not self.playlist or index < 0 or index >= len(self.playlist): return
        
        self.current_index = index
        song = self.playlist[index]
        
        # 记录历史
        if song not in self.history or self.history[0]['path'] != song['path']:
            self.history = [s for s in self.history if s['path'] != song['path']] # 移除旧的
            self.history.insert(0, song) # 插入新的
            if len(self.history) > 50: self.history.pop()
            # 优化：每次播放都保存，确保历史记录及时
            try:
                with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.history, f)
            except Exception as e:
                print(f"Error saving history: {e}")
        
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(song['path'])))
        self.player.play()
        
        # UI 更新
        self.mini_title.setText(song['name'])
        self.mini_artist.setText(song['artist'])
        self.big_title.setText(song['name'])
        self.big_artist.setText(song['artist'])
        self.btn_play.setText(ICONS['pause'])
        
        # 歌词处理
        self.load_lyrics(song)

    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText(ICONS['play'])
        else:
            if self.player.mediaStatus() == QMediaPlayer.NoMedia and self.playlist:
                self.play_index(0)
            else:
                self.player.play()
                self.btn_play.setText(ICONS['pause'])

    def play_next(self):
        if not self.playlist: return
        # 简单逻辑：顺序循环
        idx = (self.current_index + 1) % len(self.playlist)
        self.play_index(idx)

    def play_prev(self):
        if not self.playlist: return
        idx = (self.current_index - 1) % len(self.playlist)
        self.play_index(idx)

    def play_random(self):
        if not self.playlist: return
        idx = random.randint(0, len(self.playlist)-1)
        self.play_index(idx)

    def toggle_mode(self):
        modes = [ICONS['loop'], ICONS['single'], ICONS['shuffle']]
        curr = self.btn_mode.text()
        idx = (modes.index(curr) + 1) % len(modes)
        self.btn_mode.setText(modes[idx])

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            # 自动下一首
            self.play_next()

    def on_position_changed(self, pos):
        if not self.is_seeking:
            self.slider.setValue(pos)
        self.lbl_curr.setText(ms_to_str(pos))
        self.sync_lyrics_ui(pos)

    def on_duration_changed(self, dur):
        self.slider.setRange(0, dur)
        self.lbl_total.setText(ms_to_str(dur))
        # 更新表格中的时长
        if self.current_index >= 0 and self.current_index < len(self.playlist):
             self.playlist[self.current_index]['duration'] = ms_to_str(dur)
             self.table.item(self.current_index, 3).setText(ms_to_str(dur))
             # 确保在历史记录中也更新（如果存在）
             if self.history and self.history[0]['path'] == self.playlist[self.current_index]['path']:
                self.history[0]['duration'] = ms_to_str(dur)


    def on_slider_press(self): 
        self.is_seeking = True
    def on_slider_release(self): 
        self.player.setPosition(self.slider.value())
        self.is_seeking = False
    def on_slider_move(self, val):
        self.lbl_curr.setText(ms_to_str(val))

    # --- 3. 歌词系统 ---
    def load_lyrics(self, song):
        self.lyrics = []
        self.list_lyric_mini.clear()
        self.list_lyric_big.clear()
        
        lrc_path = os.path.splitext(song['path'])[0] + ".lrc"
        
        # 尝试使用本地文件
        if os.path.exists(lrc_path):
            try:
                with open(lrc_path, 'r', encoding='utf-8', errors='ignore') as f:
                    self.parse_lrc(f.read())
                return
            except Exception as e:
                print(f"Error reading local lyric: {e}")

        # 本地没有则自动搜索
        self.auto_match_lyric(song['name'])

    def parse_lrc(self, text):
        self.lyrics = []
        for line in text.splitlines():
            # [00:01.23]text
            m = re.match(r'\[(\d+):(\d+)(\.\d+)?\](.*)', line)
            if m:
                m1 = int(m.group(1)) * 60 * 1000
                s1 = int(m.group(2)) * 1000
                ms = int(float(m.group(3) or 0) * 1000)
                txt = m.group(4).strip()
                if txt:
                    self.lyrics.append({'t': m1+s1+ms, 'txt': txt})
        
        if not self.lyrics:
            self.list_lyric_mini.addItem(QListWidgetItem("歌词解析失败或为空"))
            self.list_lyric_big.addItem(QListWidgetItem("歌词解析失败或为空"))
            return

        # 填充 UI
        self.list_lyric_mini.clear()
        self.list_lyric_big.clear()
        for l in self.lyrics:
            # 创建 QListWidgetItem 时可以设置对齐方式
            item_mini = QListWidgetItem(l['txt'])
            item_big = QListWidgetItem(l['txt'])
            item_big.setTextAlignment(Qt.AlignCenter) # 在 item 级别设置对齐
            
            self.list_lyric_mini.addItem(item_mini)
            self.list_lyric_big.addItem(item_big)

    def auto_match_lyric(self, keyword):
        self.list_lyric_mini.clear(); self.list_lyric_mini.addItem("正在自动搜索歌词...")
        self.list_lyric_big.clear(); self.list_lyric_big.addItem("正在自动搜索歌词...")
        worker = LyricSearchWorker(keyword)
        worker.search_finished.connect(self.on_auto_search_result)
        self._temp_worker = worker 
        worker.start()

    def on_auto_search_result(self, songs):
        if songs:
            # 自动下载第一个
            sid = songs[0]['id']
            if self.current_index >= 0:
                song = self.playlist[self.current_index]
                path = os.path.splitext(song['path'])[0] + ".lrc"
                dl = LyricDownloadWorker(sid, path)
                dl.finished_signal.connect(lambda txt: self.parse_lrc(txt) if txt else self.on_no_lyric())
                self._temp_dl = dl
                dl.start()
        else:
            self.on_no_lyric()

    def on_no_lyric(self):
        self.list_lyric_mini.clear(); self.list_lyric_mini.addItem("暂无歌词")
        self.list_lyric_big.clear(); self.list_lyric_big.addItem("暂无歌词")

    def manual_search_lyric(self):
        if self.current_index < 0: 
            QMessageBox.warning(self, "提示", "请先播放一首歌曲。")
            return
            
        song = self.playlist[self.current_index]
        dlg = LyricSearchDialog(song['name'], self)
        if dlg.exec_() == QDialog.Accepted and dlg.result_id:
            path = os.path.splitext(song['path'])[0] + ".lrc"
            # 清空并提示
            self.list_lyric_mini.clear(); self.list_lyric_mini.addItem("正在下载并匹配歌词...")
            self.list_lyric_big.clear(); self.list_lyric_big.addItem("正在下载并匹配歌词...")
            
            dl = LyricDownloadWorker(dlg.result_id, path)
            dl.finished_signal.connect(lambda txt: self.parse_lrc(txt) if txt else self.on_no_lyric())
            self._temp_dl = dl
            dl.start()

    def sync_lyrics_ui(self, pos):
        if not self.lyrics: return
        
        idx = -1
        # 找到当前应该高亮的歌词行
        for i, l in enumerate(self.lyrics):
            if pos >= l['t']: idx = i
            else: break
        
        if idx >= 0:
            # 仅在行数变化时更新，减少UI操作
            if idx != self.list_lyric_mini.currentRow():
                # 同步 Mini
                if idx < self.list_lyric_mini.count():
                    self.list_lyric_mini.setCurrentRow(idx)
                    item = self.list_lyric_mini.item(idx)
                    # 滚动到中心，实现丝滑歌词效果
                    self.list_lyric_mini.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                
                # 同步 Big
                if idx < self.list_lyric_big.count():
                    self.list_lyric_big.setCurrentRow(idx)
                    item = self.list_lyric_big.item(idx)
                    self.list_lyric_big.scrollToItem(item, QAbstractItemView.PositionAtCenter)

    # --- 4. B站下载 ---
    def show_download_dialog(self):
        if not self.music_folder:
            QMessageBox.warning(self, "提示", "请先设置音乐根目录")
            return
        
        dlg = DownloadDialog(self, self.collections)
        if dlg.exec_() == QDialog.Accepted:
            url, mode, folder = dlg.get_data()
            if not url: return
            
            save_path = os.path.join(self.music_folder, folder) if folder else self.music_folder
            
            self.dl_worker = BilibiliDownloader(url, save_path, mode)
            self.dl_worker.progress_signal.connect(lambda s: self.setWindowTitle(f"汽水音乐 - {s}"))
            self.dl_worker.finished_signal.connect(self.on_dl_finish)
            self.dl_worker.error_signal.connect(lambda e: QMessageBox.warning(self, "下载出错", e))
            self.dl_worker.start()

    def on_dl_finish(self, path):
        self.setWindowTitle("汽水音乐 2025 - 自然清新版")
        QMessageBox.information(self, "完成", "下载任务结束")
        self.full_scan()

    # --- 5. 右键菜单 ---
    def show_context_menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid(): return
        
        menu = QMenu(self)
        row = idx.row()
        
        menu.addAction(f"{ICONS['play']} 播放", lambda: self.play_index(row))
        # 播放当前选中的歌曲，然后触发歌词搜索
        menu.addAction(f"{ICONS['search']} 搜索并绑定歌词", lambda: [self.play_index(row), self.manual_search_lyric()]) 
        
        # 移动子菜单
        mv_menu = menu.addMenu(f"{ICONS['truck']} 移动到...")
        for c in self.collections:
            mv_menu.addAction(c, lambda ch, col=c: self._do_move([row], col))
            
        menu.addSeparator()
        menu.addAction(f"🗑️ 删除文件", lambda: self.delete_song(row))
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def delete_song(self, row):
        if row >= len(self.playlist): return
        song = self.playlist[row]
        ret = QMessageBox.question(self, "确认", f"确定永久删除 '{song['name']}' 吗？")
        if ret == QMessageBox.Yes:
            try:
                os.remove(song['path'])
                lrc = os.path.splitext(song['path'])[0] + ".lrc"
                if os.path.exists(lrc): os.remove(lrc)
                self.full_scan()
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

if __name__ == "__main__":
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    win = SodaPlayer()
    win.show()
    sys.exit(app.exec_())

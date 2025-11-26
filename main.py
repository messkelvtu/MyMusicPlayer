import sys
import os
import json
import shutil
import random
import threading
import re
import urllib.request
import urllib.parse
import time
import ctypes
from ctypes import windll, c_int, byref, sizeof, Structure, POINTER, c_char
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QFileDialog, QFrame, QAbstractItemView, QCheckBox,
                             QGraphicsDropShadowEffect, QInputDialog, QMessageBox, 
                             QFontDialog, QMenu, QAction, QSlider, QDialog, QRadioButton, 
                             QComboBox, QLineEdit, QTabWidget, QSpinBox, QColorDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QGraphicsBlurEffect)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize, QCoreApplication, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QBrush, QPainter, QLinearGradient

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

# --- Windows Acrylic (毛玻璃) API 结构 ---
class ACCENT_POLICY(Structure):
    _fields_ = [
        ("AccentState", c_int),
        ("AccentFlags", c_int),
        ("GradientColor", c_int),
        ("AnimationId", c_int)
    ]

class WINDOWCOMPOSITIONATTRIBDATA(Structure):
    _fields_ = [
        ("Attribute", c_int),
        ("Data", POINTER(ACCENT_POLICY)),
        ("SizeOfData", c_int)
    ]

def enable_acrylic(hwnd):
    """在 Windows 10/11 上开启亚克力毛玻璃效果"""
    try:
        # 3 = ACCENT_ENABLE_BLURBEHIND, 4 = ACCENT_ENABLE_ACRYLICBLURBEHIND
        policy = ACCENT_POLICY()
        policy.AccentState = 4  # 开启亚克力
        policy.GradientColor = 0xCCF2F2F2 # 这里的颜色控制底色和透明度 (AABBGGRR)
        
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19 # WCA_ACCENT_POLICY
        data.Data = POINTER(ACCENT_POLICY)(policy)
        data.SizeOfData = sizeof(policy)
        
        windll.user32.SetWindowCompositionAttribute(int(hwnd), byref(data))
    except Exception as e:
        print(f"无法开启毛玻璃效果: {e}")

# --- 极光 UI 样式表 (iOS 风格) ---
STYLESHEET = """
/* 全局字体 */
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    color: #1c1c1e; /* iOS 深灰 */
}

/* 主窗口透明，交给代码处理毛玻璃 */
QMainWindow {
    background: transparent; 
}

/* 侧边栏 - 半透明磨砂白 */
QFrame#Sidebar {
    background-color: rgba(255, 255, 255, 180);
    border-right: 1px solid rgba(0, 0, 0, 0.05);
}

/* Logo */
QLabel#Logo {
    font-size: 24px; 
    font-weight: 800; 
    color: #31c27c; /* 品牌绿 */
    padding: 30px 20px 10px 20px;
    letter-spacing: 1px;
}

/* 分区标题 */
QLabel#SectionTitle {
    font-size: 11px;
    color: #8e8e93; /* iOS 次级文本色 */
    padding: 15px 25px 5px 25px;
    font-weight: bold;
    text-transform: uppercase;
}

/* 导航按钮 - iOS 列表风格 */
QPushButton.NavBtn {
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 12px 25px;
    font-size: 15px;
    color: #333;
    border-radius: 12px;
    margin: 2px 10px;
}
QPushButton.NavBtn:hover {
    background-color: rgba(0, 0, 0, 0.05);
}
QPushButton.NavBtn:checked {
    background-color: #e6f7ff;
    color: #31c27c;
    font-weight: bold;
}

/* 强调色按钮 (B站下载) */
QPushButton#DownloadBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF6699, stop:1 #FF8eb3);
    color: white;
    font-weight: bold;
    border-radius: 18px;
    text-align: center;
    margin: 10px 15px;
    padding: 8px;
    box-shadow: 0 4px 10px rgba(255, 102, 153, 0.3);
}
QPushButton#DownloadBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4d88, stop:1 #ff7aa5);
}

/* 列表/表格 - 极简风格 */
QListWidget, QTableWidget {
    background-color: rgba(255, 255, 255, 150);
    border: none;
    outline: none;
    border-radius: 15px;
    margin: 10px;
}
QListWidget::item, QTableWidget::item {
    padding: 10px;
    margin: 2px 5px;
    border-radius: 8px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.03);
}
QListWidget::item:selected, QTableWidget::item:selected {
    background-color: rgba(49, 194, 124, 0.15);
    color: #31c27c;
}
QHeaderView::section {
    background-color: transparent;
    border: none;
    border-bottom: 2px solid rgba(0,0,0,0.05);
    padding: 8px;
    font-weight: bold;
    color: #8e8e93;
}

/* 底部播放条 - 悬浮卡片 */
QFrame#PlayerBar {
    background-color: rgba(255, 255, 255, 220);
    border-top: 1px solid rgba(0, 0, 0, 0.05);
}

/* 播放按钮 - 圆形 */
QPushButton#PlayBtn { 
    background-color: #31c27c; 
    color: white; 
    border-radius: 28px; 
    font-size: 24px; 
    min-width: 56px; 
    min-height: 56px;
    margin: 0 10px;
}
QPushButton#PlayBtn:hover { 
    background-color: #2caf6f; 
    margin-top: -2px; /* 微动效 */
}

/* 控制图标 */
QPushButton.CtrlBtn {
    background: transparent;
    border: none;
    font-size: 20px;
    color: #333;
    border-radius: 20px;
    min-width: 40px;
    min-height: 40px;
}
QPushButton.CtrlBtn:hover {
    background-color: rgba(0,0,0,0.05);
    color: #31c27c;
}

/* 滑块 - iOS 样式 */
QSlider::groove:horizontal {
    border: 1px solid #ddd;
    height: 4px;
    background: #e5e5e5;
    margin: 2px 0;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: white;
    border: 1px solid #ccc;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
QSlider::sub-page:horizontal {
    background: #31c27c;
    border-radius: 2px;
}
"""

# --- 工具函数 ---
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def ms_to_str(ms):
    if not ms: return "00:00"
    s = ms // 1000
    return f"{s//60:02}:{s%60:02}"

# --- 线程与对话框类 (保持原有逻辑，样式已通过 QSS 优化) ---

class LyricListSearchWorker(QThread):
    search_finished = pyqtSignal(list)
    def __init__(self, keyword):
        super().__init__()
        self.keyword = keyword
    def run(self):
        try:
            url = "http://music.163.com/api/search/get/web?csrf_token="
            headers = {'User-Agent': 'Mozilla/5.0'}
            data = urllib.parse.urlencode({'s': self.keyword, 'type': 1, 'offset': 0, 'total': 'true', 'limit': 20}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req) as f:
                res = json.loads(f.read().decode('utf-8'))
            results = []
            if res.get('result') and res['result'].get('songs'):
                for s in res['result']['songs']:
                    artist = s['artists'][0]['name'] if s['artists'] else "未知"
                    duration = s.get('duration', 0)
                    results.append({'name': s['name'], 'artist': artist, 'id': s['id'], 'duration': duration, 'duration_str': ms_to_str(duration)})
            self.search_finished.emit(results)
        except: self.search_finished.emit([])

class LyricSearchDialog(QDialog):
    def __init__(self, song_name, duration_ms=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("搜索歌词")
        self.resize(700, 500)
        self.result_id = None
        self.duration_ms = duration_ms
        layout = QVBoxLayout(self)
        h = QHBoxLayout()
        self.input_key = QLineEdit(song_name)
        self.input_key.setPlaceholderText("输入歌名/歌手")
        btn = QPushButton("搜索")
        btn.clicked.connect(self.start_search)
        h.addWidget(self.input_key); h.addWidget(btn)
        layout.addLayout(h)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["歌名", "歌手", "时长", "ID"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemDoubleClicked.connect(self.on_select)
        layout.addWidget(self.table)
        
        if duration_ms > 0:
            layout.addWidget(QLabel(f"本地时长: {ms_to_str(duration_ms)}", styleSheet="color:#888; font-size:12px;"))
        
        btn_bind = QPushButton("选中并下载")
        btn_bind.setStyleSheet("background-color:#31c27c; color:white; padding:10px; border-radius:5px; font-weight:bold;")
        btn_bind.clicked.connect(self.confirm_bind)
        layout.addWidget(btn_bind)

    def start_search(self):
        key = self.input_key.text()
        if not key: return
        self.table.setRowCount(0)
        self.worker = LyricListSearchWorker(key)
        self.worker.search_finished.connect(self.on_search_done)
        self.worker.start()

    def on_search_done(self, results):
        self.table.setRowCount(len(results))
        for i, item in enumerate(results):
            self.table.setItem(i, 0, QTableWidgetItem(item['name']))
            self.table.setItem(i, 1, QTableWidgetItem(item['artist']))
            t_item = QTableWidgetItem(item['duration_str'])
            if abs(item['duration'] - self.duration_ms) < 3000 and self.duration_ms > 0:
                t_item.setForeground(QColor("#31c27c")); t_item.setToolTip("推荐")
            self.table.setItem(i, 2, t_item)
            self.table.setItem(i, 3, QTableWidgetItem(str(item['id'])))

    def on_select(self, item): self.confirm_bind()
    def confirm_bind(self):
        row = self.table.currentRow()
        if row >= 0: self.result_id = self.table.item(row, 3).text(); self.accept()
        else: QMessageBox.warning(self, "提示", "请选择一行")

class LyricDownloader(QThread):
    finished_signal = pyqtSignal(str)
    def __init__(self, song_id, save_path):
        super().__init__()
        self.sid = song_id; self.path = save_path
    def run(self):
        try:
            url = f"http://music.163.com/api/song/lyric?os=pc&id={self.sid}&lv=-1&kv=-1&tv=-1"
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as f: res = json.loads(f.read().decode('utf-8'))
            if 'lrc' in res and 'lyric' in res['lrc']:
                lrc = res['lrc']['lyric']
                with open(self.path, 'w', encoding='utf-8') as f: f.write(lrc)
                self.finished_signal.emit(lrc)
        except: pass

class BatchInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑信息")
        self.resize(300, 200)
        layout = QVBoxLayout(self)
        self.check_artist = QCheckBox("修改歌手:"); self.input_artist = QLineEdit()
        self.check_album = QCheckBox("修改专辑:"); self.input_album = QLineEdit()
        layout.addWidget(self.check_artist); layout.addWidget(self.input_artist)
        layout.addSpacing(10)
        layout.addWidget(self.check_album); layout.addWidget(self.input_album)
        btn_box = QHBoxLayout()
        btn_ok = QPushButton("保存"); btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)
        layout.addLayout(btn_box)
    def get_data(self):
        a = self.input_artist.text() if self.check_artist.isChecked() else None
        b = self.input_album.text() if self.check_album.isChecked() else None
        return a, b

class BatchRenameDialog(QDialog):
    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量重命名")
        self.resize(500, 500)
        self.playlist = playlist
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        t1 = QWidget(); l1 = QVBoxLayout(t1)
        self.f = QLineEdit(); self.f.setPlaceholderText("查找")
        self.r = QLineEdit(); self.r.setPlaceholderText("替换")
        l1.addWidget(QLabel("查找:")); l1.addWidget(self.f)
        l1.addWidget(QLabel("替换:")); l1.addWidget(self.r); l1.addStretch()
        self.tabs.addTab(t1, "替换")
        
        t2 = QWidget(); l2 = QVBoxLayout(t2)
        self.sh = QSpinBox(); self.sh.setRange(0,50)
        self.st = QSpinBox(); self.st.setRange(0,50)
        l2.addWidget(QLabel("删前N字:")); l2.addWidget(self.sh)
        l2.addWidget(QLabel("删后N字:")); l2.addWidget(self.st); l2.addStretch()
        self.tabs.addTab(t2, "裁剪")
        
        layout.addWidget(self.tabs)
        
        self.list = QListWidget()
        for s in playlist: 
            it = QListWidgetItem(s["name"]); it.setFlags(it.flags()|Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked)
            self.list.addItem(it)
        layout.addWidget(self.list)
        
        btn = QPushButton("执行"); btn.clicked.connect(self.accept); layout.addWidget(btn)

    def get_data(self):
        idxs = [i for i in range(self.list.count()) if self.list.item(i).checkState()==Qt.Checked]
        if self.tabs.currentIndex()==0: return "replace", (self.f.text(), self.r.text()), idxs
        else: return "trim", (self.sh.value(), self.st.value()), idxs

class DesktopLyricWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1200, 180)
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(0,0,0,0)
        self.font_color = QColor(255, 255, 255); self.current_font = QFont("Microsoft YaHei", 36, QFont.Bold)
        self.labels = []
        for i in range(3):
            l = QLabel(""); l.setAlignment(Qt.AlignCenter); self.labels.append(l); self.layout.addWidget(l)
        self.update_styles(); self.locked = False

    def update_styles(self):
        bs = self.current_font.pointSize()
        shadow = QColor(0, 0, 0, 220)
        for i, l in enumerate(self.labels):
            eff = QGraphicsDropShadowEffect(); eff.setBlurRadius(12); eff.setColor(shadow); eff.setOffset(0, 0)
            l.setGraphicsEffect(eff)
            f = QFont(self.current_font)
            css_col = self.font_color.name()
            if i==1: f.setPointSize(bs); l.setStyleSheet(f"color: {css_col};")
            else: 
                f.setPointSize(int(bs*0.6))
                r,g,b = self.font_color.red(), self.font_color.green(), self.font_color.blue()
                l.setStyleSheet(f"color: rgba({r},{g},{b}, 180);")
            l.setFont(f)

    def set_lyrics(self, p, c, n): self.labels[0].setText(p); self.labels[1].setText(c); self.labels[2].setText(n)
    def mousePressEvent(self, e):
        if e.button()==Qt.LeftButton and not self.locked: self.dp = e.globalPos()-self.frameGeometry().topLeft()
        elif e.button()==Qt.RightButton: self.show_menu(e.globalPos())
    def mouseMoveEvent(self, e):
        if e.buttons()==Qt.LeftButton and not self.locked: self.move(e.globalPos()-self.dp)
    def show_menu(self, p):
        m = QMenu(); m.addAction("🎨 颜色", self.ch_color); m.addAction("🅰️ 字体", self.ch_font)
        m.addAction("🔒 锁定" if not self.locked else "🔒 解锁", self.t_lock); m.addAction("❌ 关闭", self.hide)
        m.exec_(p)
    def ch_color(self): 
        c = QColorDialog.getColor(self.font_color, self); 
        if c.isValid(): self.font_color=c; self.update_styles()
    def ch_font(self):
        f,ok = QFontDialog.getFont(self.current_font, self)
        if ok: self.current_font=f; self.update_styles()
    def t_lock(self): self.locked = not self.locked

class DownloadDialog(QDialog):
    def __init__(self, parent=None, current_p=1, collections=[]):
        super().__init__(parent)
        self.setWindowTitle("下载")
        self.resize(400, 300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"当前为第 {current_p} P，选择模式："))
        self.rb_s = QRadioButton(f"单曲 (P{current_p})"); self.rb_l = QRadioButton(f"合集 (P{current_p}-End)")
        self.rb_s.setChecked(True)
        layout.addWidget(self.rb_s); layout.addWidget(self.rb_l); layout.addSpacing(10)
        
        layout.addWidget(QLabel("存入："))
        self.cb = QComboBox(); self.cb.addItem("根目录", ""); 
        for c in collections: self.cb.addItem(f"📁 {c}", c)
        self.cb.addItem("➕ 新建...", "NEW"); layout.addWidget(self.cb)
        self.inp_new = QLineEdit(); self.inp_new.setPlaceholderText("新合集名"); self.inp_new.hide(); layout.addWidget(self.inp_new)
        self.cb.currentIndexChanged.connect(lambda: self.inp_new.setVisible(self.cb.currentData()=="NEW"))
        
        layout.addSpacing(10)
        self.art = QLineEdit(); self.art.setPlaceholderText("预设歌手"); layout.addWidget(self.art)
        self.alb = QLineEdit(); self.alb.setPlaceholderText("预设专辑"); layout.addWidget(self.alb)
        
        btn = QPushButton("下载"); btn.clicked.connect(self.accept); layout.addWidget(btn)

    def get_data(self):
        mode = "playlist" if self.rb_l.isChecked() else "single"
        f = self.cb.currentData()
        if f=="NEW": f = self.inp_new.text().strip()
        return mode, f, self.art.text(), self.alb.text()

class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str); finished_signal = pyqtSignal(str); error_signal = pyqtSignal(str)
    def __init__(self, u, p, m, sp): super().__init__(); self.u=u; self.p=p; self.m=m; self.sp=sp
    def run(self):
        if not yt_dlp: return self.error_signal.emit("无yt-dlp")
        if not os.path.exists(self.p): os.makedirs(self.p, exist_ok=True)
        def hk(d):
            if d['status']=='downloading': self.progress_signal.emit(f"⬇️ {d.get('_percent_str','')} {os.path.basename(d.get('filename',''))}")
        opt = {
            'format':'bestaudio[ext=m4a]/best', 'outtmpl':os.path.join(self.p,'%(title)s.%(ext)s'),
            'overwrites':True, 'noplaylist':False, 'playlist_items': f"{self.sp}-" if self.m=='playlist' else str(self.sp),
            'progress_hooks':[hk], 'quiet':True, 'nocheckcertificate':True
        }
        try:
            with yt_dlp.YoutubeDL(opt) as y: y.download([self.u])
            self.finished_signal.emit(self.p)
        except Exception as e: self.error_signal.emit(str(e))

class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 (iOS极光版)")
        self.resize(1180, 780)
        self.setStyleSheet(STYLESHEET)
        
        # 开启毛玻璃
        self.setAttribute(Qt.WA_TranslucentBackground)
        if os.name == 'nt':
            try: enable_acrylic(int(self.winId()))
            except: pass

        self.music_folder = ""; self.current_collection = ""; self.collections = []
        self.playlist = []; self.history = []; self.lyrics = []
        self.current_index = -1; self.offset = 0.0; self.saved_offsets = {}; self.metadata = {}
        self.mode = 0; self.rate = 1.0; self.is_slider_pressed = False
        
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.stateChanged.connect(self.on_state_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.error.connect(self.handle_player_error)
        
        self.desktop_lyric = DesktopLyricWindow()
        self.desktop_lyric.show()
        
        self.init_ui()
        self.load_config()

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        
        # Sidebar
        sb = QFrame(); sb.setObjectName("Sidebar"); sb.setFixedWidth(260)
        sl = QVBoxLayout(sb); sl.setContentsMargins(0,0,0,0)
        sl.addWidget(QLabel("✨ SODA MUSIC", objectName="Logo"))
        
        btn_c = QWidget(); btn_l = QVBoxLayout(btn_c); btn_l.setSpacing(8)
        b1 = QPushButton("📺  B站下载"); b1.setObjectName("DownloadBtn"); b1.clicked.connect(self.dl_bili); btn_l.addWidget(b1)
        b2 = QPushButton("➕  新建合集"); b2.setProperty("NavBtn",True); b2.clicked.connect(self.new_coll); btn_l.addWidget(b2)
        b3 = QPushButton("🔄  刷新库"); b3.setProperty("NavBtn",True); b3.clicked.connect(self.full_scan); btn_l.addWidget(b3)
        sl.addWidget(btn_c)
        
        sl.addWidget(QLabel("  我的音乐库", objectName="SectionTitle"))
        self.nav = QListWidget(); self.nav.setStyleSheet("background:transparent; border:none; font-size:14px;")
        self.nav.itemClicked.connect(self.switch_coll)
        sl.addWidget(self.nav)
        
        sl.addStretch()
        bf = QPushButton("📂  管理根目录"); bf.setProperty("NavBtn",True); bf.clicked.connect(self.sel_folder); sl.addWidget(bf)
        bl = QPushButton("🎤  桌面歌词"); bl.setProperty("NavBtn",True); bl.clicked.connect(self.tog_lyric); sl.addWidget(bl)
        layout.addWidget(sb)
        
        # Main
        rp = QWidget(); rl = QVBoxLayout(rp); rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)
        
        # Title
        self.lbl_title = QLabel("全部音乐"); self.lbl_title.setStyleSheet("font-size:22px; font-weight:bold; padding:20px; color:#333;")
        rl.addWidget(self.lbl_title)
        
        # Content
        cont = QWidget(); cl = QHBoxLayout(cont); cl.setContentsMargins(10,0,10,0)
        self.table = QTableWidget(); self.table.setColumnCount(4); 
        self.table.setHorizontalHeaderLabels(["标题", "歌手", "专辑", "时长"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False); self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.itemDoubleClicked.connect(self.play_sel); self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_menu)
        cl.addWidget(self.table, stretch=6)
        
        self.lrc_p = QListWidget(); self.lrc_p.setFocusPolicy(Qt.NoFocus)
        self.lrc_p.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.lrc_p.setStyleSheet("background:transparent; color:#888; font-size:14px; border:none;")
        cl.addWidget(self.lrc_p, stretch=4)
        rl.addWidget(cont)
        
        # Bar
        bar = QFrame(); bar.setObjectName("PlayerBar"); bar.setFixedHeight(110)
        bl = QVBoxLayout(bar)
        
        pl = QHBoxLayout(); self.lc = QLabel("00:00"); self.lt = QLabel("00:00"); self.sl = QSlider(Qt.Horizontal)
        self.sl.sliderPressed.connect(self.sp); self.sl.sliderReleased.connect(self.sr); self.sl.valueChanged.connect(self.sm)
        pl.addWidget(self.lc); pl.addWidget(self.sl); pl.addWidget(self.lt); bl.addLayout(pl)
        
        cl = QHBoxLayout()
        self.bm = QPushButton("🔁"); self.bm.setProperty("CtrlBtn",True); self.bm.clicked.connect(self.tm)
        bp = QPushButton("⏮"); bp.setProperty("CtrlBtn",True); bp.clicked.connect(self.pp)
        self.bp = QPushButton("▶"); self.bp.setObjectName("PlayBtn"); self.bp.clicked.connect(self.tp)
        bn = QPushButton("⏭"); bn.setProperty("CtrlBtn",True); bn.clicked.connect(self.pn)
        self.br = QPushButton("1.0x"); self.br.setProperty("CtrlBtn",True); self.br.clicked.connect(self.tr)
        cl.addStretch(); cl.addWidget(self.bm); cl.addSpacing(10); cl.addWidget(bp); cl.addWidget(self.bp)
        cl.addWidget(bn); cl.addSpacing(10); cl.addWidget(self.br); cl.addStretch()
        
        ol = QHBoxLayout()
        bs = QPushButton("⏪"); bs.setProperty("OffsetBtn",True); bs.clicked.connect(lambda: self.ao(-0.5))
        self.lo = QLabel("0.0s"); self.lo.setStyleSheet("color:#999; font-size:10px;")
        bf = QPushButton("⏩"); bf.setProperty("OffsetBtn",True); bf.clicked.connect(lambda: self.ao(0.5))
        ol.addStretch(); ol.addWidget(bs); ol.addWidget(self.lo); ol.addWidget(bf)
        
        bl.addLayout(cl); bl.addLayout(ol)
        rl.addWidget(bar)
        layout.addWidget(rp)

    # Logic
    def full_scan(self):
        if not self.music_folder: return
        self.collections = []
        ext = ('.mp3','.wav','.m4a','.flac','.mp4')
        for d in os.listdir(self.music_folder):
            fd = os.path.join(self.music_folder, d)
            if os.path.isdir(fd):
                fs = [f for f in os.listdir(fd) if f.lower().endswith(ext)]
                if len(fs) > 1: self.collections.append(d) # 只有>1首才算合集
        self.nav.clear(); self.nav.addItem("💿  全部歌曲"); self.nav.addItem("🕒  最近播放")
        for c in self.collections: self.nav.addItem(f"📁  {c}")
        self.load_list()

    def switch_coll(self, item):
        t = item.text()
        if "全部" in t: self.current_collection=""; self.lbl_title.setText("全部音乐")
        elif "最近" in t: self.current_collection="HISTORY"; self.lbl_title.setText("最近播放")
        else: self.current_collection=t.replace("📁  ",""); self.lbl_title.setText(self.current_collection)
        self.load_list()

    def load_list(self):
        self.playlist = []; self.table.setRowCount(0)
        ext = ('.mp3','.wav','.m4a','.flac','.mp4')
        ds = []
        if self.current_collection=="HISTORY":
            for s in self.history:
                if os.path.exists(s["path"]): self.add_song_row(s)
            return
        
        if self.current_collection: ds=[os.path.join(self.music_folder, self.current_collection)]
        else:
            ds=[self.music_folder]
            for c in self.collections: ds.append(os.path.join(self.music_folder,c))
        
        for d in ds:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.lower().endswith(ext):
                        fp = os.path.abspath(os.path.join(d,f))
                        meta = self.metadata.get(f, {})
                        s = {"path":fp, "name":f, "artist":meta.get("a","未知"), "album":meta.get("b","未知")}
                        self.add_song_row(s)
        self._all_songs = self.playlist.copy()

    def add_song_row(self, s):
        self.playlist.append(s)
        r = self.table.rowCount(); self.table.insertRow(r)
        self.table.setItem(r,0,QTableWidgetItem(os.path.splitext(s["name"])[0]))
        self.table.setItem(r,1,QTableWidgetItem(s["artist"]))
        self.table.setItem(r,2,QTableWidgetItem(s["album"]))
        self.table.setItem(r,3,QTableWidgetItem("-"))

    def dl_bili(self):
        if not self.music_folder: return QMessageBox.warning(self,"提示","请先设置目录")
        u,ok = QInputDialog.getText(self,"下载","链接:")
        if ok and u:
            p=1
            m=re.search(r'[?&]p=(\d+)', u)
            if m: p=int(m.group(1))
            d = DownloadDialog(self, p, self.collections)
            if d.exec_()==QDialog.Accepted:
                mode,f,a,b = d.get_data()
                path = os.path.join(self.music_folder, f) if f else self.music_folder
                self.tmp_meta = (a,b)
                self.lbl_title.setText("⏳ 下载中...")
                self.dl = BilibiliDownloader(u, path, mode, p)
                self.dl.progress_signal.connect(lambda s: self.lbl_title.setText(s))
                self.dl.finished_signal.connect(self.on_dl_ok)
                self.dl.start()

    def on_dl_ok(self, p):
        # 自动写元数据
        a,b = self.tmp_meta
        if a or b:
            for f in os.listdir(p):
                if f not in self.metadata: self.metadata[f] = {"a":a or "未知", "b":b or "未知"}
            self.save_meta()
        self.full_scan(); self.lbl_title.setText("下载完成")

    def show_menu(self, pos):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return
        m = QMenu()
        
        mv = m.addMenu("📂 批量移动到...")
        mv.addAction("💿 根目录", lambda: self.do_move(rows, ""))
        for c in self.collections: mv.addAction(f"📁 {c}", lambda _,t=c: self.do_move(rows, t))
        
        m.addAction("🔠 批量重命名", self.do_rename_batch)
        m.addAction("✏️ 批量改信息", lambda: self.do_edit_info(rows))
        m.addSeparator()
        if len(rows)==1:
            idx = rows[0]
            m.addAction("🔐 绑定歌词 (整理)", lambda: self.do_bind(idx))
            m.addAction("🔍 手动搜歌词", lambda: self.do_search_lrc(idx))
            m.addAction("❌ 解绑歌词", lambda: self.do_del_lrc(idx))
        m.addAction("🗑️ 删除", lambda: self.do_del(rows))
        m.exec_(self.table.mapToGlobal(pos))

    def do_move(self, rows, target):
        self.player.setMedia(QMediaContent())
        tp = os.path.join(self.music_folder, target) if target else self.music_folder
        if not os.path.exists(tp): os.makedirs(tp)
        
        # 核心修复：一次性收集路径，防止索引变化
        targets = [self.playlist[i] for i in rows]
        cnt=0
        for s in targets:
            try:
                src = s["path"]; dst = os.path.join(tp, s["name"])
                if src!=dst:
                    shutil.move(src, dst)
                    l = os.path.splitext(src)[0]+".lrc"
                    if os.path.exists(l): shutil.move(l, os.path.join(tp, os.path.basename(l)))
                    cnt+=1
            except: pass
        self.full_scan(); QMessageBox.information(self,"完成",f"移动{cnt}首")

    def do_rename_batch(self):
        if not self.playlist: return
        self.player.setMedia(QMediaContent())
        d = BatchRenameDialog(self.playlist, self)
        if d.exec_()==QDialog.Accepted:
            mode, p, idxs = d.get_data()
            ts = [self.playlist[i] for i in idxs if i<len(self.playlist)]
            for s in ts:
                old=s["path"]; base,ext=os.path.splitext(s["name"]); nb=base
                if mode=="replace" and p[0] in base: nb=base.replace(p[0],p[1])
                elif mode=="trim":
                    if p[0]>0: nb=nb[p[0]:]
                    if p[1]>0: nb=nb[:-p[1]]
                nn=nb.strip()+ext; np=os.path.join(os.path.dirname(old),nn)
                if np!=old:
                    try: 
                        os.rename(old,np)
                        l=os.path.splitext(old)[0]+".lrc"
                        if os.path.exists(l): os.rename(l, os.path.splitext(np)[0]+".lrc")
                    except:pass
            self.full_scan()

    def do_bind(self, idx):
        self.player.setMedia(QMediaContent())
        s = self.playlist[idx]; old=s["path"]
        f,_ = QFileDialog.getOpenFileName(self,"LRC","","*.lrc")
        if f:
            d = os.path.join(os.path.dirname(old), os.path.splitext(s["name"])[0])
            os.makedirs(d, exist_ok=True)
            try:
                shutil.move(old, os.path.join(d, s["name"]))
                shutil.copy(f, os.path.join(d, os.path.splitext(s["name"])[0]+".lrc"))
                self.full_scan()
            except:pass

    def do_search_lrc(self, idx):
        s = self.playlist[idx]
        dur = self.player.duration() if self.current_index==idx else 0
        d = LyricSearchDialog(os.path.splitext(s["name"])[0], dur, self)
        if d.exec_()==QDialog.Accepted and d.result_id:
            lp = os.path.splitext(s["path"])[0]+".lrc"
            self.ld = LyricDownloader(d.result_id, lp)
            self.ld.finished_signal.connect(lambda c: self.on_lrc_ok(c,idx))
            self.ld.start()
    def on_lrc_ok(self, c, i):
        if self.current_index==i: self.parse_lrc(c)
        QMessageBox.information(self,"OK","绑定成功")

    def do_del_lrc(self, idx):
        p = os.path.splitext(self.playlist[idx]["path"])[0]+".lrc"
        if os.path.exists(p): os.remove(p); QMessageBox.information(self,"OK","已删除")
        if self.current_index==idx: self.parse_lrc("")

    def do_del(self, rows):
        if QMessageBox.Yes!=QMessageBox.question(self,"确","删?"): return
        self.player.setMedia(QMediaContent())
        for i in rows:
            if i<len(self.playlist):
                try:
                    p=self.playlist[i]["path"]
                    os.remove(p)
                    l=os.path.splitext(p)[0]+".lrc"
                    if os.path.exists(l): os.remove(l)
                except:pass
        self.full_scan()

    def do_edit_info(self, rows):
        d = BatchInfoDialog(self)
        if d.exec_()==QDialog.Accepted:
            a,b = d.get_data()
            for i in rows:
                if i<len(self.playlist):
                    n = self.playlist[i]["name"]
                    if n not in self.metadata: self.metadata[n]={}
                    if a: self.metadata[n]["a"]=a
                    if b: self.metadata[n]["b"]=b
            self.save_meta(); self.full_scan()

    # Play
    def play_sel(self, item): self.play(item.row())
    def play(self, idx):
        if not self.playlist or idx>=len(self.playlist): return
        self.current_index = idx
        s = self.playlist[idx]
        
        if s not in self.history: 
            self.history.insert(0,s)
            if len(self.history)>50: self.history.pop()
            self.save_hist()
            
        try:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(s["path"])))
            self.player.setPlaybackRate(self.rate); self.player.play()
            self.bp.setText("⏸")
            
            self.offset = self.saved_offsets.get(s["name"], 0.0)
            self.lo.setText(f"{self.offset}s")
            
            lp = os.path.splitext(s["path"])[0]+".lrc"
            if os.path.exists(lp):
                with open(lp,'r',encoding='utf-8',errors='ignore') as f: self.parse_lrc(f.read())
            else:
                self.lrc_p.clear(); self.lrc_p.addItem("搜索歌词...")
                self.sw = LyricListSearchWorker(s["name"])
                self.sw.search_finished.connect(self.auto_lrc)
                self.sw.start()
        except: pass
        
    def auto_lrc(self, res):
        if res and self.current_index>=0:
            # 智能权重：优先文件名完全匹配，或者时长接近
            best = res[0]
            lp = os.path.splitext(self.playlist[self.current_index]["path"])[0]+".lrc"
            self.ad = LyricDownloader(best['id'], lp)
            self.ad.finished_signal.connect(self.parse_lrc)
            self.ad.start()
        else: self.lrc_p.clear(); self.lrc_p.addItem("无歌词")

    def parse_lrc(self, txt):
        self.lyrics = []; self.lrc_p.clear()
        for l in txt.splitlines():
            m = re.match(r'\[(\d+):(\d+)\.(\d+)\](.*)', l)
            if m:
                t = int(m.group(1))*60 + int(m.group(2)) + int(m.group(3))/100
                tx = m.group(4).strip()
                if tx: 
                    self.lyrics.append({"t":t, "txt":tx})
                    self.lrc_p.addItem(tx)

    # Ctrl
    def ao(self, v):
        self.offset+=v; self.lo.setText(f"{self.offset}s")
        if self.current_index>=0: 
            self.saved_offsets[self.playlist[self.current_index]["name"]]=self.offset
            self.save_off()
    def tp(self): 
        if self.player.state()==QMediaPlayer.PlayingState: self.player.pause()
        else: self.player.play()
    def tm(self): self.mode=(self.mode+1)%3; self.bm.setText(["🔁","🔂","🔀"][self.mode])
    def tr(self):
        rs=[1.0,1.25,1.5,2.0,0.5]; i=rs.index(self.rate) if self.rate in rs else 0
        self.rate=rs[(i+1)%5]; self.player.setPlaybackRate(self.rate); self.br.setText(f"{self.rate}x")
    def pn(self):
        if not self.playlist: return
        n = random.randint(0,len(self.playlist)-1) if self.mode==2 else (self.current_index+1)%len(self.playlist)
        self.play(n)
    def pp(self):
        if not self.playlist: return
        p = random.randint(0,len(self.playlist)-1) if self.mode==2 else (self.current_index-1)%len(self.playlist)
        self.play(p)
    
    # Events
    def on_position_changed(self, p):
        if not self.is_slider_pressed: self.sl.setValue(p)
        self.lc.setText(ms_to_str(p))
        t = p/1000 + self.offset
        if self.lyrics:
            idx = -1
            for i, l in enumerate(self.lyrics):
                if t >= l["t"]: idx = i
                else: break
            if idx != -1:
                self.lrc_p.setCurrentRow(idx)
                self.lrc_p.scrollToItem(self.lrc_p.item(idx), QAbstractItemView.PositionAtCenter)
                pr = self.lyrics[idx-1]["txt"] if idx>0 else ""
                cu = self.lyrics[idx]["txt"]
                ne = self.lyrics[idx+1]["txt"] if idx<len(self.lyrics)-1 else ""
                self.desktop_lyric.set_lyrics(pr, cu, ne)
    def on_state_changed(self, s): self.bp.setText("⏸" if s==QMediaPlayer.PlayingState else "▶")
    def on_media_status_changed(self, s):
        if s==QMediaPlayer.EndOfMedia:
            if self.mode==1: self.player.play()
            else: self.pn()
    def handle_player_error(self): QTimer.singleShot(1000, self.pn)
    def on_duration_changed(self, d): 
        self.sl.setRange(0, d); self.lt.setText(ms_to_str(d))
        if self.current_index>=0: 
            self.table.setItem(self.current_index, 3, QTableWidgetItem(ms_to_str(d)))
            self.playlist[self.current_index]["duration"] = ms_to_str(d)
    
    def sp(self): self.is_slider_pressed=True
    def sr(self): self.is_slider_pressed=False; self.player.setPosition(self.sl.value())
    def sm(self, v): 
        if self.is_slider_pressed: self.lc.setText(ms_to_str(v))

    def new_coll(self): self.create_collection()
    def sel_folder(self): self.select_folder()
    def tog_lyric(self): 
        if self.desktop_lyric.isVisible(): self.desktop_lyric.hide()
        else: self.desktop_lyric.show()

    # Config
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try: 
                with open(CONFIG_FILE,'r') as f: 
                    d=json.load(f); self.music_folder=d.get("folder","")
                    if self.music_folder: self.full_scan()
            except:pass
        if os.path.exists(METADATA_FILE): 
            try: 
                with open(METADATA_FILE,'r') as f: self.metadata=json.load(f)
            except:pass
        if os.path.exists(OFFSET_FILE):
            try: 
                with open(OFFSET_FILE,'r') as f: self.saved_offsets=json.load(f)
            except:pass
        if os.path.exists(HISTORY_FILE):
            try: 
                with open(HISTORY_FILE,'r') as f: self.history=json.load(f)
            except:pass

    def save_config(self): 
        with open(CONFIG_FILE,'w') as f: json.dump({"folder":self.music_folder},f)
    def save_meta(self): 
        with open(METADATA_FILE,'w') as f: json.dump(self.metadata,f)
    def save_off(self): 
        with open(OFFSET_FILE,'w') as f: json.dump(self.saved_offsets,f)
    def save_hist(self): 
        with open(HISTORY_FILE,'w') as f: json.dump(self.history,f)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(app_path, 'PyQt5', 'Qt', 'plugins')
        QCoreApplication.addLibraryPath(os.path.join(app_path, 'PyQt5', 'Qt', 'plugins'))
    app = QApplication(sys.argv)
    f = QFont("Microsoft YaHei", 10); app.setFont(f)
    w = SodaPlayer(); w.show(); sys.exit(app.exec_())

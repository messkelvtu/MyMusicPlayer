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
from datetime import datetime
from ctypes import windll, c_int, byref, sizeof, Structure, POINTER

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QFileDialog, QFrame, QAbstractItemView, QCheckBox,
                             QGraphicsDropShadowEffect, QInputDialog, QMessageBox, 
                             QFontDialog, QMenu, QAction, QSlider, QDialog, QRadioButton, 
                             QComboBox, QLineEdit, QTabWidget, QSpinBox, QColorDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget, QScrollArea, QSizePolicy)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize, QCoreApplication, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QFont, QColor, QPalette, QLinearGradient, QPainter, QIcon, QPixmap, QCursor, QBrush
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

# --- Windows Acrylic (毛玻璃) ---
class ACCENT_POLICY(Structure):
    _fields_ = [("AccentState", c_int), ("AccentFlags", c_int), ("GradientColor", c_int), ("AnimationId", c_int)]

class WINDOWCOMPOSITIONATTRIBDATA(Structure):
    _fields_ = [("Attribute", c_int), ("Data", POINTER(ACCENT_POLICY)), ("SizeOfData", c_int)]

def enable_acrylic(hwnd):
    try:
        policy = ACCENT_POLICY()
        policy.AccentState = 4  # ENABLE_ACRYLICBLURBEHIND
        policy.GradientColor = 0xCCF2F2F2  # AABBGGRR (White with transparency)
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = POINTER(ACCENT_POLICY)(policy)
        data.SizeOfData = sizeof(policy)
        windll.user32.SetWindowCompositionAttribute(int(hwnd), byref(data))
    except: pass

# --- 现代化 UI 样式表 ---
STYLESHEET = """
QMainWindow { background: transparent; }
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; color: #1c1c1e; }

/* 侧边栏 */
QFrame#Sidebar {
    background-color: rgba(245, 245, 247, 0.9);
    border-right: 1px solid rgba(0, 0, 0, 0.05);
}

QLabel#Logo {
    font-size: 22px; font-weight: 900; color: #1ECD97;
    padding: 30px 20px; letter-spacing: 1px;
}

QLabel#SectionTitle {
    font-size: 12px; color: #8e8e93; font-weight: bold;
    padding: 15px 25px 5px 25px;
}

/* 导航按钮 */
QPushButton.NavBtn {
    background: transparent; border: none; text-align: left;
    padding: 10px 25px; font-size: 14px; color: #333; border-radius: 8px; margin: 2px 12px;
}
QPushButton.NavBtn:hover { background-color: rgba(0,0,0,0.05); }
QPushButton.NavBtn:checked { background-color: #e6f7ff; color: #1ECD97; font-weight: bold; }

QPushButton#DownloadBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF6699, stop:1 #ff85b3);
    color: white; font-weight: bold; border-radius: 18px; text-align: center;
    margin: 10px 20px; padding: 8px;
}
QPushButton#DownloadBtn:hover { margin-top: 11px; }

/* 主列表区域 */
QTableWidget {
    background-color: rgba(255, 255, 255, 0.6);
    border: none; outline: none;
    selection-background-color: rgba(30, 205, 151, 0.15);
    selection-color: #1ECD97;
    alternate-background-color: rgba(250, 250, 250, 0.5);
}
QHeaderView::section {
    background-color: transparent; border: none; border-bottom: 1px solid #eee;
    padding: 8px; font-weight: bold; color: #888;
}

/* 歌词页 */
QWidget#LyricsPage {
    background-color: #ffffff; 
}
QListWidget#BigLyric {
    background: transparent; border: none; outline: none;
    font-size: 18px; color: #555; font-weight: 500;
}
QListWidget#BigLyric::item { padding: 15px; text-align: center; }
QListWidget#BigLyric::item:selected { color: #1ECD97; font-size: 24px; font-weight: bold; }

/* 底部播放条 */
QFrame#PlayerBar {
    background-color: rgba(255, 255, 255, 0.95);
    border-top: 1px solid rgba(0, 0, 0, 0.05);
}

/* 播放控制 */
QPushButton#PlayBtn { 
    background-color: #1ECD97; color: white; border-radius: 24px; 
    font-size: 20px; min-width: 48px; min-height: 48px; border:none;
}
QPushButton#PlayBtn:hover { background-color: #1ebc8a; transform: scale(1.05); }

QPushButton.CtrlBtn { background: transparent; border: none; font-size: 20px; color: #444; }
QPushButton.CtrlBtn:hover { color: #1ECD97; }

/* 进度条 */
QSlider::groove:horizontal { height: 4px; background: #e5e5e5; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #fff; border: 1px solid #ccc; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}
QSlider::sub-page:horizontal { background: #1ECD97; border-radius: 2px; }

/* 专辑封面占位 */
QLabel#AlbumArt {
    background-color: #eee; border-radius: 8px; border: 1px solid #ddd;
}
"""

# --- 辅助函数 ---
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def ms_to_str(ms):
    s = ms // 1000
    return f"{s//60:02}:{s%60:02}"

# --- 功能类 (搜索、下载等保持逻辑不变) ---
class LyricListSearchWorker(QThread):
    search_finished = pyqtSignal(list)
    def __init__(self, keyword):
        super().__init__(); self.keyword = keyword
    def run(self):
        try:
            url = "http://music.163.com/api/search/get/web?csrf_token="
            headers = {'User-Agent': 'Mozilla/5.0'}
            data = urllib.parse.urlencode({'s': self.keyword, 'type': 1, 'offset': 0, 'total': 'true', 'limit': 15}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req) as f: res = json.loads(f.read().decode('utf-8'))
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
        super().__init__(parent); self.setWindowTitle("搜索歌词"); self.resize(600, 400); self.result_id = None; self.duration_ms = duration_ms
        l = QVBoxLayout(self); h = QHBoxLayout(); self.ik = QLineEdit(song_name); b = QPushButton("搜索"); b.clicked.connect(self.ss); h.addWidget(self.ik); h.addWidget(b); l.addLayout(h)
        self.tb = QTableWidget(); self.tb.setColumnCount(4); self.tb.setHorizontalHeaderLabels(["歌名","歌手","时长","ID"]); self.tb.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.tb.setSelectionBehavior(QAbstractItemView.SelectRows); self.tb.itemDoubleClicked.connect(self.os); l.addWidget(self.tb)
        self.sl = QLabel("输入关键词..."); l.addWidget(self.sl)
    def ss(self):
        k = self.ik.text(); self.tb.setRowCount(0); self.sl.setText("搜索中...")
        self.w = LyricListSearchWorker(k); self.w.search_finished.connect(self.sd); self.w.start()
    def sd(self, res):
        self.sl.setText(f"找到 {len(res)} 条"); self.tb.setRowCount(len(res))
        for i, r in enumerate(res):
            self.tb.setItem(i,0,QTableWidgetItem(r['name'])); self.tb.setItem(i,1,QTableWidgetItem(r['artist']))
            ti = QTableWidgetItem(r['duration_str'])
            if abs(r['duration']-self.duration_ms)<3000 and self.duration_ms>0: ti.setForeground(QColor("#1ECD97"))
            self.tb.setItem(i,2,ti); self.tb.setItem(i,3,QTableWidgetItem(str(r['id'])))
    def os(self, it): self.result_id = self.tb.item(it.row(),3).text(); self.accept()

class LyricDownloader(QThread):
    finished_signal = pyqtSignal(str)
    def __init__(self, sid, path): super().__init__(); self.sid=sid; self.path=path
    def run(self):
        try:
            url = f"http://music.163.com/api/song/lyric?os=pc&id={self.sid}&lv=-1&kv=-1&tv=-1"
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req) as f: res = json.loads(f.read().decode('utf-8'))
            if 'lrc' in res:
                lrc = res['lrc']['lyric']
                with open(self.path,'w',encoding='utf-8') as f: f.write(lrc)
                self.finished_signal.emit(lrc)
        except:pass

class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str); finished_signal = pyqtSignal(str,str); error_signal = pyqtSignal(str)
    def __init__(self, url, path, mode, sp): super().__init__(); self.u=url; self.p=path; self.m=mode; self.sp=sp
    def run(self):
        if not yt_dlp: return self.error_signal.emit("无yt-dlp")
        if not os.path.exists(self.p): 
            try: os.makedirs(self.p)
            except: return self.error_signal.emit("无法建目录")
        def ph(d):
            if d['status']=='downloading': self.progress_signal.emit(f"⬇️ {d.get('_percent_str','')} {os.path.basename(d.get('filename',''))[:20]}...")
        opts = {'format':'bestaudio[ext=m4a]/best[ext=mp4]', 'outtmpl':os.path.join(self.p,'%(title)s.%(ext)s'), 'overwrites':True,
                'noplaylist':self.m=='single', 'playlist_items':str(self.sp) if self.m=='single' else f"{self.sp}-",
                'progress_hooks':[ph], 'quiet':True, 'nocheckcertificate':True, 'restrictfilenames':False}
        try:
            with yt_dlp.YoutubeDL(opts) as y: y.download([self.u])
            self.finished_signal.emit(self.p, "")
        except Exception as e: self.error_signal.emit(str(e))

class DownloadDialog(QDialog):
    def __init__(self, parent=None, current_p=1, collections=[]):
        super().__init__(parent); self.setWindowTitle("下载"); self.resize(400,250)
        l=QVBoxLayout(self); l.addWidget(QLabel(f"当前 P{current_p}，选择模式："))
        self.rb_s=QRadioButton(f"单曲 (P{current_p})"); self.rb_l=QRadioButton(f"合集 (P{current_p}-End)"); self.rb_s.setChecked(True)
        l.addWidget(self.rb_s); l.addWidget(self.rb_l); l.addSpacing(10)
        l.addWidget(QLabel("存入：")); self.cb=QComboBox(); self.cb.addItem("根目录","")
        for c in collections: self.cb.addItem(f"📁 {c}",c)
        self.cb.addItem("➕ 新建...","NEW"); l.addWidget(self.cb)
        self.inew=QLineEdit(); self.inew.setPlaceholderText("名称"); self.inew.hide(); l.addWidget(self.inew)
        self.cb.currentIndexChanged.connect(lambda: self.inew.setVisible(self.cb.currentData()=="NEW"))
        l.addSpacing(10); l.addWidget(QLabel("预设信息:")); self.ia=QLineEdit(); self.ia.setPlaceholderText("歌手"); l.addWidget(self.ia)
        self.ib=QLineEdit(); self.ib.setPlaceholderText("专辑"); l.addWidget(self.ib)
        b=QPushButton("下载"); b.clicked.connect(self.accept); l.addWidget(b)
    def get_data(self):
        m="playlist" if self.rb_l.isChecked() else "single"; f=self.cb.currentData()
        if f=="NEW": f=self.inew.text().strip()
        return m,f,self.ia.text(),self.ib.text()

class BatchRenameDialog(QDialog):
    def __init__(self, pl, parent=None):
        super().__init__(parent); self.resize(500,600); self.pl=pl; self.si=[]
        l=QVBoxLayout(self); self.tab=QTabWidget()
        t1=QWidget(); l1=QVBoxLayout(t1); self.ifind=QLineEdit(); self.irep=QLineEdit()
        l1.addWidget(QLabel("查:")); l1.addWidget(self.ifind); l1.addWidget(QLabel("替:")); l1.addWidget(self.irep); l1.addStretch(); self.tab.addTab(t1,"替换")
        t2=QWidget(); l2=QVBoxLayout(t2); self.sh=QSpinBox(); self.st=QSpinBox()
        l2.addWidget(QLabel("删前:")); l2.addWidget(self.sh); l2.addWidget(QLabel("删后:")); l2.addWidget(self.st); l2.addStretch(); self.tab.addTab(t2,"裁剪")
        l.addWidget(self.tab)
        self.lst=QListWidget()
        for s in pl: i=QListWidgetItem(s["name"]); i.setFlags(i.flags()|Qt.ItemIsUserCheckable); i.setCheckState(Qt.Checked); self.lst.addItem(i)
        l.addWidget(self.lst)
        b=QPushButton("执行"); b.clicked.connect(self.ok); l.addWidget(b)
    def ok(self):
        self.si=[i for i in range(self.lst.count()) if self.lst.item(i).checkState()==Qt.Checked]
        self.accept()
    def get_data(self):
        if self.tab.currentIndex()==0: return "rep", (self.ifind.text(),self.irep.text()), self.si
        else: return "trim", (self.sh.value(),self.st.value()), self.si

class DesktopLyricWindow(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool); self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1200,180); l=QVBoxLayout(self); self.col=QColor(255,255,255); self.font=QFont("Microsoft YaHei",36,QFont.Bold)
        self.lbs=[QLabel("") for _ in range(3)]; [l.addWidget(lb) for lb in self.lbs]; [lb.setAlignment(Qt.AlignCenter) for lb in self.lbs]
        self.upd(); self.move(100,800)
    def upd(self):
        sh=QColor(0,0,0,200); s=self.font.pointSize()
        for i,lb in enumerate(self.lbs):
            ef=QGraphicsDropShadowEffect(); ef.setBlurRadius(8); ef.setColor(sh); ef.setOffset(1,1); lb.setGraphicsEffect(ef)
            f=QFont(self.font); f.setPointSize(s if i==1 else int(s*0.6))
            c=self.col.name() if i==1 else f"rgba({self.col.red()},{self.col.green()},{self.col.blue()},160)"
            lb.setStyleSheet(f"color:{c}"); lb.setFont(f)
    def set_text(self, p, c, n): self.lbs[0].setText(p); self.lbs[1].setText(c); self.lbs[2].setText(n)
    def mousePressEvent(self, e): 
        if e.button()==Qt.LeftButton: self.dp=e.globalPos()-self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e): 
        if e.buttons()==Qt.LeftButton: self.move(e.globalPos()-self.dp)

# --- 核心主程序 ---
class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 2025")
        self.resize(1200, 800)
        self.setStyleSheet(STYLESHEET)
        
        # Windows 毛玻璃效果
        self.setAttribute(Qt.WA_TranslucentBackground)
        if os.name == 'nt':
            try: enable_acrylic(int(self.winId()))
            except: pass

        # 数据
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
        self.mode = 0; self.rate = 1.0; self.volume = 80; self.is_slider_pressed = False

        # 播放器
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.on_pos_changed)
        self.player.durationChanged.connect(self.on_dur_changed)
        self.player.stateChanged.connect(self.on_state_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.error.connect(lambda: QTimer.singleShot(1000, self.play_next))
        self.player.setVolume(self.volume)

        self.desktop_lyric = DesktopLyricWindow()
        
        self.init_ui()
        self.load_conf()

    def init_ui(self):
        # 使用 QStackedWidget 实现页面切换
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0,0,0,0); self.main_layout.setSpacing(0)

        # === 左侧侧边栏 ===
        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(260)
        sl = QVBoxLayout(sidebar); sl.setContentsMargins(0,0,0,0); sl.setSpacing(5)
        
        sl.addWidget(QLabel("🎵 汽水音乐", objectName="Logo"))
        
        # 功能区
        btn_box = QWidget(); bl = QVBoxLayout(btn_box); bl.setSpacing(8)
        b_dl = QPushButton("☁️ B站下载"); b_dl.setObjectName("DownloadBtn"); b_dl.clicked.connect(self.dl_bili)
        b_rf = QPushButton("🔄 刷新库"); b_rf.setProperty("NavBtn",True); b_rf.clicked.connect(self.full_scan)
        bl.addWidget(b_dl); bl.addWidget(b_rf); sl.addWidget(btn_box)
        
        sl.addWidget(QLabel("音乐库", objectName="SectionTitle"))
        self.nav = QListWidget(); self.nav.setStyleSheet("background:transparent; border:none; font-size:14px;")
        self.nav.itemClicked.connect(self.switch_coll)
        sl.addWidget(self.nav)
        
        sl.addStretch()
        b_fo = QPushButton("📁 根目录"); b_fo.setProperty("NavBtn",True); b_fo.clicked.connect(self.sel_folder)
        b_mv = QPushButton("🚚 批量移动"); b_mv.setProperty("NavBtn",True); b_mv.clicked.connect(self.batch_move_dialog)
        b_dl = QPushButton("🎤 桌面歌词"); b_dl.setProperty("NavBtn",True); b_dl.clicked.connect(self.tog_desk_lrc)
        sl.addWidget(b_mv); sl.addWidget(b_fo); sl.addWidget(b_dl)
        
        self.main_layout.addWidget(sidebar)

        # === 右侧内容区 (包含 StackedWidget) ===
        right_panel = QWidget()
        r_layout = QVBoxLayout(right_panel); r_layout.setContentsMargins(0,0,0,0); r_layout.setSpacing(0)
        
        self.stack = QStackedWidget()
        
        # -- 页面 0: 列表页 --
        page_list = QWidget(); pl_layout = QVBoxLayout(page_list); pl_layout.setContentsMargins(0,0,0,0)
        
        # 顶部栏 (搜索 + 标题)
        top_bar = QFrame(); top_bar.setFixedHeight(70); top_bar.setStyleSheet("background:rgba(255,255,255,0.5); border-bottom:1px solid #eee;")
        tl = QHBoxLayout(top_bar); tl.setContentsMargins(25,0,25,0)
        self.lbl_coll = QLabel("全部音乐"); self.lbl_coll.setStyleSheet("font-size:20px; font-weight:bold;")
        self.search_box = QLineEdit(); self.search_box.setPlaceholderText("🔍 搜索本地歌曲..."); self.search_box.setFixedWidth(250)
        self.search_box.setStyleSheet("border-radius:15px; padding:5px 15px; border:1px solid #ddd;")
        self.search_box.textChanged.connect(self.filter_list)
        tl.addWidget(self.lbl_coll); tl.addStretch(); tl.addWidget(self.search_box)
        pl_layout.addWidget(top_bar)
        
        # 歌曲表格
        self.table = QTableWidget(); self.table.setColumnCount(4); self.table.setHorizontalHeaderLabels(["标题","歌手","专辑","时长"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False); self.table.setShowGrid(False); self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.itemDoubleClicked.connect(self.play_item); self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_menu)
        pl_layout.addWidget(self.table)
        
        self.stack.addWidget(page_list)
        
        # -- 页面 1: 歌词详情页 (附件3风格) --
        page_lrc = QWidget(); page_lrc.setObjectName("LyricsPage")
        lrc_layout = QHBoxLayout(page_lrc); lrc_layout.setContentsMargins(50,50,50,50)
        
        # 左侧：大封面
        left_box = QVBoxLayout(); left_box.setAlignment(Qt.AlignCenter)
        self.art_cover = QLabel(); self.art_cover.setFixedSize(350,350)
        self.art_cover.setStyleSheet("background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #a18cd1, stop:1 #fbc2eb); border-radius: 20px;")
        self.art_title = QLabel("暂无播放"); self.art_title.setStyleSheet("font-size:24px; font-weight:bold; margin-top:20px;")
        self.art_artist = QLabel("--"); self.art_artist.setStyleSheet("font-size:16px; color:#666;")
        btn_back = QPushButton("﹀ 收起"); btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet("border:none; color:#888; font-size:14px; margin-top:30px;")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        
        left_box.addWidget(self.art_cover); left_box.addWidget(self.art_title); left_box.addWidget(self.art_artist)
        left_box.addWidget(btn_back); lrc_layout.addLayout(left_box)
        
        # 右侧：滚动大歌词
        self.big_lrc = QListWidget(); self.big_lrc.setObjectName("BigLyric")
        self.big_lrc.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.big_lrc.setFocusPolicy(Qt.NoFocus)
        lrc_layout.addWidget(self.big_lrc, stretch=1)
        
        self.stack.addWidget(page_lrc)
        r_layout.addWidget(self.stack)

        # === 底部播放栏 (悬浮风格) ===
        bar = QFrame(); bar.setObjectName("PlayerBar"); bar.setFixedHeight(90)
        bl = QHBoxLayout(bar); bl.setContentsMargins(20,10,20,10)
        
        # 左侧：迷你封面+信息 (点击进入歌词页)
        info_w = QWidget(); info_l = QHBoxLayout(info_w); info_l.setContentsMargins(0,0,0,0)
        self.mini_art = QPushButton(); self.mini_art.setFixedSize(50,50); self.mini_art.setStyleSheet("background:#ccc; border-radius:8px; border:none;")
        self.mini_art.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        text_w = QWidget(); text_l = QVBoxLayout(text_w); text_l.setSpacing(2); text_l.setContentsMargins(0,0,0,0)
        self.bar_title = QLabel("未播放"); self.bar_title.setStyleSheet("font-weight:bold; font-size:14px;")
        self.bar_artist = QLabel("--"); self.bar_artist.setStyleSheet("color:#666; font-size:12px;")
        text_l.addWidget(self.bar_title); text_l.addWidget(self.bar_artist)
        info_l.addWidget(self.mini_art); info_l.addWidget(text_w)
        bl.addWidget(info_w, stretch=2)
        
        # 中间：控制+进度
        center_w = QWidget(); center_l = QVBoxLayout(center_w)
        btns = QHBoxLayout(); btns.setSpacing(15); btns.setAlignment(Qt.AlignCenter)
        self.b_mode = QPushButton("🔁"); self.b_mode.setProperty("CtrlBtn",True); self.b_mode.clicked.connect(self.tog_mode)
        b_pv = QPushButton("⏮"); b_pv.setProperty("CtrlBtn",True); b_pv.clicked.connect(self.play_prev)
        self.b_pp = QPushButton("▶"); self.b_pp.setObjectName("PlayBtn"); self.b_pp.clicked.connect(self.tog_play)
        b_nx = QPushButton("⏭"); b_nx.setProperty("CtrlBtn",True); b_nx.clicked.connect(self.play_next)
        self.b_rate = QPushButton("1.0x"); self.b_rate.setProperty("CtrlBtn",True); self.b_rate.clicked.connect(self.tog_rate)
        btns.addWidget(self.b_mode); btns.addWidget(b_pv); btns.addWidget(self.b_pp); btns.addWidget(b_nx); btns.addWidget(self.b_rate)
        
        prog = QHBoxLayout()
        self.l_cur = QLabel("00:00"); self.l_tot = QLabel("00:00")
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(0,0)
        self.slider.sliderPressed.connect(self.sp); self.slider.sliderReleased.connect(self.sr); self.slider.valueChanged.connect(self.sm)
        prog.addWidget(self.l_cur); prog.addWidget(self.slider); prog.addWidget(self.l_tot)
        
        center_l.addLayout(btns); center_l.addLayout(prog)
        bl.addWidget(center_w, stretch=4)
        
        # 右侧：音量+微调
        right_w = QWidget(); right_l = QHBoxLayout(right_w); right_l.setAlignment(Qt.AlignRight)
        self.vol_s = QSlider(Qt.Horizontal); self.vol_s.setRange(0,100); self.vol_s.setValue(80); self.vol_s.setFixedWidth(80)
        self.vol_s.valueChanged.connect(lambda v: self.player.setVolume(v))
        
        b_off = QPushButton("词微调"); b_off.setProperty("OffsetBtn",True)
        b_off.clicked.connect(self.adjust_offset_dialog)
        
        right_l.addWidget(QLabel("🔈")); right_l.addWidget(self.vol_s); right_l.addWidget(b_off)
        bl.addWidget(right_w, stretch=2)

        r_layout.addWidget(bar)
        self.main_layout.addWidget(right_panel)

    # --- 逻辑处理 ---
    def full_scan(self):
        if not self.music_folder: return
        self.collections = []
        ext = ('.mp3','.wav','.m4a','.flac','.mp4')
        for d in os.listdir(self.music_folder):
            fd = os.path.join(self.music_folder, d)
            if os.path.isdir(fd):
                fs = [f for f in os.listdir(fd) if f.lower().endswith(ext)]
                if len(fs) > 1: self.collections.append(d)
        
        self.nav.clear(); self.nav.addItem("💿  全部歌曲"); self.nav.addItem("🕒  最近播放")
        for c in self.collections: self.nav.addItem(f"📁  {c}")
        self.load_list()

    def load_list(self):
        self.playlist = []; self.table.setRowCount(0)
        ext = ('.mp3','.wav','.m4a','.flac','.mp4')
        ds = []
        if self.current_collection=="HISTORY":
            for s in self.history: self.add_row(s)
            return
        
        if self.current_collection: ds = [os.path.join(self.music_folder, self.current_collection)]
        else:
            ds = [self.music_folder] + [os.path.join(self.music_folder, c) for c in self.collections]
            
        for d in ds:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.lower().endswith(ext):
                        fp = os.path.abspath(os.path.join(d,f))
                        meta = self.metadata.get(f, {})
                        self.add_row({"path":fp, "name":f, "artist":meta.get("a","未知"), "album":meta.get("b","未知")})
        self._base_list = self.playlist.copy()

    def add_row(self, s):
        self.playlist.append(s)
        r = self.table.rowCount(); self.table.insertRow(r)
        self.table.setItem(r,0,QTableWidgetItem(os.path.splitext(s["name"])[0]))
        self.table.setItem(r,1,QTableWidgetItem(s["artist"]))
        self.table.setItem(r,2,QTableWidgetItem(s["album"]))
        self.table.setItem(r,3,QTableWidgetItem(s.get("dur","-")))

    def filter_list(self, txt):
        txt = txt.lower()
        for i in range(self.table.rowCount()):
            h = self.table.isRowHidden(i)
            m = False
            for c in range(3):
                if self.table.item(i,c) and txt in self.table.item(i,c).text().lower(): m=True
            self.table.setRowHidden(i, not m)

    def play_item(self, item): self.play(item.row())
    def play(self, idx):
        if not self.playlist: return
        self.current_index = idx
        s = self.playlist[idx]
        
        # 记录历史
        if s not in self.history: self.history.insert(0,s)
        if len(self.history)>100: self.history.pop()
        self.save_hist()

        # 播放
        try:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(s["path"])))
            self.player.setPlaybackRate(self.rate); self.player.play()
            self.b_pp.setText("⏸")
            
            # 更新UI
            nm = os.path.splitext(s["name"])[0]
            self.bar_title.setText(nm); self.bar_artist.setText(s["artist"])
            self.art_title.setText(nm); self.art_artist.setText(s["artist"])
            
            # 歌词
            self.offset = self.saved_offsets.get(s["name"], 0.0)
            lrc = os.path.splitext(s["path"])[0]+".lrc"
            if os.path.exists(lrc): 
                with open(lrc,'r',encoding='utf-8',errors='ignore') as f: self.parse_lrc(f.read())
            else:
                self.panel_lrc(["搜索中..."]); self.big_lrc.clear(); self.big_lrc.addItem("搜索中...")
                self.sw = LyricListSearchWorker(nm)
                self.sw.search_finished.connect(self.auto_lrc)
                self.sw.start()
        except: pass

    def auto_lrc(self, res):
        if res:
            lp = os.path.splitext(self.playlist[self.current_index]["path"])[0]+".lrc"
            self.ld = LyricDownloader(res[0]['id'], lp)
            self.ld.finished_signal.connect(self.parse_lrc)
            self.ld.start()
        else: self.panel_lrc(["无歌词"]); self.big_lrc.clear(); self.big_lrc.addItem("无歌词")

    def parse_lrc(self, txt):
        self.lyrics = []; self.big_lrc.clear()
        for l in txt.splitlines():
            m = re.match(r'\[(\d+):(\d+)\.(\d+)\](.*)', l)
            if m:
                t = int(m.group(1))*60 + int(m.group(2)) + int(m.group(3))/100
                tx = m.group(4).strip()
                if tx: 
                    self.lyrics.append({"t":t, "txt":tx})
                    self.big_lrc.addItem(tx)

    def on_pos_changed(self, p):
        if not self.is_slider_pressed: self.slider.setValue(p)
        self.l_cur.setText(ms_to_str(p))
        t = p/1000 + self.offset
        if self.lyrics:
            idx = -1
            for i, l in enumerate(self.lyrics):
                if t >= l["t"]: idx = i
                else: break
            if idx != -1:
                # 桌面歌词
                pr = self.lyrics[idx-1]["txt"] if idx>0 else ""
                cu = self.lyrics[idx]["txt"]
                ne = self.lyrics[idx+1]["txt"] if idx<len(self.lyrics)-1 else ""
                self.desktop_lyric.set_lyrics(pr, cu, ne)
                
                # 歌词页滚动
                self.big_lrc.setCurrentRow(idx)
                self.big_lrc.scrollToItem(self.big_lrc.item(idx), QAbstractItemView.PositionAtCenter)

    def show_menu(self, p):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return
        m = QMenu()
        
        # 批量移动
        mv = m.addMenu("📂 批量移动到")
        mv.addAction("根目录", lambda: self.do_move(rows, ""))
        for c in self.collections: mv.addAction(c, lambda _,t=c: self.do_move(rows, t))
        
        m.addAction("🔠 批量重命名", self.batch_rename_ui)
        m.addAction("✏️ 批量改信息", lambda: self.batch_info_ui(rows))
        m.addSeparator()
        if len(rows)==1:
            i = rows[0]
            m.addAction("🔐 绑定/整理歌词", lambda: self.bind_lrc(i))
            m.addAction("🔍 手动搜歌词", lambda: self.manual_lrc(i))
            m.addAction("❌ 解绑歌词", lambda: self.del_lrc(i))
        m.addAction("🗑️ 删除", lambda: self.do_del(rows))
        m.exec_(self.table.mapToGlobal(p))

    # --- 批量移动逻辑 ---
    def batch_move_dialog(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return QMessageBox.warning(self,"提示","请先选择歌曲")
        ls = ["根目录"] + self.collections
        t, ok = QInputDialog.getItem(self, "移动", "目标:", ls, 0, False)
        if ok: self.do_move(rows, "" if t=="根目录" else t)

    def do_move(self, rows, target):
        self.player.setMedia(QMediaContent()) # 释放
        tp = os.path.join(self.music_folder, target) if target else self.music_folder
        if not os.path.exists(tp): os.makedirs(tp)
        
        targets = [self.playlist[i] for i in rows]
        cnt = 0
        for s in targets:
            try:
                dst = os.path.join(tp, s["name"])
                if s["path"] != dst:
                    shutil.move(s["path"], dst)
                    l = os.path.splitext(s["path"])[0]+".lrc"
                    if os.path.exists(l): shutil.move(l, os.path.join(tp, os.path.basename(l)))
                    cnt+=1
            except: pass
        self.full_scan(); QMessageBox.information(self,"ok",f"移动 {cnt} 首")

    # --- 其他功能 ---
    def batch_rename_ui(self):
        if not self.playlist: return
        self.player.setMedia(QMediaContent())
        d = BatchRenameDialog(self.playlist, self)
        if d.exec_()==QDialog.Accepted:
            m, p, idxs = d.get_data()
            ts = [self.playlist[i] for i in idxs if i<len(self.playlist)]
            for s in ts:
                old=s["path"]; base,ext=os.path.splitext(s["name"]); nb=base
                if m=="replace" and p[0] in base: nb=base.replace(p[0],p[1])
                elif m=="trim":
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

    def bind_lrc(self, idx):
        self.player.setMedia(QMediaContent())
        s = self.playlist[idx]; p=s["path"]; n=os.path.splitext(s["name"])[0]
        f, _ = QFileDialog.getOpenFileName(self, "选歌词", "", "LRC (*.lrc)")
        if f:
            d = os.path.join(os.path.dirname(p), n)
            try:
                if not os.path.exists(d): os.makedirs(d)
                shutil.move(p, os.path.join(d, s["name"]))
                shutil.copy(f, os.path.join(d, n+".lrc"))
                self.full_scan(); QMessageBox.information(self,"ok","整理完成")
            except:pass

    def manual_lrc(self, idx):
        s = self.playlist[idx]; d=0 # 简化，不传时长了
        dlg = LyricSearchDialog(os.path.splitext(s["name"])[0], 0, self)
        if dlg.exec_()==QDialog.Accepted and dlg.result_id:
            lp = os.path.splitext(s["path"])[0]+".lrc"
            self.ld = LyricDownloader(dlg.result_id, lp)
            self.ld.finished_signal.connect(lambda c: self.parse_lrc(c))
            self.ld.start()

    def del_lrc(self, idx):
        p = os.path.splitext(self.playlist[idx]["path"])[0]+".lrc"
        if os.path.exists(p): os.remove(p); self.parse_lrc(""); QMessageBox.information(self,"ok","已删")

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

    def batch_info_ui(self, rows):
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

    def dl_bili(self):
        if not self.music_folder: return QMessageBox.warning(self,"","请先设置目录")
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
                self.lbl_collection_title.setText("⏳ 下载中...")
                self.dl = BilibiliDownloader(u, path, mode, p)
                self.dl.progress_signal.connect(lambda s: self.lbl_collection_title.setText(s))
                self.dl.finished_signal.connect(self.on_dl_ok)
                self.dl.start()
    def on_dl_ok(self, p):
        a,b = self.tmp_meta
        if a or b:
            for f in os.listdir(p):
                if f not in self.metadata: self.metadata[f]={"a":a or "未知", "b":b or "未知"}
            self.save_meta()
        self.full_scan(); self.lbl_collection_title.setText("下载完成")

    def new_coll(self):
        n, ok = QInputDialog.getText(self, "新建", "名称:")
        if ok and n: 
            os.makedirs(os.path.join(self.music_folder, sanitize_filename(n)), exist_ok=True)
            self.full_scan()

    def adjust_offset_dialog(self):
        i, ok = QInputDialog.getDouble(self, "微调", "偏移秒数(+延后/-提前):", self.offset, -10, 10, 1)
        if ok: 
            self.offset = i
            if self.current_index>=0: 
                self.saved_offsets[self.playlist[self.current_index]["name"]]=self.offset
                self.save_off()

    # 基础
    def switch_coll(self, item):
        t = item.text()
        if "全部" in t: self.current_collection=""
        elif "最近" in t: self.current_collection="HISTORY"
        else: self.current_collection=t.replace("📁  ","")
        self.load_list()

    def sel_folder(self):
        f=QFileDialog.getExistingDirectory(self,"选目录")
        if f: self.music_folder=f; self.full_scan(); self.save_config()

    def tog_lyric(self): 
        if self.desktop_lyric.isVisible(): self.desktop_lyric.hide()
        else: self.desktop_lyric.show()
    def tog_desk_lrc(self): self.tog_lyric()

    def sp(self): self.is_slider_pressed=True
    def sr(self): self.is_slider_pressed=False; self.player.setPosition(self.slider.value())
    def sm(self, v): 
        if self.is_slider_pressed: self.lbl_curr_time.setText(ms_to_str(v))
    def on_dur_changed(self, d): 
        self.slider.setRange(0, d); self.lbl_total_time.setText(ms_to_str(d))
        if self.current_index>=0:
            self.playlist[self.current_index]["dur"] = ms_to_str(d)
            self.table.setItem(self.current_index, 3, QTableWidgetItem(ms_to_str(d)))

    def play_next(self):
        if not self.playlist: return
        n = random.randint(0,len(self.playlist)-1) if self.mode==2 else (self.current_index+1)%len(self.playlist)
        self.play(n)
    def play_prev(self):
        if not self.playlist: return
        p = random.randint(0,len(self.playlist)-1) if self.mode==2 else (self.current_index-1)%len(self.playlist)
        self.play(p)
    def tog_play(self):
        if self.player.state()==QMediaPlayer.PlayingState: self.player.pause()
        else: self.player.play()
    def tog_mode(self): self.mode=(self.mode+1)%3; self.b_mode.setText(["🔁","🔂","🔀"][self.mode])
    def tog_rate(self):
        rs=[1.0,1.25,1.5,2.0,0.5]; i=rs.index(self.rate) if self.rate in rs else 0
        self.rate=rs[(i+1)%5]; self.player.setPlaybackRate(self.rate); self.b_rate.setText(f"{self.rate}x")
    def on_state_changed(self, s): self.b_pp.setText("⏸" if s==QMediaPlayer.PlayingState else "▶")
    def on_media_status(self, s): 
        if s==QMediaPlayer.EndOfMedia: 
            if self.mode==1: self.player.play() 
            else: self.play_next()

    def panel_lrc(self, ls): self.big_lrc.clear(); [self.big_lrc.addItem(x) for x in ls]

    # Config
    def load_conf(self):
        if os.path.exists(CONFIG_FILE):
            try: 
                with open(CONFIG_FILE,'r') as f: 
                    d=json.load(f); self.music_folder=d.get("folder","")
                    if self.music_folder: self.full_scan()
            except:pass
        if os.path.exists(METADATA_FILE): 
            try: with open(METADATA_FILE,'r') as f: self.metadata=json.load(f)
            except:pass
        if os.path.exists(OFFSET_FILE):
            try: with open(OFFSET_FILE,'r') as f: self.saved_offsets=json.load(f)
            except:pass
        if os.path.exists(HISTORY_FILE):
            try: with open(HISTORY_FILE,'r') as f: self.history=json.load(f)
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
    f = QFont("Microsoft YaHei UI", 10); app.setFont(f)
    w = SodaPlayer(); w.show(); sys.exit(app.exec_())

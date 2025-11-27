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
                             QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget, 
                             QScrollArea, QSizePolicy, QSplitter, QGraphicsBlurEffect)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize, QCoreApplication, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect
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
        # QQ音乐风格：深黑带一点点绿的底色
        policy.GradientColor = 0xCC0F1210 
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = POINTER(ACCENT_POLICY)(policy)
        data.SizeOfData = sizeof(policy)
        windll.user32.SetWindowCompositionAttribute(int(hwnd), byref(data))
    except: pass

# --- 2025 概念版样式表 ---
STYLESHEET = """
/* 全局重置 */
QMainWindow { background: transparent; }
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; color: #E0E0E0; }

/* === 左侧导航栏 === */
QFrame#Sidebar {
    background-color: rgba(20, 20, 23, 0.6);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

QLabel#Logo {
    font-size: 20px; font-weight: 900; color: #1ECD97;
    padding: 25px 15px; letter-spacing: 1px; font-style: italic;
}

QLabel#SectionTitle {
    font-size: 11px; color: #666; padding: 15px 20px 5px 20px;
    font-weight: bold; text-transform: uppercase; letter-spacing: 1px;
}

/* 导航胶囊按钮 */
QPushButton.NavBtn {
    background: transparent; border: none; text-align: left;
    padding: 10px 18px; font-size: 14px; color: #AAA;
    border-radius: 8px; margin: 2px 12px;
}
QPushButton.NavBtn:hover {
    background-color: rgba(255, 255, 255, 0.05); color: #FFF;
}
QPushButton.NavBtn:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(30, 205, 151, 0.2), stop:1 rgba(30, 205, 151, 0.05));
    color: #1ECD97; font-weight: bold;
}

/* 特殊功能按钮 */
QPushButton#BiliBtn {
    background: rgba(255, 102, 153, 0.15); color: #FF6699;
    border: 1px solid rgba(255, 102, 153, 0.3);
    font-weight: bold; border-radius: 18px; margin: 10px 20px; padding: 8px;
}
QPushButton#BiliBtn:hover {
    background: rgba(255, 102, 153, 0.3);
    box-shadow: 0 0 10px rgba(255, 102, 153, 0.5);
}

/* === 中间内容区 === */
/* 列表头 */
QHeaderView::section {
    background-color: transparent; border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding: 8px; font-weight: bold; color: #666;
}
/* 表格行 */
QTableWidget {
    background-color: transparent; border: none; outline: none;
    gridline-color: transparent;
}
QTableWidget::item {
    padding: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.02);
    color: #CCC;
}
QTableWidget::item:hover { background-color: rgba(255, 255, 255, 0.03); }
QTableWidget::item:selected {
    background-color: rgba(30, 205, 151, 0.15);
    color: #1ECD97; border-radius: 4px;
}

/* 搜索框 */
QLineEdit#SearchBox {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px; color: #FFF; padding: 6px 15px;
}
QLineEdit#SearchBox:focus {
    background-color: rgba(0, 0, 0, 0.3);
    border: 1px solid #1ECD97;
}

/* === 歌词页 (沉浸式) === */
QWidget#LyricsPage { background-color: #000; }
QListWidget#BigLyric {
    background: transparent; border: none; outline: none;
    font-size: 22px; color: rgba(255,255,255,0.4); font-weight: 500;
}
QListWidget#BigLyric::item { padding: 20px; text-align: center; }
QListWidget#BigLyric::item:selected { 
    color: #FFF; font-size: 30px; font-weight: bold;
    text-shadow: 0 0 10px rgba(30, 205, 151, 0.6);
}

/* === 底部播放栏 (悬浮感) === */
QFrame#PlayerBar {
    background-color: rgba(25, 25, 28, 0.95);
    border-top: 1px solid rgba(255, 255, 255, 0.08);
}

/* 播放控制按钮 */
QPushButton#PlayBtn { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1ECD97, stop:1 #119970);
    color: white; border-radius: 22px; font-size: 20px; 
    min-width: 44px; min-height: 44px; border: none;
}
QPushButton#PlayBtn:hover { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2affb8, stop:1 #18c48f);
    box-shadow: 0 0 15px #1ECD97;
}

QPushButton.CtrlBtn { 
    background: transparent; border: none; font-size: 18px; color: #888; 
}
QPushButton.CtrlBtn:hover { color: #FFF; }

/* 进度条 (发光) */
QSlider::groove:horizontal { 
    height: 3px; background: rgba(255,255,255,0.1); border-radius: 1px; 
}
QSlider::handle:horizontal {
    background: #FFF; width: 10px; height: 10px; margin: -4px 0; border-radius: 5px;
    box-shadow: 0 0 5px #FFF;
}
QSlider::sub-page:horizontal { 
    background: #1ECD97; border-radius: 1px;
}

/* === 右侧面板 === */
QFrame#RightPanel {
    background-color: rgba(20, 20, 23, 0.95);
    border-left: 1px solid rgba(255, 255, 255, 0.05);
}
"""

# --- 辅助函数 ---
def sanitize_filename(name): return re.sub(r'[\\/*?:"<>|]', "", name).strip()
def ms_to_str(ms): return f"{ms//1000//60:02}:{ms//1000%60:02}" if ms else "00:00"

# --- 功能线程 ---
class LyricListSearchWorker(QThread):
    search_finished = pyqtSignal(list)
    def __init__(self, keyword): super().__init__(); self.keyword = keyword
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
                    results.append({'name': s['name'], 'artist': artist, 'id': s['id'], 'duration': s.get('duration', 0), 'duration_str': ms_to_str(s.get('duration', 0))})
            self.search_finished.emit(results)
        except: self.search_finished.emit([])

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

# --- 对话框类 (简化版) ---
class LyricSearchDialog(QDialog):
    def __init__(self, song_name, duration_ms=0, parent=None):
        super().__init__(parent); self.setWindowTitle("搜索歌词"); self.resize(600, 400); self.result_id = None; self.duration_ms = duration_ms
        self.setStyleSheet("QDialog { background: #2b2b2b; color: #FFF; } QLineEdit { background: #444; color: #FFF; } QTableWidget { background: #333; color:#FFF; } QLabel { color: #FFF; }")
        l = QVBoxLayout(self); h = QHBoxLayout(); self.ik = QLineEdit(song_name); b = QPushButton("搜索"); b.clicked.connect(self.ss); h.addWidget(self.ik); h.addWidget(b); l.addLayout(h)
        self.tb = QTableWidget(); self.tb.setColumnCount(4); self.tb.setHorizontalHeaderLabels(["歌名","歌手","时长","ID"]); self.tb.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.tb.setSelectionBehavior(QAbstractItemView.SelectRows); self.tb.itemDoubleClicked.connect(self.os); l.addWidget(self.tb)
        self.sl = QLabel("输入关键词..."); l.addWidget(self.sl)
        btn_bind = QPushButton("下载并绑定"); btn_bind.setStyleSheet("background-color:#31c27c; color:white; padding:8px;"); btn_bind.clicked.connect(self.confirm_bind); l.addWidget(btn_bind)
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
    def confirm_bind(self):
        r = self.tb.currentRow()
        if r>=0: self.result_id = self.tb.item(r,3).text(); self.accept()

class BatchInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("编辑信息"); self.resize(300,200)
        self.setStyleSheet("QDialog { background: #2b2b2b; color: #FFF; } QLineEdit { background: #444; color: #FFF; }")
        l=QVBoxLayout(self)
        self.ca=QCheckBox("歌手"); self.ia=QLineEdit(); self.cb=QCheckBox("专辑"); self.ib=QLineEdit()
        l.addWidget(self.ca); l.addWidget(self.ia); l.addWidget(self.cb); l.addWidget(self.ib)
        b=QPushButton("保存"); b.clicked.connect(self.accept); l.addWidget(b)
    def get_data(self): return (self.ia.text() if self.ca.isChecked() else None, self.ib.text() if self.cb.isChecked() else None)

class BatchRenameDialog(QDialog):
    def __init__(self, pl, parent=None):
        super().__init__(parent); self.setWindowTitle("重命名"); self.resize(500,500); self.pl=pl; self.si=[]
        self.setStyleSheet("QDialog { background: #2b2b2b; color: #FFF; } QLineEdit { background: #444; color: #FFF; } QListWidget { background: #333; color: #FFF; }")
        l=QVBoxLayout(self); self.tab=QTabWidget()
        t1=QWidget(); l1=QVBoxLayout(t1); self.f=QLineEdit(); self.r=QLineEdit()
        l1.addWidget(QLabel("查:")); l1.addWidget(self.f); l1.addWidget(QLabel("替:")); l1.addWidget(self.r); l1.addStretch(); self.tab.addTab(t1,"替换")
        t2=QWidget(); l2=QVBoxLayout(t2); self.sh=QSpinBox(); self.st=QSpinBox()
        l2.addWidget(QLabel("删前:")); l2.addWidget(self.sh); l2.addWidget(QLabel("删后:")); l2.addWidget(self.st); l2.addStretch(); self.tab.addTab(t2,"裁剪")
        l.addWidget(self.tab)
        self.lst=QListWidget()
        for s in pl: i=QListWidgetItem(s["name"]); i.setFlags(i.flags()|Qt.ItemIsUserCheckable); i.setCheckState(Qt.Checked); self.lst.addItem(i)
        l.addWidget(self.lst)
        b=QPushButton("执行"); b.clicked.connect(self.ok); l.addWidget(b)
    def ok(self): self.si=[i for i in range(self.lst.count()) if self.lst.item(i).checkState()==Qt.Checked]; self.accept()
    def get_data(self):
        if self.tab.currentIndex()==0: return "rep", (self.f.text(),self.r.text()), self.si
        else: return "trim", (self.sh.value(),self.st.value()), self.si

class DownloadDialog(QDialog):
    def __init__(self, parent=None, current_p=1, collections=[]):
        super().__init__(parent); self.setWindowTitle("下载"); self.resize(400,250)
        self.setStyleSheet("QDialog { background: #2b2b2b; color: #FFF; } QComboBox { background: #444; color: #FFF; } QLineEdit { background: #444; color: #FFF; }")
        l=QVBoxLayout(self); l.addWidget(QLabel(f"当前 P{current_p}，选模式："))
        self.r1=QRadioButton("单曲"); self.r2=QRadioButton("合集"); self.r1.setChecked(True); l.addWidget(self.r1); l.addWidget(self.r2)
        self.cb=QComboBox(); self.cb.addItem("根目录",""); 
        for c in collections: self.cb.addItem(f"📁 {c}",c)
        self.cb.addItem("➕ 新建...","NEW"); l.addWidget(self.cb)
        self.inew=QLineEdit(); self.inew.setPlaceholderText("名称"); self.inew.hide(); l.addWidget(self.inew)
        self.cb.currentIndexChanged.connect(lambda: self.inew.setVisible(self.cb.currentData()=="NEW"))
        l.addSpacing(10); self.ia=QLineEdit(); self.ia.setPlaceholderText("预设歌手"); l.addWidget(self.ia)
        self.ib=QLineEdit(); self.ib.setPlaceholderText("预设专辑"); l.addWidget(self.ib)
        b=QPushButton("下载"); b.clicked.connect(self.accept); l.addWidget(b)
    def get_data(self):
        m="playlist" if self.r2.isChecked() else "single"; f=self.cb.currentData(); 
        if f=="NEW": f=self.inew.text().strip()
        return m,f,self.ia.text(),self.ib.text()

class DesktopLyricWindow(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool); self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1200,180); l=QVBoxLayout(self); self.col=QColor(255,255,255); self.font=QFont("Microsoft YaHei",36,QFont.Bold)
        self.lbs=[QLabel("") for _ in range(3)]; [l.addWidget(lb) for lb in self.lbs]; [lb.setAlignment(Qt.AlignCenter) for lb in self.lbs]
        self.upd(); self.move(100,800); self.locked=False
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
        elif e.button()==Qt.RightButton: self.show_menu(e.globalPos())
    def mouseMoveEvent(self, e): 
        if e.buttons()==Qt.LeftButton: self.move(e.globalPos()-self.dp)
    def show_menu(self, p):
        m=QMenu(); m.addAction("🎨 颜色",self.cc); m.addAction("🅰️ 字体",self.cf)
        m.addAction("🔒 锁定/解锁",self.tl); m.addAction("❌ 关闭",self.hide); m.exec_(p)
    def cc(self): 
        c=QColorDialog.getColor(self.col,self); 
        if c.isValid(): self.col=c; self.upd()
    def cf(self): 
        f,o=QFontDialog.getFont(self.font,self); 
        if o: self.font=f; self.upd()
    def tl(self): self.locked=not self.locked

# --- 主界面 ---
class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 2025")
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)
        
        # 深色渐变背景 + 毛玻璃
        self.setAttribute(Qt.WA_TranslucentBackground)
        if os.name == 'nt': try: enable_acrylic(int(self.winId()))
        except: pass
        
        # 数据
        self.music_folder = ""; self.current_collection = ""; self.collections = []
        self.playlist = []; self.history = []; self.lyrics = []; self.current_index = -1
        self.offset = 0.0; self.saved_offsets = {}; self.metadata = {}
        self.mode = 0; self.rate = 1.0; self.volume = 80; self.is_slider_pressed = False
        self.right_panel_visible = True # 右侧面板状态

        # 播放器
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.on_pos)
        self.player.durationChanged.connect(self.on_dur)
        self.player.stateChanged.connect(self.on_state)
        self.player.mediaStatusChanged.connect(self.on_media)
        self.player.error.connect(self.handle_err)
        self.player.setVolume(self.volume)

        self.desktop_lyric = DesktopLyricWindow(); self.desktop_lyric.show()
        self.init_ui(); self.load_conf()

    def init_ui(self):
        cw = QWidget(); self.setCentralWidget(cw)
        
        # 核心布局：三栏 (左侧导航 | 中间内容 | 右侧面板)
        main_h = QHBoxLayout(cw); main_h.setContentsMargins(0,0,0,0); main_h.setSpacing(0)

        # 1. 左侧导航栏 (Compact)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(240)
        sl = QVBoxLayout(self.sidebar); sl.setContentsMargins(0,0,0,0); sl.setSpacing(5)
        
        sl.addWidget(QLabel("🎵 SODA MUSIC", objectName="Logo"))
        
        # 核心功能
        sl.addWidget(QLabel("我的音乐", objectName="SectionTitle"))
        self.btn_all = QPushButton("💿 全部歌曲"); self.btn_all.setProperty("NavBtn",True); self.btn_all.setCheckable(True); self.btn_all.clicked.connect(lambda: self.switch_coll(None))
        self.btn_hist = QPushButton("🕒 最近播放"); self.btn_hist.setProperty("NavBtn",True); self.btn_hist.setCheckable(True); self.btn_hist.clicked.connect(lambda: self.switch_coll("HISTORY"))
        sl.addWidget(self.btn_all); sl.addWidget(self.btn_hist)
        
        sl.addWidget(QLabel("歌单管理", objectName="SectionTitle"))
        self.nav = QListWidget(); self.nav.setStyleSheet("background:transparent; border:none; font-size:14px; color:#AAA;")
        self.nav.itemClicked.connect(self.on_coll_click)
        sl.addWidget(self.nav)
        
        # 底部工具
        sl.addStretch()
        b_bili = QPushButton("📥 B站提取"); b_bili.setObjectName("DownloadBtn"); b_bili.clicked.connect(self.dl_bili)
        sl.addWidget(b_bili)
        
        tools = QWidget(); tl = QHBoxLayout(tools); tl.setContentsMargins(10,0,10,10)
        b_set = QPushButton("📁"); b_set.setToolTip("根目录"); b_set.clicked.connect(self.sel_folder); b_set.setStyleSheet("border:1px solid #333; border-radius:15px; width:30px; height:30px; color:#888;")
        b_lrc = QPushButton("🎤"); b_lrc.setToolTip("桌面歌词"); b_lrc.clicked.connect(self.tog_desk_lrc); b_lrc.setStyleSheet("border:1px solid #333; border-radius:15px; width:30px; height:30px; color:#888;")
        b_add = QPushButton("➕"); b_add.setToolTip("新建合集"); b_add.clicked.connect(self.new_coll); b_add.setStyleSheet("border:1px solid #333; border-radius:15px; width:30px; height:30px; color:#888;")
        tl.addWidget(b_set); tl.addWidget(b_lrc); tl.addWidget(b_add)
        sl.addWidget(tools)
        
        main_h.addWidget(self.sidebar)

        # 2. 中间内容区 (Stacked: List / LyricPage)
        center_panel = QWidget()
        cl = QVBoxLayout(center_panel); cl.setContentsMargins(0,0,0,0); cl.setSpacing(0)
        
        # TopBar
        top = QWidget(); top.setFixedHeight(60); th = QHBoxLayout(top); th.setContentsMargins(20,10,20,10)
        self.lb_title = QLabel("全部音乐"); self.lb_title.setStyleSheet("font-size:20px; font-weight:bold; color:#FFF;")
        self.search = QLineEdit(); self.search.setObjectName("SearchBox"); self.search.setPlaceholderText("🔍 搜索本地歌曲..."); self.search.setFixedWidth(240)
        self.search.textChanged.connect(self.filter_list)
        th.addWidget(self.lb_title); th.addStretch(); th.addWidget(self.search)
        cl.addWidget(top)

        # Stack
        self.stack = QStackedWidget()
        
        # Page 0: Song List
        p0 = QWidget(); p0l = QVBoxLayout(p0); p0l.setContentsMargins(0,0,0,0)
        self.table = QTableWidget(); self.table.setColumnCount(4); self.table.setHorizontalHeaderLabels(["标题","歌手","专辑","时长"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False); self.table.setShowGrid(False); self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.itemDoubleClicked.connect(self.play_sel); self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_menu)
        p0l.addWidget(self.table)
        self.stack.addWidget(p0)
        
        # Page 1: Immersive Lyrics
        p1 = QWidget(); p1.setObjectName("LyricsPage"); p1l = QHBoxLayout(p1)
        # Left Cover
        lc = QVBoxLayout(); lc.setAlignment(Qt.AlignCenter)
        self.art_cover = QLabel(); self.art_cover.setFixedSize(350,350); self.art_cover.setStyleSheet("background-color:#222; border-radius:12px;")
        # Mock blur effect with gradient for now as local files don't have embedded art usually
        self.art_cover.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1A2980, stop:1 #26D0CE); border-radius:12px;")
        self.art_title = QLabel("--"); self.art_title.setStyleSheet("font-size:24px; font-weight:bold; color:#FFF; margin-top:20px;")
        self.art_artist = QLabel("--"); self.art_artist.setStyleSheet("font-size:16px; color:#AAA;")
        btn_back = QPushButton("﹀ 返回列表"); btn_back.setCursor(Qt.PointingHandCursor); btn_back.setStyleSheet("background:transparent; color:#666; border:none; margin-top:40px;")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        lc.addWidget(self.art_cover); lc.addWidget(self.art_title); lc.addWidget(self.art_artist); lc.addWidget(btn_back)
        p1l.addLayout(lc, stretch=1)
        # Right Lyrics
        self.big_lrc = QListWidget(); self.big_lrc.setObjectName("BigLyric"); self.big_lrc.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.big_lrc.setFocusPolicy(Qt.NoFocus); p1l.addWidget(self.big_lrc, stretch=1)
        self.stack.addWidget(p1)

        cl.addWidget(self.stack)

        # Bottom Player Bar
        bar = QFrame(); bar.setObjectName("PlayerBar"); bar.setFixedHeight(90); bl = QHBoxLayout(bar); bl.setContentsMargins(20,5,20,5)
        
        # Info
        info = QWidget(); il = QHBoxLayout(info); il.setContentsMargins(0,0,0,0)
        self.mini_art = QPushButton(); self.mini_art.setFixedSize(56,56); self.mini_art.setCursor(Qt.PointingHandCursor)
        self.mini_art.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1A2980, stop:1 #26D0CE); border-radius:6px; border:none;")
        self.mini_art.clicked.connect(self.tog_page)
        it = QWidget(); itl = QVBoxLayout(it); itl.setSpacing(2); itl.setContentsMargins(10,10,0,10)
        self.b_ti = QLabel("--"); self.b_ti.setStyleSheet("font-weight:bold; color:#EEE; font-size:14px;")
        self.b_ar = QLabel("--"); self.b_ar.setStyleSheet("color:#888; font-size:12px;")
        itl.addWidget(self.b_ti); itl.addWidget(self.b_ar); il.addWidget(self.mini_art); il.addWidget(it)
        bl.addWidget(info, stretch=3)

        # Controls
        ctr = QWidget(); cl_lay = QVBoxLayout(ctr); cl_lay.setContentsMargins(0,5,0,5)
        # Buttons
        cbs = QHBoxLayout(); cbs.setSpacing(15); cbs.setAlignment(Qt.AlignCenter)
        self.bm = QPushButton("🔁"); self.bm.setProperty("CtrlBtn",True); self.bm.clicked.connect(self.tog_mode)
        bp = QPushButton("⏮"); bp.setProperty("CtrlBtn",True); bp.clicked.connect(self.play_prev)
        self.bp = QPushButton("▶"); self.bp.setObjectName("PlayBtn"); self.bp.clicked.connect(self.tog_play)
        bn = QPushButton("⏭"); bn.setProperty("CtrlBtn",True); bn.clicked.connect(self.play_next)
        self.br = QPushButton("1.0x"); self.br.setProperty("CtrlBtn",True); self.br.setStyleSheet("font-size:12px;"); self.br.clicked.connect(self.tog_rate)
        cbs.addWidget(self.bm); cbs.addWidget(bp); cbs.addWidget(self.bp); cbs.addWidget(bn); cbs.addWidget(self.br)
        # Progress
        cps = QHBoxLayout()
        self.lc = QLabel("00:00"); self.lc.setStyleSheet("color:#666; font-size:11px;")
        self.lt = QLabel("00:00"); self.lt.setStyleSheet("color:#666; font-size:11px;")
        self.sl = QSlider(Qt.Horizontal); self.sl.setRange(0,0); self.sl.sliderPressed.connect(self.sp)
        self.sl.sliderReleased.connect(self.sr); self.sl.valueChanged.connect(self.sm)
        cps.addWidget(self.lc); cps.addWidget(self.sl); cps.addWidget(self.lt)
        cl_lay.addLayout(cbs); cl_lay.addLayout(cps)
        bl.addWidget(ctr, stretch=4)

        # Right Utils
        rut = QHBoxLayout(); rut.setAlignment(Qt.AlignRight)
        self.sv = QSlider(Qt.Horizontal); self.sv.setRange(0,100); self.sv.setValue(80); self.sv.setFixedWidth(80)
        self.sv.valueChanged.connect(self.player.setVolume)
        
        b_side = QPushButton("Playlist"); b_side.setProperty("CtrlBtn",True); b_side.clicked.connect(self.tog_right_panel)
        b_side.setIcon(QIcon(self.style().standardIcon(self.style().SP_FileDialogListView)))

        rut.addWidget(QLabel("🔈", styleSheet="color:#888;")); rut.addWidget(self.sv); rut.addSpacing(10); rut.addWidget(b_side)
        bl.addLayout(rut, stretch=3)

        cl.addWidget(bar)
        main_h.addWidget(center_panel, stretch=1)

        # 3. 右侧可折叠面板 (Info & Lyrics)
        self.right_panel = QFrame(); self.right_panel.setObjectName("RightPanel"); self.right_panel.setFixedWidth(280)
        rl = QVBoxLayout(self.right_panel); rl.setContentsMargins(0,0,0,0)
        rl.addWidget(QLabel("当前播放", styleSheet="font-size:14px; font-weight:bold; padding:15px; color:#DDD;"))
        
        self.lrc_p = QListWidget(); self.lrc_p.setObjectName("LyricPanel"); self.lrc_p.setFocusPolicy(Qt.NoFocus)
        self.lrc_p.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rl.addWidget(self.lrc_p)
        
        # Offset controls
        off = QHBoxLayout(); off.setContentsMargins(10,10,10,10)
        bs = QPushButton("-0.5s"); bs.setProperty("OffsetBtn",True); bs.clicked.connect(lambda: self.adj_off(-0.5))
        self.lo = QLabel("0.0s"); self.lo.setStyleSheet("color:#888; font-size:11px;")
        bf = QPushButton("+0.5s"); bf.setProperty("OffsetBtn",True); bf.clicked.connect(lambda: self.adj_off(0.5))
        off.addWidget(bs); off.addWidget(self.lo); off.addWidget(bf); rl.addLayout(off)

        main_h.addWidget(self.right_panel)

    # --- 动效 ---
    def tog_right_panel(self):
        w = 0 if self.right_panel.width() > 0 else 280
        self.anim = QPropertyAnimation(self.right_panel, b"maximumWidth")
        self.anim.setDuration(300); self.anim.setStartValue(self.right_panel.width()); self.anim.setEndValue(w)
        self.anim.setEasingCurve(QEasingCurve.OutCubic); self.anim.start()
    
    def tog_page(self):
        idx = 1 if self.stack.currentIndex()==0 else 0
        self.stack.setCurrentIndex(idx)

    # --- 逻辑 (保持原样) ---
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
        for c in self.collections: 
            it = QListWidgetItem(f"📁  {c}"); it.setData(Qt.UserRole, c); self.nav.addItem(it)
        self.switch_coll(None)

    def switch_coll(self, coll_name):
        self.btn_all.setChecked(coll_name is None)
        self.btn_hist.setChecked(coll_name == "HISTORY")
        if coll_name == "HISTORY": self.current_collection="HISTORY"; self.lb_title.setText("最近播放")
        elif coll_name: self.current_collection=coll_name; self.lb_title.setText(coll_name)
        else: self.current_collection=""; self.lb_title.setText("全部音乐")
        self.load_list()

    def on_coll_click(self, item): self.switch_coll(item.data(Qt.UserRole))

    def load_list(self):
        self.playlist = []; self.table.setRowCount(0)
        ext = ('.mp3','.wav','.m4a','.flac','.mp4')
        ds = []
        if self.current_collection=="HISTORY":
            for s in self.history: self.add_row(s)
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
            h = True
            for c in range(3):
                if self.table.item(i,c) and txt in self.table.item(i,c).text().lower(): h=False
            self.table.setRowHidden(i, h)

    def play_sel(self, item): self.play(item.row())
    def play(self, idx):
        if not self.playlist: return
        self.player.setMedia(QMediaContent()) # Fix rename crash
        self.current_index = idx; s = self.playlist[idx]
        if s not in self.history: self.history.insert(0,s); self.save_hist()
        try:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(s["path"])))
            self.player.setPlaybackRate(self.rate); self.player.play()
            self.b_pp.setText("⏸")
            
            nm = os.path.splitext(s["name"])[0]
            self.bar_title.setText(nm); self.bar_artist.setText(s["artist"])
            self.art_title.setText(nm); self.art_artist.setText(s["artist"])
            self.b_ti.setText(nm[:10]+".." if len(nm)>10 else nm); self.b_ar.setText(s["artist"])

            self.offset = self.saved_offsets.get(s["name"], 0.0)
            self.lo.setText(f"{self.offset}s")
            
            lp = os.path.splitext(s["path"])[0]+".lrc"
            if os.path.exists(lp):
                with open(lp,'r',encoding='utf-8',errors='ignore') as f: self.parse_lrc(f.read())
            else:
                self.panel_lrc(["🔍 搜索歌词..."]); self.sw = LyricListSearchWorker(nm)
                self.sw.search_finished.connect(self.auto_lrc)
                self.sw.start()
        except: pass

    def auto_lrc(self, res):
        if res:
            lp = os.path.splitext(self.playlist[self.current_index]["path"])[0]+".lrc"
            self.ld = LyricDownloader(res[0]['id'], lp)
            self.ld.finished_signal.connect(self.parse_lrc)
            self.ld.start()
        else: self.panel_lrc(["🎵 纯音乐"])

    def parse_lrc(self, txt):
        self.lyrics = []; self.lrc_p.clear(); self.big_lrc.clear()
        for l in txt.splitlines():
            m = re.match(r'\[(\d+):(\d+)\.(\d+)\](.*)', l)
            if m:
                t = int(m.group(1))*60 + int(m.group(2)) + int(m.group(3))/100
                tx = m.group(4).strip()
                if tx: self.lyrics.append({"t":t, "txt":tx}); self.lrc_p.addItem(tx); self.big_lrc.addItem(tx)

    def panel_lrc(self, ls):
        self.lyrics=[]; self.lrc_p.clear(); self.big_lrc.clear()
        for x in ls: self.lrc_p.addItem(x); self.big_lrc.addItem(x)

    def on_pos(self, p):
        if not self.is_slider_pressed: self.slider.setValue(p)
        self.lc.setText(ms_to_str(p))
        t = p/1000 + self.offset
        if self.lyrics:
            idx = -1
            for i, l in enumerate(self.lyrics):
                if t >= l["t"]: idx = i
                else: break
            if idx != -1:
                pr=self.lyrics[idx-1]["txt"] if idx>0 else ""; cu=self.lyrics[idx]["txt"]; ne=self.lyrics[idx+1]["txt"] if idx<len(self.lyrics)-1 else ""
                self.desktop_lyric.set_text(pr, cu, ne)
                self.lrc_p.setCurrentRow(idx); self.lrc_p.scrollToItem(self.lrc_p.item(idx), QAbstractItemView.PositionAtCenter)
                self.big_lrc.setCurrentRow(idx); self.big_lrc.scrollToItem(self.big_lrc.item(idx), QAbstractItemView.PositionAtCenter)

    def show_menu(self, p):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return
        m = QMenu(); m.setStyleSheet("QMenu{background:#2D2D30; color:#EEE;} QMenu::item:selected{background:#3E3E42;}")
        mv = m.addMenu("📂 移动到...")
        mv.addAction("根目录", lambda: self.do_move(rows, ""))
        for c in self.collections: mv.addAction(c, lambda _,t=c: self.do_move(rows, t))
        m.addAction("🔠 批量重命名", self.do_rename_batch)
        m.addAction("✏️ 改信息", lambda: self.do_edit_info(rows))
        m.addSeparator()
        if len(rows)==1:
            i = rows[0]
            m.addAction("🔐 绑定/整理", lambda: self.do_bind(i))
            m.addAction("🔍 搜歌词", lambda: self.do_search_lrc(i))
            m.addAction("❌ 删歌词", lambda: self.do_del_lrc(i))
        m.addAction("🗑️ 删除", lambda: self.do_del(rows))
        m.exec_(self.table.mapToGlobal(p))

    # --- Actions ---
    def do_move(self, rows, target):
        self.player.setMedia(QMediaContent())
        tp = os.path.join(self.music_folder, target) if target else self.music_folder
        if not os.path.exists(tp): os.makedirs(tp)
        targets = [self.playlist[i] for i in rows]; cnt=0
        for s in targets:
            try:
                src = s["path"]; dst = os.path.join(tp, s["name"])
                if src!=dst:
                    shutil.move(src, dst)
                    l = os.path.splitext(src)[0]+".lrc"
                    if os.path.exists(l): shutil.move(l, os.path.join(tp, os.path.basename(l)))
                    cnt+=1
            except: pass
        self.full_scan(); QMessageBox.information(self,"OK",f"移动 {cnt}")

    def do_rename_batch(self):
        if not self.playlist: return
        self.player.setMedia(QMediaContent())
        d = BatchRenameDialog(self.playlist, self)
        if d.exec_()==QDialog.Accepted:
            m, p, idxs = d.get_data()
            ts = [self.playlist[i] for i in idxs if i<len(self.playlist)]
            for s in ts:
                old=s["path"]; base,ext=os.path.splitext(s["name"]); nb=base
                if m=="rep" and p[0] in base: nb=base.replace(p[0],p[1])
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
                self.full_scan(); QMessageBox.information(self,"ok","整理完成")
            except:pass

    def do_search_lrc(self, idx):
        s = self.playlist[idx]; dur = self.player.duration() if self.current_index==idx else 0
        dlg = LyricSearchDialog(os.path.splitext(s["name"])[0], dur, self)
        if dlg.exec_()==QDialog.Accepted and dlg.result_id:
            lp = os.path.splitext(s["path"])[0]+".lrc"
            self.ld = LyricDownloader(dlg.result_id, lp)
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
                    p=self.playlist[i]["path"]; os.remove(p)
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
                self.lb_title.setText("⏳ 下载中...")
                self.dl = BilibiliDownloader(u, path, mode, p)
                self.dl.progress_signal.connect(lambda s: self.lb_title.setText(s))
                self.dl.finished_signal.connect(self.on_dl_ok)
                self.dl.start()
    def on_dl_ok(self, p):
        a,b = self.tmp_meta
        if a or b:
            for f in os.listdir(p):
                if f not in self.metadata: self.metadata[f]={"a":a or "未知", "b":b or "未知"}
            self.save_meta()
        self.full_scan(); self.lb_title.setText("下载完成")

    def new_coll(self):
        n, ok = QInputDialog.getText(self, "新建", "名称:")
        if ok and n: 
            os.makedirs(os.path.join(self.music_folder, sanitize_filename(n)), exist_ok=True)
            self.full_scan()

    def adj_off(self, v):
        self.offset+=v; self.lo.setText(f"{self.offset}s")
        if self.current_index>=0: 
            self.saved_offsets[self.playlist[self.current_index]["name"]]=self.offset
            self.save_off()

    def sel_folder(self):
        f=QFileDialog.getExistingDirectory(self,"选目录")
        if f: self.music_folder=f; self.full_scan(); self.save_config()
    def tog_lyric(self): 
        if self.desktop_lyric.isVisible(): self.desktop_lyric.hide()
        else: self.desktop_lyric.show()
    def tog_desk_lrc(self): self.tog_lyric()
    def sp(self): self.is_slider_pressed=True
    def sr(self): self.is_slider_pressed=False; self.player.setPosition(self.sl.value())
    def sm(self, v): 
        if self.is_slider_pressed: self.lc.setText(ms_to_str(v))
    def on_dur(self, d): 
        self.sl.setRange(0, d); self.lt.setText(ms_to_str(d))
        if self.current_index>=0:
             self.playlist[self.current_index]["dur"] = ms_to_str(d)
             self.table.setItem(self.current_index, 3, QTableWidgetItem(ms_to_str(d)))
    def on_state(self, s): self.b_pp.setText("⏸" if s==QMediaPlayer.PlayingState else "▶")
    def on_media(self, s): 
        if s==QMediaPlayer.EndOfMedia: 
            if self.mode==1: self.player.play() 
            else: self.play_next()
    def handle_err(self): QTimer.singleShot(1000, self.play_next)
    def tog_play(self):
        if self.player.state()==QMediaPlayer.PlayingState: self.player.pause()
        else: self.player.play()
    def tog_mode(self): self.mode=(self.mode+1)%3; self.bm.setText(["🔁","🔂","🔀"][self.mode])
    def tog_rate(self):
        rs=[1.0,1.25,1.5,2.0,0.5]; i=rs.index(self.rate) if self.rate in rs else 0
        self.rate=rs[(i+1)%5]; self.player.setPlaybackRate(self.rate); self.br.setText(f"{self.rate}x")
    def play_next(self):
        if not self.playlist: return
        n = random.randint(0,len(self.playlist)-1) if self.mode==2 else (self.current_index+1)%len(self.playlist)
        self.play(n)
    def play_prev(self):
        if not self.playlist: return
        p = random.randint(0,len(self.playlist)-1) if self.mode==2 else (self.current_index-1)%len(self.playlist)
        self.play(p)
    
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

    # 批量移动弹窗
    def batch_move_dialog(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return QMessageBox.warning(self,"提示","请先选择歌曲")
        ls = ["根目录"] + self.collections
        t, ok = QInputDialog.getItem(self, "移动", "目标:", ls, 0, False)
        if ok: self.do_move(rows, "" if t=="根目录" else t)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(app_path, 'PyQt5', 'Qt', 'plugins')
        QCoreApplication.addLibraryPath(os.path.join(app_path, 'PyQt5', 'Qt', 'plugins'))
    app = QApplication(sys.argv)
    f = QFont("Microsoft YaHei UI", 10); app.setFont(f)
    w = SodaPlayer(); w.show(); sys.exit(app.exec_())

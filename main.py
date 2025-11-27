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
                             QScrollArea, QSizePolicy)
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

# --- Windows 毛玻璃特效 API ---
class ACCENT_POLICY(Structure):
    _fields_ = [("AccentState", c_int), ("AccentFlags", c_int), ("GradientColor", c_int), ("AnimationId", c_int)]
class WINDOWCOMPOSITIONATTRIBDATA(Structure):
    _fields_ = [("Attribute", c_int), ("Data", POINTER(ACCENT_POLICY)), ("SizeOfData", c_int)]
def enable_acrylic(hwnd):
    try:
        policy = ACCENT_POLICY()
        policy.AccentState = 4; policy.GradientColor = 0xCCF2F2F2 
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19; data.Data = POINTER(ACCENT_POLICY)(policy); data.SizeOfData = sizeof(policy)
        windll.user32.SetWindowCompositionAttribute(int(hwnd), byref(data))
    except: pass

# --- 极光 UI 样式 (iOS 风格) ---
STYLESHEET = """
QMainWindow { background: transparent; }
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; color: #333; }

/* 侧边栏 */
QFrame#Sidebar { background-color: rgba(245, 245, 247, 0.85); border-right: 1px solid rgba(0,0,0,0.08); }
QLabel#Logo { font-size: 22px; font-weight: 900; color: #1ECD97; padding: 30px 20px; }
QLabel#SectionTitle { font-size: 12px; color: #8e8e93; font-weight: bold; padding: 15px 20px 5px 20px; }

/* 导航按钮 */
QPushButton.NavBtn {
    background: transparent; border: none; text-align: left; padding: 10px 20px;
    font-size: 14px; color: #444; border-radius: 8px; margin: 2px 10px;
}
QPushButton.NavBtn:hover { background-color: rgba(0,0,0,0.04); }
QPushButton.NavBtn:checked { background-color: #e6f7ff; color: #1ECD97; font-weight: bold; }

QPushButton#DownloadBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF6699, stop:1 #ff85b3);
    color: white; font-weight: bold; border-radius: 18px; margin: 10px 20px; padding: 8px;
}
QPushButton#DownloadBtn:hover { margin-top: 11px; }

/* 表格列表 */
QTableWidget {
    background-color: rgba(255, 255, 255, 0.5); border: none; outline: none;
    selection-background-color: rgba(30, 205, 151, 0.15); selection-color: #1ECD97;
    alternate-background-color: rgba(250, 250, 250, 0.4);
}
QHeaderView::section {
    background-color: transparent; border: none; border-bottom: 1px solid #eee;
    padding: 8px; font-weight: bold; color: #888;
}

/* 歌词页 */
QWidget#LyricsPage { background-color: #ffffff; }
QListWidget#BigLyric { background: transparent; border: none; outline: none; font-size: 18px; color: #999; font-weight: 500; }
QListWidget#BigLyric::item { padding: 15px; text-align: center; }
QListWidget#BigLyric::item:selected { color: #333; font-size: 24px; font-weight: bold; }

/* 播放栏 */
QFrame#PlayerBar { background-color: rgba(255, 255, 255, 0.9); border-top: 1px solid rgba(0,0,0,0.05); }
QPushButton#PlayBtn { 
    background-color: #1ECD97; color: white; border-radius: 24px; 
    font-size: 20px; min-width: 48px; min-height: 48px; border:none;
}
QPushButton#PlayBtn:hover { background-color: #1ebc8a; transform: scale(1.05); }
QPushButton.CtrlBtn { background: transparent; border: none; font-size: 18px; color: #555; }
QPushButton.CtrlBtn:hover { color: #1ECD97; }

QSlider::groove:horizontal { height: 4px; background: #e5e5e5; border-radius: 2px; }
QSlider::handle:horizontal { background: #fff; border: 1px solid #ccc; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
QSlider::sub-page:horizontal { background: #1ECD97; border-radius: 2px; }
"""

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def ms_to_str(ms):
    if not ms: return "00:00"
    s = ms // 1000
    return f"{s//60:02}:{s%60:02}"

# --- 批量重命名弹窗 ---
class BatchRenameDialog(QDialog):
    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量重命名")
        self.resize(500, 600)
        self.playlist = playlist
        self.selected_indices = []
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # Tab 1: 替换
        t1 = QWidget(); l1 = QVBoxLayout(t1)
        h1 = QHBoxLayout()
        self.ifind = QLineEdit(); self.ifind.setPlaceholderText("查找")
        self.irep = QLineEdit(); self.irep.setPlaceholderText("替换")
        h1.addWidget(QLabel("查找:")); h1.addWidget(self.ifind)
        h1.addWidget(QLabel("替换:")); h1.addWidget(self.irep)
        l1.addLayout(h1); l1.addStretch()
        self.tabs.addTab(t1, "文本替换")
        
        # Tab 2: 裁剪
        t2 = QWidget(); l2 = QVBoxLayout(t2)
        h2 = QHBoxLayout()
        self.sh = QSpinBox(); self.sh.setRange(0, 50)
        self.st = QSpinBox(); self.st.setRange(0, 50)
        h2.addWidget(QLabel("删前N字:")); h2.addWidget(self.sh)
        h2.addWidget(QLabel("删后N字:")); h2.addWidget(self.st)
        l2.addLayout(h2); l2.addStretch()
        self.tabs.addTab(t2, "字符裁剪")
        
        layout.addWidget(self.tabs)
        
        self.list = QListWidget()
        for s in self.playlist:
            item = QListWidgetItem(s["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list.addItem(item)
        layout.addWidget(self.list)
        
        h_sel = QHBoxLayout()
        b_all = QPushButton("全选"); b_all.clicked.connect(lambda: self.set_all(True))
        b_no = QPushButton("全不选"); b_no.clicked.connect(lambda: self.set_all(False))
        h_sel.addWidget(b_all); h_sel.addWidget(b_no); h_sel.addStretch()
        layout.addLayout(h_sel)
        
        btn = QPushButton("执行重命名")
        btn.setFixedHeight(40)
        btn.setStyleSheet("background:#1ECD97; color:white; font-weight:bold; border-radius:6px;")
        btn.clicked.connect(self.on_accept)
        layout.addWidget(btn)

    def set_all(self, checked):
        st = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.list.count()): self.list.item(i).setCheckState(st)
    def on_accept(self):
        self.selected_indices = [i for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.Checked]
        self.accept()
    def get_data(self):
        idx = self.tabs.currentIndex()
        if idx == 0: return "replace", (self.ifind.text(), self.irep.text()), self.selected_indices
        else: return "trim", (self.sh.value(), self.st.value()), self.selected_indices

# --- 在线歌词搜索 ---
class LyricListSearchWorker(QThread):
    search_finished = pyqtSignal(list)
    def __init__(self, keyword): super().__init__(); self.keyword = keyword
    def run(self):
        try:
            url = "http://music.163.com/api/search/get/web?csrf_token="
            data = urllib.parse.urlencode({'s': self.keyword, 'type': 1, 'offset': 0, 'total': 'true', 'limit': 15}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'User-Agent':'Mozilla/5.0'})
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
        self.tb = QTableWidget(); self.tb.setColumnCount(4); self.tb.setHorizontalHeaderLabels(["歌名","歌手","时长","ID"]); self.tb.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tb.setSelectionBehavior(QAbstractItemView.SelectRows); self.tb.itemDoubleClicked.connect(self.on_sel); l.addWidget(self.tb)
        if duration_ms>0: l.addWidget(QLabel(f"本地时长: {ms_to_str(duration_ms)}", styleSheet="color:#888"))
        btn = QPushButton("绑定选中歌词"); btn.clicked.connect(self.confirm); l.addWidget(btn)
    def ss(self):
        self.tb.setRowCount(0)
        self.w = LyricListSearchWorker(self.ik.text())
        self.w.search_finished.connect(self.sd); self.w.start()
    def sd(self, res):
        self.tb.setRowCount(len(res))
        for i, r in enumerate(res):
            self.tb.setItem(i,0,QTableWidgetItem(r['name'])); self.tb.setItem(i,1,QTableWidgetItem(r['artist']))
            ti = QTableWidgetItem(r['duration_str'])
            if abs(r['duration']-self.duration_ms)<3000: ti.setForeground(QColor("#1ECD97"))
            self.tb.setItem(i,2,ti); self.tb.setItem(i,3,QTableWidgetItem(str(r['id'])))
    def on_sel(self): self.confirm()
    def confirm(self):
        r = self.tb.currentRow()
        if r>=0: self.result_id=self.tb.item(r,3).text(); self.accept()

class LyricDownloader(QThread):
    finished_signal = pyqtSignal(str)
    def __init__(self, sid, path): super().__init__(); self.sid=sid; self.path=path
    def run(self):
        try:
            url = f"http://music.163.com/api/song/lyric?os=pc&id={self.sid}&lv=-1&kv=-1&tv=-1"
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})) as f:
                res = json.loads(f.read().decode('utf-8'))
            if 'lrc' in res:
                lrc = res['lrc']['lyric']
                with open(self.path, 'w', encoding='utf-8') as f: f.write(lrc)
                self.finished_signal.emit(lrc)
        except: pass

# --- B站下载 ---
class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str); finished_signal = pyqtSignal(str); error_signal = pyqtSignal(str)
    def __init__(self, u, p, m, sp): super().__init__(); self.u=u; self.p=p; self.m=m; self.sp=sp
    def run(self):
        if not yt_dlp: return self.error_signal.emit("无yt-dlp")
        if not os.path.exists(self.p): os.makedirs(self.p, exist_ok=True)
        def ph(d):
            if d['status']=='downloading': self.progress_signal.emit(f"⬇️ {d.get('_percent_str','')} {os.path.basename(d.get('filename',''))[:15]}")
        # 强制下载 m4a
        opts = {'format':'bestaudio[ext=m4a]/best', 'outtmpl':os.path.join(self.p,'%(title)s.%(ext)s'),
                'overwrites':True, 'noplaylist':self.m=='single', 'playlist_items':str(self.sp) if self.m=='single' else f"{self.sp}-",
                'progress_hooks':[ph], 'quiet':True, 'nocheckcertificate':True, 'restrictfilenames':False}
        try:
            with yt_dlp.YoutubeDL(opts) as y: y.download([self.u])
            self.finished_signal.emit(self.p)
        except Exception as e: self.error_signal.emit(str(e))

class DownloadDialog(QDialog):
    def __init__(self, parent=None, p=1, cols=[]):
        super().__init__(parent); self.setWindowTitle("下载"); self.resize(400,280)
        l=QVBoxLayout(self); l.addWidget(QLabel(f"当前 P{p}，选择："))
        self.rb_s=QRadioButton(f"单曲 (P{p})"); self.rb_l=QRadioButton(f"合集 (P{p}-End)"); self.rb_s.setChecked(True)
        l.addWidget(self.rb_s); l.addWidget(self.rb_l); l.addSpacing(10)
        l.addWidget(QLabel("存入：")); self.cb=QComboBox(); self.cb.addItem("根目录","")
        for c in cols: self.cb.addItem(f"📁 {c}",c)
        self.cb.addItem("➕ 新建...","NEW"); l.addWidget(self.cb)
        self.inew=QLineEdit(); self.inew.setPlaceholderText("新合集名"); self.inew.hide(); l.addWidget(self.inew)
        self.cb.currentIndexChanged.connect(lambda: self.inew.setVisible(self.cb.currentData()=="NEW"))
        l.addSpacing(10); b=QPushButton("下载"); b.clicked.connect(self.accept); l.addWidget(b)
    def get_data(self):
        m="playlist" if self.rb_l.isChecked() else "single"; f=self.cb.currentData()
        if f=="NEW": f=self.inew.text().strip()
        return m,f

# --- 桌面歌词 ---
class DesktopLyricWindow(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool); self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1200,180); l=QVBoxLayout(self); l.setContentsMargins(0,0,0,0)
        self.col=QColor(255,255,255); self.font=QFont("Microsoft YaHei",36,QFont.Bold)
        self.lbs=[QLabel("") for _ in range(3)]; [l.addWidget(lb) for lb in self.lbs]; [lb.setAlignment(Qt.AlignCenter) for lb in self.lbs]
        self.upd(); self.locked=False
    def upd(self):
        sh=QColor(0,0,0,200); s=self.font.pointSize()
        for i,lb in enumerate(self.lbs):
            ef=QGraphicsDropShadowEffect(); ef.setBlurRadius(10); ef.setColor(sh); ef.setOffset(1,1); lb.setGraphicsEffect(ef)
            f=QFont(self.font); f.setPointSize(s if i==1 else int(s*0.6))
            c=self.col.name() if i==1 else f"rgba({self.col.red()},{self.col.green()},{self.col.blue()},160)"
            lb.setStyleSheet(f"color:{c}"); lb.setFont(f)
    def set_text(self, p, c, n): self.lbs[0].setText(p); self.lbs[1].setText(c); self.lbs[2].setText(n)
    def mousePressEvent(self, e): 
        if e.button()==Qt.LeftButton and not self.locked: self.dp=e.globalPos()-self.frameGeometry().topLeft()
        elif e.button()==Qt.RightButton: self.menu(e.globalPos())
    def mouseMoveEvent(self, e): 
        if e.buttons()==Qt.LeftButton and not self.locked: self.move(e.globalPos()-self.dp)
    def menu(self, p):
        m=QMenu(); m.addAction("🎨 颜色", self.cc); m.addAction("🅰️ 字体", self.cf)
        m.addAction("🔒 锁定" if not self.locked else "🔒 解锁", self.tl); m.addAction("❌ 关闭", self.hide)
        m.exec_(p)
    def cc(self): 
        c=QColorDialog.getColor(self.col, self); 
        if c.isValid(): self.col=c; self.upd()
    def cf(self):
        f,ok=QFontDialog.getFont(self.font, self)
        if ok: self.font=f; self.upd()
    def tl(self): self.locked=not self.locked

# --- 主程序 ---
class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 2025")
        self.resize(1180, 780); self.setStyleSheet(STYLESHEET)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if os.name=='nt':
            try: enable_acrylic(int(self.winId()))
            except: pass

        self.music_folder=""; self.current_collection=""; self.collections=[]
        self.playlist=[]; self.history=[]; self.lyrics=[]
        self.curr_idx=-1; self.offset=0.0; self.saved_offsets={}; self.metadata={}
        self.mode=0; self.rate=1.0; self.vol=80; self.slider_down=False

        self.player=QMediaPlayer()
        self.player.positionChanged.connect(self.on_pos); self.player.durationChanged.connect(self.on_dur)
        self.player.stateChanged.connect(self.on_state); self.player.mediaStatusChanged.connect(self.on_status)
        self.player.error.connect(lambda: QTimer.singleShot(1000, self.play_next))
        self.player.setVolume(self.vol)

        self.desk_lrc=DesktopLyricWindow()
        self.init_ui()
        self.load_conf()

    def init_ui(self):
        cw=QWidget(); self.setCentralWidget(cw); main=QHBoxLayout(cw); main.setContentsMargins(0,0,0,0); main.setSpacing(0)
        
        # Sidebar
        sb=QFrame(); sb.setObjectName("Sidebar"); sb.setFixedWidth(260)
        sl=QVBoxLayout(sb); sl.setContentsMargins(0,0,0,0); sl.setSpacing(0)
        sl.addWidget(QLabel("🎵 汽水音乐", objectName="Logo"))
        
        bc=QWidget(); bl=QVBoxLayout(bc); bl.setSpacing(8); bl.setContentsMargins(15,0,15,0)
        b1=QPushButton("📺 B站下载"); b1.setObjectName("DownloadBtn"); b1.clicked.connect(self.dl_bili); bl.addWidget(b1)
        b2=QPushButton("🔄 刷新库"); b2.setProperty("NavBtn",True); b2.clicked.connect(self.full_scan); bl.addWidget(b2)
        sl.addWidget(bc)
        
        sl.addWidget(QLabel("  合集列表", objectName="SectionTitle"))
        self.nav=QListWidget(); self.nav.setStyleSheet("background:transparent;border:none;")
        self.nav.itemClicked.connect(self.switch_coll)
        sl.addWidget(self.nav)
        
        sl.addStretch()
        bf=QPushButton("📂 根目录"); bf.setProperty("NavBtn",True); bf.clicked.connect(self.sel_folder); sl.addWidget(bf)
        bd=QPushButton("🎤 桌面歌词"); bd.setProperty("NavBtn",True); bd.clicked.connect(self.tog_lrc); sl.addWidget(bd)
        main.addWidget(sb)

        # Content
        rp=QWidget(); rl=QVBoxLayout(rp); rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)
        
        self.stack=QStackedWidget()
        
        # Page 1: List
        p1=QWidget(); p1l=QVBoxLayout(p1); p1l.setContentsMargins(0,0,0,0)
        head=QFrame(); head.setFixedHeight(60); head.setStyleSheet("background:rgba(255,255,255,0.6); border-bottom:1px solid #eee;")
        hl=QHBoxLayout(head); hl.setContentsMargins(25,0,25,0)
        self.lbl_title=QLabel("全部音乐"); self.lbl_title.setStyleSheet("font-size:20px;font-weight:bold;")
        self.search=QLineEdit(); self.search.setPlaceholderText("🔍 搜索..."); self.search.setFixedWidth(200)
        self.search.setStyleSheet("border-radius:15px; padding:5px 10px; border:1px solid #ddd;")
        self.search.textChanged.connect(self.filter_list)
        hl.addWidget(self.lbl_title); hl.addStretch(); hl.addWidget(self.search); p1l.addWidget(head)
        
        self.table=QTableWidget(); self.table.setColumnCount(4); self.table.setHorizontalHeaderLabels(["标题","歌手","专辑","时长"])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False); self.table.setShowGrid(False); self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.itemDoubleClicked.connect(self.play_item); self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_menu)
        p1l.addWidget(self.table)
        self.stack.addWidget(p1)
        
        # Page 2: Lyrics
        p2=QWidget(); p2.setObjectName("LyricsPage"); p2l=QHBoxLayout(p2); p2l.setContentsMargins(40,40,40,40)
        lb=QVBoxLayout(); lb.setAlignment(Qt.AlignCenter)
        cover=QLabel(); cover.setFixedSize(350,350); cover.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #a1c4fd,stop:1 #c2e9fb); border-radius:20px;")
        self.l_t=QLabel("--"); self.l_t.setStyleSheet("font-size:24px;font-weight:bold;margin-top:20px;")
        self.l_a=QLabel("--"); self.l_a.setStyleSheet("color:#666;")
        bb=QPushButton("﹀ 返回列表"); bb.setFlat(True); bb.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        lb.addWidget(cover); lb.addWidget(self.l_t); lb.addWidget(self.l_a); lb.addWidget(bb); p2l.addLayout(lb)
        
        self.big_lrc=QListWidget(); self.big_lrc.setObjectName("BigLyric"); self.big_lrc.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        p2l.addWidget(self.big_lrc, stretch=1)
        self.stack.addWidget(p2)
        
        rl.addWidget(self.stack)
        
        # Player Bar
        bar=QFrame(); bar.setObjectName("PlayerBar"); bar.setFixedHeight(90)
        bl=QHBoxLayout(bar); bl.setContentsMargins(20,5,20,5)
        
        # Mini Info
        mi=QWidget(); mil=QHBoxLayout(mi); mil.setContentsMargins(0,0,0,0)
        mc=QPushButton(); mc.setFixedSize(50,50); mc.setStyleSheet("background:#ddd;border-radius:8px;")
        mc.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        mt=QWidget(); mtl=QVBoxLayout(mt); mtl.setContentsMargins(5,0,0,0); mtl.setSpacing(2)
        self.mt_t=QLabel("未播放"); self.mt_t.setStyleSheet("font-weight:bold;")
        self.mt_a=QLabel("--"); self.mt_a.setStyleSheet("color:#666;font-size:12px;")
        mtl.addWidget(self.mt_t); mtl.addWidget(self.mt_a); mtl.addStretch()
        mil.addWidget(mc); mil.addWidget(mt); bl.addWidget(mi, stretch=2)
        
        # Controls
        cc=QWidget(); ccl=QVBoxLayout(cc); ccl.setContentsMargins(0,5,0,5)
        cbtns=QHBoxLayout(); cbtns.setSpacing(15)
        self.b_m=QPushButton("🔁"); self.b_m.setProperty("CtrlBtn",True); self.b_m.clicked.connect(self.tog_mode)
        bp=QPushButton("⏮"); bp.setProperty("CtrlBtn",True); bp.clicked.connect(self.play_prev)
        self.b_p=QPushButton("▶"); self.b_p.setObjectName("PlayBtn"); self.b_p.clicked.connect(self.tog_play)
        bn=QPushButton("⏭"); bn.setProperty("CtrlBtn",True); bn.clicked.connect(self.play_next)
        cbtns.addStretch(); cbtns.addWidget(self.b_m); cbtns.addWidget(bp); cbtns.addWidget(self.b_p); cbtns.addWidget(bn); cbtns.addStretch()
        
        prog=QHBoxLayout(); self.lp=QLabel("00:00"); self.lt=QLabel("00:00")
        self.sl=QSlider(Qt.Horizontal); self.sl.sliderPressed.connect(self.sp); self.sl.sliderReleased.connect(self.sr); self.sl.valueChanged.connect(self.sm)
        prog.addWidget(self.lp); prog.addWidget(self.sl); prog.addWidget(self.lt)
        ccl.addLayout(cbtns); ccl.addLayout(prog); bl.addWidget(cc, stretch=4)
        
        # Right
        rc=QHBoxLayout(); rc.setAlignment(Qt.AlignRight)
        vs=QSlider(Qt.Horizontal); vs.setRange(0,100); vs.setValue(80); vs.setFixedWidth(80); vs.valueChanged.connect(lambda v: self.player.setVolume(v))
        rc.addWidget(QLabel("🔈")); rc.addWidget(vs)
        bl.addLayout(rc, stretch=2)
        
        rl.addWidget(bar); main.addWidget(rp)

    # --- 逻辑 ---
    def full_scan(self):
        if not self.music_folder: return
        self.collections = []
        ext = ('.mp3','.wav','.m4a','.flac','.mp4')
        # 扫描一级子文件夹，且只有 >1 首歌的才算合集
        for d in os.listdir(self.music_folder):
            fd = os.path.join(self.music_folder, d)
            if os.path.isdir(fd):
                fs = [f for f in os.listdir(fd) if f.lower().endswith(ext)]
                if len(fs) > 1: self.collections.append(d)
        
        self.nav.clear(); self.nav.addItem("💿  全部歌曲"); self.nav.addItem("🕒  最近播放")
        for c in self.collections: self.nav.addItem(f"📁  {c}")
        if not self.current_collection: self.load_list()

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
            for s in self.history: self.add_row(s)
            return
        
        if self.current_collection: ds=[os.path.join(self.music_folder, self.current_collection)]
        else:
            ds=[self.music_folder]
            for c in self.collections: ds.append(os.path.join(self.music_folder, c))
            
        for d in ds:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.lower().endswith(ext):
                        fp = os.path.abspath(os.path.join(d,f))
                        # 排除单曲文件夹内的文件（如果不是在浏览具体合集时）
                        if not self.current_collection and os.path.dirname(fp) != self.music_folder:
                             # 检查该文件夹是否是合集，如果不是合集（即单曲文件夹），则显示
                             pass 

                        meta = self.metadata.get(f, {})
                        self.add_row({"path":fp, "name":f, "artist":meta.get("a","未知"), "album":meta.get("b","未知")})
        self._all = self.playlist.copy()

    def add_row(self, s):
        self.playlist.append(s)
        r = self.table.rowCount(); self.table.insertRow(r)
        self.table.setItem(r,0,QTableWidgetItem(os.path.splitext(s["name"])[0]))
        self.table.setItem(r,1,QTableWidgetItem(s["artist"]))
        self.table.setItem(r,2,QTableWidgetItem(s["album"]))
        self.table.setItem(r,3,QTableWidgetItem("-"))

    def filter_list(self, txt):
        t = txt.lower()
        for i in range(self.table.rowCount()):
            match = False
            for c in range(3):
                if self.table.item(i,c) and t in self.table.item(i,c).text().lower(): match=True
            self.table.setRowHidden(i, not match)

    # 播放
    def play_item(self, item): self.play(item.row())
    def play(self, idx):
        if not self.playlist: return
        self.current_index = idx
        s = self.playlist[idx]
        
        if s not in self.history: self.history.insert(0,s); self.save_hist()
        
        try:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(s["path"])))
            self.player.setPlaybackRate(self.rate); self.player.play()
            self.b_p.setText("⏸")
            
            # UI
            nm = os.path.splitext(s["name"])[0]
            self.mt_t.setText(nm); self.mt_a.setText(s["artist"])
            self.l_t.setText(nm); self.l_a.setText(s["artist"])
            
            # 歌词
            self.offset = self.saved_offsets.get(s["name"], 0.0)
            lrc = os.path.splitext(s["path"])[0]+".lrc"
            if os.path.exists(lrc): 
                with open(lrc,'r',encoding='utf-8',errors='ignore') as f: self.parse_lrc(f.read())
            else:
                self.big_lrc.clear(); self.big_lrc.addItem("搜索中...")
                self.sw = LyricListSearchWorker(nm)
                self.sw.search_finished.connect(self.auto_lrc)
                self.sw.start()
        except: pass

    def auto_lrc(self, res):
        if res:
            best = res[0] # 默认第一个
            # 智能匹配逻辑：文件名完全包含
            n = self.playlist[self.current_index]["name"]
            for r in res:
                if r['name'] in n or n in r['name']: best=r; break
            
            lp = os.path.splitext(self.playlist[self.current_index]["path"])[0]+".lrc"
            self.ld = LyricDownloader(best['id'], lp)
            self.ld.finished_signal.connect(self.parse_lrc)
            self.ld.start()
        else: self.big_lrc.clear(); self.big_lrc.addItem("无歌词")

    def parse_lrc(self, txt):
        self.lyrics = []; self.big_lrc.clear()
        for l in txt.splitlines():
            m = re.match(r'\[(\d+):(\d+)\.(\d+)\](.*)', l)
            if m:
                t = int(m.group(1))*60 + int(m.group(2)) + int(m.group(3))/100
                tx = m.group(4).strip()
                if tx: self.lyrics.append({"t":t,"txt":tx}); self.big_lrc.addItem(tx)

    # 批量移动修复
    def batch_move_dialog(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return QMessageBox.warning(self,"提示","请先选择歌曲")
        ls = ["根目录"] + self.collections
        t, ok = QInputDialog.getItem(self, "移动", "目标:", ls, 0, False)
        if ok: self.do_move(rows, "" if t=="根目录" else t)

    def do_move(self, rows, target):
        self.player.setMedia(QMediaContent()) # 关键修复：释放文件锁
        tp = os.path.join(self.music_folder, target) if target else self.music_folder
        if not os.path.exists(tp): os.makedirs(tp)
        
        # 先收集路径，防止循环中playlist变动
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

    def show_menu(self, p):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return
        m = QMenu()
        
        mv = m.addMenu("📂 批量移动到")
        mv.addAction("根目录", lambda: self.do_move(rows, ""))
        for c in self.collections: mv.addAction(c, lambda _,t=c: self.do_move(rows, t))
        
        m.addAction("🔠 批量重命名", self.do_rename)
        if len(rows)==1:
            i=rows[0]
            m.addAction("🔐 绑定歌词 (整理)", lambda: self.do_bind(i))
            m.addAction("🔍 手动搜歌词", lambda: self.do_manual_lrc(i))
            m.addAction("❌ 解绑歌词", lambda: self.do_del_lrc(i))
        m.addAction("🗑️ 删除", lambda: self.do_del(rows))
        m.exec_(self.table.mapToGlobal(p))

    def do_rename(self):
        if not self.playlist: return
        self.player.setMedia(QMediaContent()) # 释放锁
        d = BatchRenameDialog(self.playlist, self)
        if d.exec_()==QDialog.Accepted:
            mod, p, idxs = d.get_data()
            # 收集目标
            ts = [self.playlist[i] for i in idxs if i<len(self.playlist)]
            for s in ts:
                old=s["path"]; base,ext=os.path.splitext(s["name"]); nb=base
                if mod=="rep" and p[0] in base: nb=base.replace(p[0],p[1])
                elif mod=="trim":
                    if p[0]>0: nb=nb[p[0]:]
                    if p[1]>0: nb=nb[:-p[1]]
                nn = nb.strip()+ext; np=os.path.join(os.path.dirname(old), nn)
                if np!=old:
                    try:
                        os.rename(old, np)
                        l=os.path.splitext(old)[0]+".lrc"
                        if os.path.exists(l): os.rename(l, os.path.splitext(np)[0]+".lrc")
                    except:pass
            self.full_scan()

    # B站下载
    def dl_bili(self):
        if not self.music_folder: return QMessageBox.warning(self,"","请先设置目录")
        u,ok=QInputDialog.getText(self,"下载","链接:")
        if ok and u:
            p=1
            m=re.search(r'[?&]p=(\d+)', u)
            if m: p=int(m.group(1))
            d=DownloadDialog(self, p, self.collections)
            if d.exec_()==QDialog.Accepted:
                mod,f,a,b = d.get_data()
                pt = os.path.join(self.music_folder, f) if f else self.music_folder
                self.tmp_meta = (a,b)
                self.lbl_title.setText("⏳ 下载中...")
                self.dl=BilibiliDownloader(u, pt, mod, p)
                self.dl.progress_signal.connect(lambda s: self.lbl_title.setText(s))
                self.dl.finished_signal.connect(self.on_dl_ok)
                self.dl.start()
    def on_dl_ok(self, p, _):
        a,b=self.tmp_meta
        if a or b:
            for f in os.listdir(p):
                if f not in self.metadata: self.metadata[f]={"a":a or "未知", "b":b or "未知"}
            self.save_meta()
        self.full_scan(); self.lbl_title.setText("下载完成")

    def do_bind(self, idx):
        self.player.setMedia(QMediaContent())
        s = self.playlist[idx]; p=s["path"]; n=os.path.splitext(s["name"])[0]
        f, _ = QFileDialog.getOpenFileName(self, "选词", "", "LRC (*.lrc)")
        if f:
            d = os.path.join(os.path.dirname(p), n)
            try:
                if not os.path.exists(d): os.makedirs(d)
                shutil.move(p, os.path.join(d, s["name"]))
                shutil.copy(f, os.path.join(d, n+".lrc"))
                self.full_scan(); QMessageBox.information(self,"ok","ok")
            except:pass

    def do_manual_lrc(self, idx):
        s = self.playlist[idx]; dur=self.player.duration() if self.current_index==idx else 0
        d = LyricSearchDialog(os.path.splitext(s["name"])[0], dur, self)
        if d.exec_()==QDialog.Accepted and d.result_id:
            lp = os.path.splitext(s["path"])[0]+".lrc"
            self.ld = LyricDownloader(d.result_id, lp)
            self.ld.finished_signal.connect(lambda c: self.on_manual_ok(c, idx))
            self.ld.start()
    def on_manual_ok(self, c, i):
        if self.current_index==i: self.parse_lrc(c)
        QMessageBox.information(self,"ok","已应用")

    def do_del(self, rows):
        if QMessageBox.Yes!=QMessageBox.question(self,"删","确认删除?"): return
        self.player.setMedia(QMediaContent())
        for i in rows:
            if i<len(self.playlist):
                try:
                    p=self.playlist[i]["path"]; os.remove(p)
                    l=os.path.splitext(p)[0]+".lrc"
                    if os.path.exists(l): os.remove(l)
                except:pass
        self.full_scan()
    def do_del_lrc(self, idx):
        p=os.path.splitext(self.playlist[idx]["path"])[0]+".lrc"
        if os.path.exists(p): os.remove(p); self.parse_lrc(""); QMessageBox.information(self,"ok","已删")

    # 基础
    def on_pos(self, p):
        if not self.slider_down: self.sl.setValue(p)
        self.lp.setText(ms_to_str(p))
        t = p/1000 + self.offset
        if self.lyrics:
            idx = -1
            for i,l in enumerate(self.lyrics):
                if t>=l["t"]: idx=i
                else: break
            if idx!=-1:
                self.big_lrc.setCurrentRow(idx)
                self.big_lrc.scrollToItem(self.big_lrc.item(idx), QAbstractItemView.PositionAtCenter)
                pr=self.lyrics[idx-1]["txt"] if idx>0 else ""
                cu=self.lyrics[idx]["txt"]
                ne=self.lyrics[idx+1]["txt"] if idx<len(self.lyrics)-1 else ""
                self.desktop_lyric.set_text(pr,cu,ne)
    def sp(self): self.slider_down=True
    def sr(self): self.slider_down=False; self.player.setPosition(self.sl.value())
    def sm(self, v): 
        if self.slider_down: self.lp.setText(ms_to_str(v))
    def on_dur(self, d): self.sl.setRange(0,d); self.lt.setText(ms_to_str(d))
    
    def tog_play(self): 
        if self.player.state()==QMediaPlayer.PlayingState: self.player.pause()
        else: self.player.play()
    def tog_mode(self): self.mode=(self.mode+1)%3; self.b_m.setText(["🔁","🔂","🔀"][self.mode])
    def tog_rate(self):
        rs=[1.0,1.25,1.5,2.0,0.5]; i=rs.index(self.rate) if self.rate in rs else 0
        self.rate=rs[(i+1)%5]; self.player.setPlaybackRate(self.rate); self.b_rate.setText(f"{self.rate}x")
    def play_next(self):
        if not self.playlist: return
        n = random.randint(0,len(self.playlist)-1) if self.mode==2 else (self.current_index+1)%len(self.playlist)
        self.play(n)
    def play_prev(self):
        if not self.playlist: return
        p = random.randint(0,len(self.playlist)-1) if self.mode==2 else (self.current_index-1)%len(self.playlist)
        self.play(p)
    def on_state_changed(self, s): self.b_pp.setText("⏸" if s==QMediaPlayer.PlayingState else "▶")
    def on_media_status(self, s): 
        if s==QMediaPlayer.EndOfMedia: 
            if self.mode==1: self.player.play() 
            else: self.play_next()
    def new_coll(self):
        n,ok=QInputDialog.getText(self,"新建","名称:")
        if ok and n: os.makedirs(os.path.join(self.music_folder, sanitize_filename(n)), exist_ok=True); self.full_scan()
    def sel_folder(self):
        f=QFileDialog.getExistingDirectory(self,"选目录"); 
        if f: self.music_folder=f; self.full_scan(); self.save_conf()
    def tog_lrc(self): 
        if self.desktop_lyric.isVisible(): self.desktop_lyric.hide()
        else: self.desktop_lyric.show()
    
    def load_conf(self):
        if os.path.exists(CONFIG_FILE):
            try: 
                with open(CONFIG_FILE,'r') as f: d=json.load(f); self.music_folder=d.get("folder",""); self.full_scan()
            except:pass
        if os.path.exists(METADATA_FILE):
            try: with open(METADATA_FILE,'r') as f: self.metadata=json.load(f)
            except:pass
        if os.path.exists(HISTORY_FILE):
            try: with open(HISTORY_FILE,'r') as f: self.history=json.load(f)
            except:pass
        if os.path.exists(OFFSET_FILE):
            try: with open(OFFSET_FILE,'r') as f: self.saved_offsets=json.load(f)
            except:pass
    def save_conf(self): with open(CONFIG_FILE,'w') as f: json.dump({"folder":self.music_folder},f)
    def save_meta(self): with open(METADATA_FILE,'w') as f: json.dump(self.metadata,f)
    def save_hist(self): with open(HISTORY_FILE,'w') as f: json.dump(self.history,f)
    def save_off(self): with open(OFFSET_FILE,'w') as f: json.dump(self.saved_offsets,f)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(app_path, 'PyQt5', 'Qt', 'plugins')
        QCoreApplication.addLibraryPath(os.path.join(app_path, 'PyQt5', 'Qt', 'plugins'))
    app = QApplication(sys.argv)
    f = QFont("Microsoft YaHei", 10); app.setFont(f)
    w = SodaPlayer(); w.show(); sys.exit(app.exec_())

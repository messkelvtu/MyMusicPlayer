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
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QFileDialog, QFrame, QAbstractItemView, QCheckBox,
                             QGraphicsDropShadowEffect, QInputDialog, QMessageBox, 
                             QFontDialog, QMenu, QAction, QSlider, QDialog, QRadioButton, 
                             QComboBox, QLineEdit, QTabWidget, QSpinBox, QColorDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize, QCoreApplication, QTimer
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

# --- 深色高级 UI 样式 (复刻附件2) ---
STYLESHEET = """
/* 全局深色背景 */
QMainWindow { background-color: #1E1B18; }
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; color: #E0E0E0; }

/* 侧边栏 - 深褐/黑 */
QFrame#Sidebar {
    background-color: #2D2824;
    border-right: 1px solid #3A3530;
}

/* 侧边栏按钮 - 垂直布局风格 */
QPushButton.NavBtn {
    background: transparent;
    border: none;
    text-align: left;
    padding: 15px 20px;
    font-size: 15px;
    color: #A0A0A0;
    border-radius: 8px;
    margin: 4px 10px;
}
QPushButton.NavBtn:hover {
    background-color: #3A3530;
    color: #FFFFFF;
}
QPushButton.NavBtn:checked {
    background-color: #3A3530;
    color: #D4AF37; /* 金色高亮 */
    border-left: 4px solid #D4AF37;
}

/* B站下载按钮 - 特殊样式 */
QPushButton#DownloadBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D4AF37, stop:1 #F2D06B);
    color: #2D2824;
    font-weight: bold;
    border-radius: 20px;
    text-align: center;
    margin: 20px;
    padding: 10px;
}
QPushButton#DownloadBtn:hover {
    margin-top: 19px; /* 微动效 */
}

/* 列表/表格 - 深色卡片 */
QTableWidget {
    background-color: transparent;
    border: none;
    outline: none;
    gridline-color: #3A3530;
}
QHeaderView::section {
    background-color: transparent;
    border: none;
    border-bottom: 1px solid #3A3530;
    padding: 8px;
    font-weight: bold;
    color: #888;
}
QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #2A2520;
}
QTableWidget::item:selected {
    background-color: #3A3530;
    color: #D4AF37;
}

/* 底部播放栏 - 悬浮深色 */
QFrame#PlayerBar {
    background-color: #25211E;
    border-top: 1px solid #3A3530;
}

/* 播放按钮 - 金色圆形 */
QPushButton#PlayBtn { 
    background-color: #D4AF37; 
    color: #2D2824; 
    border-radius: 25px; 
    font-size: 20px; 
    min-width: 50px; 
    min-height: 50px;
    border: none;
}
QPushButton#PlayBtn:hover { 
    background-color: #F2D06B; 
    transform: scale(1.05); 
}

/* 控制图标 */
QPushButton.CtrlBtn { 
    background: transparent; 
    border: none; 
    font-size: 20px; 
    color: #A0A0A0; 
}
QPushButton.CtrlBtn:hover { color: #D4AF37; }

/* 进度条 - 细长 */
QSlider::groove:horizontal { 
    height: 2px; 
    background: #4A4540; 
}
QSlider::handle:horizontal {
    background: #D4AF37; 
    width: 10px; 
    height: 10px; 
    margin: -4px 0; 
    border-radius: 5px;
}
QSlider::sub-page:horizontal { 
    background: #D4AF37; 
}

/* 标题文字 */
QLabel#MainTitle { font-size: 24px; font-weight: bold; color: #D4AF37; margin: 20px; }
QLabel#SubTitle { font-size: 16px; font-weight: bold; color: #FFFFFF; margin: 10px 20px; }

/* 歌词面板 */
QListWidget#LyricPanel {
    background: transparent;
    border: none;
    color: #888;
    font-size: 14px;
    outline: none;
}
QListWidget#LyricPanel::item:selected {
    color: #D4AF37;
    font-size: 16px;
    font-weight: bold;
    background: transparent;
}
"""

# --- 辅助函数 ---
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def ms_to_str(ms):
    s = ms // 1000
    return f"{s//60:02}:{s%60:02}"

# --- 功能线程 (保持不变) ---
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
        btn_bind = QPushButton("下载并绑定"); btn_bind.clicked.connect(self.confirm_bind); l.addWidget(btn_bind)
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

class BatchRenameDialog(QDialog):
    def __init__(self, pl, parent=None):
        super().__init__(parent); self.resize(500,500); self.pl=pl; self.si=[]
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
    def ok(self):
        self.si=[i for i in range(self.lst.count()) if self.lst.item(i).checkState()==Qt.Checked]
        self.accept()
    def get_data(self):
        if self.tab.currentIndex()==0: return "rep", (self.f.text(),self.r.text()), self.si
        else: return "trim", (self.sh.value(),self.st.value()), self.si

class BatchInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("编辑信息"); self.resize(300,200); l=QVBoxLayout(self)
        self.ca=QCheckBox("歌手"); self.ia=QLineEdit(); self.cb=QCheckBox("专辑"); self.ib=QLineEdit()
        l.addWidget(self.ca); l.addWidget(self.ia); l.addWidget(self.cb); l.addWidget(self.ib)
        b=QPushButton("保存"); b.clicked.connect(self.accept); l.addWidget(b)
    def get_data(self): return (self.ia.text() if self.ca.isChecked() else None, self.ib.text() if self.cb.isChecked() else None)

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

# --- 核心主程序 ---
class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 2025")
        self.resize(1200, 800)
        self.setStyleSheet(STYLESHEET)

        self.music_folder = ""; self.current_collection = ""; self.collections = []
        self.playlist = []; self.history = []; self.lyrics = []
        self.current_index = -1; self.offset = 0.0; self.saved_offsets = {}; self.metadata = {}
        self.mode = 0; self.rate = 1.0; self.volume = 80; self.is_slider_pressed = False

        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.on_pos_changed)
        self.player.durationChanged.connect(self.on_dur_changed)
        self.player.stateChanged.connect(self.on_state_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.error.connect(self.handle_err); self.player.setVolume(self.volume)
        
        self.desktop_lyric = DesktopLyricWindow(); self.desktop_lyric.show()
        self.init_ui(); self.load_conf()

    def init_ui(self):
        cw = QWidget(); self.setCentralWidget(cw); lay = QHBoxLayout(cw); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        
        # === 侧边栏 ===
        sb = QFrame(); sb.setObjectName("Sidebar"); sb.setFixedWidth(260); sl = QVBoxLayout(sb)
        sl.setSpacing(5); sl.setContentsMargins(0,0,0,0)
        
        sl.addWidget(QLabel("🎵 汽水音乐", objectName="Logo"))
        
        b_dl = QPushButton("☁️ B站下载"); b_dl.setObjectName("DownloadBtn"); b_dl.clicked.connect(self.dl_bili)
        sl.addWidget(b_dl)
        
        nav_box = QWidget(); nl = QVBoxLayout(nav_box); nl.setSpacing(2)
        self.btn_all = QPushButton("💿 全部音乐"); self.btn_all.setProperty("NavBtn",True); self.btn_all.setCheckable(True); self.btn_all.clicked.connect(lambda: self.switch_coll(None))
        self.btn_hist = QPushButton("🕒 最近播放"); self.btn_hist.setProperty("NavBtn",True); self.btn_hist.setCheckable(True); self.btn_hist.clicked.connect(lambda: self.switch_coll("HISTORY"))
        nl.addWidget(self.btn_all); nl.addWidget(self.btn_hist); sl.addWidget(nav_box)
        
        sl.addWidget(QLabel("歌单宝藏库", objectName="SectionTitle"))
        self.nav = QListWidget(); self.nav.setStyleSheet("background:transparent; border:none; margin:0 10px;")
        self.nav.itemClicked.connect(self.on_coll_click)
        sl.addWidget(self.nav)
        
        sl.addStretch()
        bf = QPushButton("📂 管理根目录"); bf.setProperty("NavBtn",True); bf.clicked.connect(self.sel_folder); sl.addWidget(bf)
        bl = QPushButton("🎤 桌面歌词"); bl.setProperty("NavBtn",True); bl.clicked.connect(self.tog_desk_lrc); sl.addWidget(bl)
        lay.addWidget(sb)

        # === 右侧区域 ===
        rp = QWidget(); rl = QVBoxLayout(rp); rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)
        
        # Header
        hd = QWidget(); hl = QHBoxLayout(hd); hl.setContentsMargins(30,20,30,10)
        self.lb_title = QLabel("全部音乐"); self.lb_title.setStyleSheet("font-size:28px; font-weight:bold; color:#D4AF37;")
        self.search = QLineEdit(); self.search.setPlaceholderText("🔍 搜索歌曲..."); self.search.setFixedWidth(250)
        self.search.setStyleSheet("border-radius:18px; padding:8px 15px; border:1px solid #3A3530; background:#25211E; color:#DDD;")
        self.search.textChanged.connect(self.filter_list)
        hl.addWidget(self.lb_title); hl.addStretch(); hl.addWidget(self.search); rl.addWidget(hd)
        
        # Content (Table + Lyric)
        cont = QWidget(); cl = QHBoxLayout(cont); cl.setContentsMargins(20,0,20,0)
        
        self.table = QTableWidget(); self.table.setColumnCount(4); self.table.setHorizontalHeaderLabels(["歌曲","歌手","专辑","时长"])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False); self.table.setShowGrid(False); self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.itemDoubleClicked.connect(self.play_sel); self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_menu)
        cl.addWidget(self.table, stretch=6)
        
        self.lrc_p = QListWidget(); self.lrc_p.setObjectName("LyricPanel"); self.lrc_p.setFocusPolicy(Qt.NoFocus)
        self.lrc_p.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cl.addWidget(self.lrc_p, stretch=3)
        rl.addWidget(cont)

        # Player Bar
        bar = QFrame(); bar.setObjectName("PlayerBar"); bar.setFixedHeight(100); bl = QVBoxLayout(bar)
        
        prg = QHBoxLayout(); self.lc = QLabel("00:00"); self.lt = QLabel("00:00"); self.sl = QSlider(Qt.Horizontal)
        self.sl.sliderPressed.connect(self.sp); self.sl.sliderReleased.connect(self.sr); self.sl.valueChanged.connect(self.sm)
        prg.addWidget(self.lc); prg.addWidget(self.sl); prg.addWidget(self.lt); bl.addLayout(prg)
        
        ctr = QHBoxLayout()
        self.bm = QPushButton("🔁"); self.bm.setProperty("CtrlBtn",True); self.bm.clicked.connect(self.tm)
        bp = QPushButton("⏮"); bp.setProperty("CtrlBtn",True); bp.clicked.connect(self.pp)
        self.bp = QPushButton("▶"); self.bp.setObjectName("PlayBtn"); self.bp.clicked.connect(self.tp)
        bn = QPushButton("⏭"); bn.setProperty("CtrlBtn",True); bn.clicked.connect(self.pn)
        
        # Offset btns
        bo1 = QPushButton("-0.5s"); bo1.setProperty("OffsetBtn",True); bo1.clicked.connect(lambda: self.ao(-0.5))
        bo2 = QPushButton("+0.5s"); bo2.setProperty("OffsetBtn",True); bo2.clicked.connect(lambda: self.ao(0.5))
        
        ctr.addStretch(); ctr.addWidget(self.bm); ctr.addSpacing(20); ctr.addWidget(bp); ctr.addWidget(self.bp)
        ctr.addWidget(bn); ctr.addSpacing(20); ctr.addWidget(bo1); ctr.addWidget(bo2); ctr.addStretch()
        bl.addLayout(ctr)
        
        rl.addWidget(bar); lay.addWidget(rp)

    # Logic
    def full_scan(self):
        if not self.music_folder: return
        self.collections = []
        ext = ('.mp3','.wav','.m4a','.flac','.mp4')
        for d in os.listdir(self.music_folder):
            fd = os.path.join(self.music_folder, d)
            if os.path.isdir(fd):
                fs = [f for f in os.listdir(fd) if f.lower().endswith(ext)]
                if len(fs) > 1: self.collections.append(d)
        self.nav.clear()
        for c in self.collections: 
            it = QListWidgetItem(f"{c}"); it.setData(Qt.UserRole, c)
            self.nav.addItem(it)
        self.switch_coll(None)

    def on_coll_click(self, item): self.switch_coll(item.data(Qt.UserRole))
    
    def switch_coll(self, coll_name):
        self.btn_all.setChecked(coll_name is None)
        self.btn_hist.setChecked(coll_name == "HISTORY")
        
        if coll_name == "HISTORY":
            self.current_collection = "HISTORY"
            self.lb_title.setText("最近播放")
        elif coll_name:
            self.current_collection = coll_name
            self.lb_title.setText(coll_name)
        else:
            self.current_collection = ""
            self.lb_title.setText("全部音乐")
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
        self.table.setItem(r,3,QTableWidgetItem("-"))

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
        self.current_index = idx; s = self.playlist[idx]
        if s not in self.history: self.history.insert(0,s); self.save_hist()
        try:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(s["path"])))
            self.player.setPlaybackRate(self.rate); self.player.play()
            self.bp.setText("⏸")
            
            self.offset = self.saved_offsets.get(s["name"], 0.0)
            
            lp = os.path.splitext(s["path"])[0]+".lrc"
            if os.path.exists(lp):
                with open(lp,'r',encoding='utf-8',errors='ignore') as f: self.parse_lrc(f.read())
            else:
                self.lrc_p.clear(); self.lrc_p.addItem("搜索歌词...")
                self.sw = LyricListSearchWorker(os.path.splitext(s["name"])[0])
                self.sw.search_finished.connect(self.auto_lrc)
                self.sw.start()
        except: pass

    def auto_lrc(self, res):
        if res:
            lp = os.path.splitext(self.playlist[self.current_index]["path"])[0]+".lrc"
            self.ld = LyricDownloader(res[0]['id'], lp)
            self.ld.finished_signal.connect(self.parse_lrc)
            self.ld.start()
        else: self.lrc_p.clear(); self.lrc_p.addItem("无歌词")

    def parse_lrc(self, txt):
        self.lyrics = []; self.lrc_p.clear()
        for l in txt.splitlines():
            m = re.match(r'\[(\d+):(\d+)\.(\d+)\](.*)', l)
            if m:
                t = int(m.group(1))*60 + int(m.group(2)) + int(m.group(3))/100
                tx = m.group(4).strip()
                if tx: self.lyrics.append({"t":t, "txt":tx}); self.lrc_p.addItem(tx)

    def show_menu(self, p):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return
        m = QMenu()
        
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

    # --- 修复后的文件操作 (先释放player) ---
    def release_player(self):
        self.player.setMedia(QMediaContent()) # 核心修复
        
    def do_move(self, rows, target):
        self.release_player()
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
        self.release_player()
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
        self.release_player()
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

    def do_del_lrc(self, idx):
        p = os.path.splitext(self.playlist[idx]["path"])[0]+".lrc"
        if os.path.exists(p): os.remove(p); QMessageBox.information(self,"OK","已删除")
        if self.current_index==idx: self.parse_lrc("")

    def do_del(self, rows):
        if QMessageBox.Yes!=QMessageBox.question(self,"确","删?"): return
        self.release_player()
        for i in rows:
            if i<len(self.playlist):
                try:
                    p=self.playlist[i]["path"]; os.remove(p)
                    l=os.path.splitext(p)[0]+".lrc"
                    if os.path.exists(l): os.remove(l)
                except:pass
        self.full_scan()

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

    def ao(self, v):
        self.offset+=v
        if self.current_index>=0: 
            self.saved_offsets[self.playlist[self.current_index]["name"]]=self.offset
            self.save_off()

    # ... (其他播放控制逻辑保持不变)
    def sel_folder(self):
        f=QFileDialog.getExistingDirectory(self,"选目录")
        if f: self.music_folder=f; self.full_scan(); self.save_config()
    def tog_desk_lrc(self): 
        if self.desktop_lyric.isVisible(): self.desktop_lyric.hide()
        else: self.desktop_lyric.show()
    def sp(self): self.is_slider_pressed=True
    def sr(self): self.is_slider_pressed=False; self.player.setPosition(self.sl.value())
    def sm(self, v): 
        if self.is_slider_pressed: self.lc.setText(ms_to_str(v))
    def on_dur_changed(self, d): self.sl.setRange(0, d); self.lt.setText(ms_to_str(d))
    def on_pos_changed(self, p):
        if not self.is_slider_pressed: self.sl.setValue(p)
        self.lc.setText(ms_to_str(p))
        t = p/1000 + self.offset
        if self.lyrics:
            idx = -1
            for i, l in enumerate(self.lyrics):
                if t >= l["t"]: idx = i
                else: break
            if idx != -1:
                self.lrc_p.setCurrentRow(idx); self.lrc_p.scrollToItem(self.lrc_p.item(idx), QAbstractItemView.PositionAtCenter)
                pr=self.lyrics[idx-1]["txt"] if idx>0 else ""; cu=self.lyrics[idx]["txt"]; ne=self.lyrics[idx+1]["txt"] if idx<len(self.lyrics)-1 else ""
                self.desktop_lyric.set_lyrics(pr, cu, ne)
    def on_state_changed(self, s): self.b_pp.setText("⏸" if s==QMediaPlayer.PlayingState else "▶")
    def on_media_status(self, s): 
        if s==QMediaPlayer.EndOfMedia: 
            if self.mode==1: self.player.play() 
            else: self.play_next()
    def handle_err(self): QTimer.singleShot(1000, self.play_next)
    def tog_play(self):
        if self.player.state()==QMediaPlayer.PlayingState: self.player.pause()
        else: self.player.play()
    def tm(self): self.mode=(self.mode+1)%3; self.bm.setText(["🔁","🔂","🔀"][self.mode])
    def tr(self):
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
                    d=json.load(f); self.music_folder=d.get("folder",""); 
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

    def save_config(self): with open(CONFIG_FILE,'w') as f: json.dump({"folder":self.music_folder},f)
    def save_meta(self): with open(METADATA_FILE,'w') as f: json.dump(self.metadata,f)
    def save_off(self): with open(OFFSET_FILE,'w') as f: json.dump(self.saved_offsets,f)
    def save_hist(self): with open(HISTORY_FILE,'w') as f: json.dump(self.history,f)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(app_path, 'PyQt5', 'Qt', 'plugins')
        QCoreApplication.addLibraryPath(os.path.join(app_path, 'PyQt5', 'Qt', 'plugins'))
    app = QApplication(sys.argv)
    f = QFont("Microsoft YaHei UI", 10); app.setFont(f)
    w = SodaPlayer(); w.show(); sys.exit(app.exec_())

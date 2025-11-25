import sys
import os
import json
import shutil
import random
import threading
import subprocess

# ==========================================
# 1. 核心修复：Qt 插件寻路
# ==========================================
def init_env_setup():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        # 暴力搜索 plugins
        possible_paths = [
            os.path.join(base_path, 'PyQt5', 'Qt5', 'plugins'),
            os.path.join(base_path, 'PyQt5', 'Qt', 'plugins'),
            os.path.join(base_path, 'PyQt5', 'plugins'),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                os.environ['QT_PLUGIN_PATH'] = p
                from PyQt5.QtCore import QCoreApplication
                QCoreApplication.addLibraryPath(p)
                break
init_env_setup()

# ==========================================
# 2. 核心修复：寻找内置 FFmpeg
# ==========================================
def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        # 打包模式：在临时目录找
        path = os.path.join(sys._MEIPASS, 'ffmpeg.exe')
        if os.path.exists(path):
            return path
    # 本地模式
    if os.path.exists("ffmpeg.exe"):
        return os.path.abspath("ffmpeg.exe")
    return None # 找不到就返回None

FFMPEG_BIN = get_ffmpeg_path()

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QFileDialog, QFrame, QAbstractItemView,
                             QGraphicsDropShadowEffect, QInputDialog, QMessageBox, 
                             QFontDialog, QMenu, QAction, QSlider)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QDesktopServices
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

CONFIG_FILE = "config.json"

# --- 样式表 ---
STYLESHEET = """
QMainWindow { background-color: #FFFFFF; }
QWidget { font-family: "SimSun", "宋体", serif; color: #333333; }
QFrame#Sidebar { background-color: #F7F9FC; border-right: 1px solid #EEEEEE; }
QLabel#Logo { font-size: 22px; font-weight: bold; color: #1ECD97; padding: 20px; }
QPushButton.NavBtn { background-color: transparent; border: none; text-align: left; padding: 12px 20px; font-size: 14px; color: #666; border-radius: 8px; margin: 4px 10px; }
QPushButton.NavBtn:hover { background-color: #E8F5E9; color: #1ECD97; }
QPushButton#DownloadBtn { color: #FF6699; }
QPushButton#DownloadBtn:hover { background-color: #FFF0F5; color: #FF6699; }
QListWidget { background-color: #FFFFFF; border: none; outline: none; }
QListWidget::item { padding: 10px; margin: 2px 10px; border-radius: 6px; border-bottom: 1px solid #F9F9F9; }
QListWidget::item:selected { background-color: #FFF8E1; color: #F9A825; }
QFrame#PlayerBar { background-color: #FFFFFF; border-top: 1px solid #F0F0F0; }
QPushButton#PlayBtn { background-color: #1ECD97; color: white; border-radius: 25px; font-size: 20px; min-width: 50px; min-height: 50px; }
QPushButton#PlayBtn:hover { background-color: #18c48f; }
QPushButton.CtrlBtn { background: transparent; border: none; font-size: 16px; color: #666; }
QPushButton.CtrlBtn:hover { color: #1ECD97; background-color: #F0F0F0; border-radius: 4px; }
QSlider::groove:horizontal { border: 1px solid #EEE; height: 6px; background: #F0F0F0; margin: 2px 0; border-radius: 3px; }
QSlider::handle:horizontal { background: #1ECD97; border: 1px solid #1ECD97; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }
QSlider::sub-page:horizontal { background: #1ECD97; border-radius: 3px; }
"""

class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, url, folder, mode):
        super().__init__()
        self.url = url
        self.folder = folder
        self.mode = mode 

    def run(self):
        if not yt_dlp:
            self.progress_signal.emit("错误：缺少 yt-dlp")
            return
        
        if not FFMPEG_BIN:
            self.progress_signal.emit("致命错误：FFmpeg 未打包成功，无法转码！")
            return

        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '')
                filename = os.path.basename(d.get('filename', '未知'))
                if len(filename) > 25: filename = filename[:25] + "..."
                self.progress_signal.emit(f"⬇️ {p} : {filename}")
            elif d['status'] == 'finished':
                self.progress_signal.emit("♻️ 正在转码 MP3...")

        is_playlist = True if self.mode == 1 else False

        ydl_opts = {
            'outtmpl': os.path.join(self.folder, '%(title)s.%(ext)s'),
            'noplaylist': not is_playlist,
            'ignoreerrors': True,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'nocheckcertificate': True,
            
            # 指定内置的 ffmpeg
            'ffmpeg_location': FFMPEG_BIN,
            
            # 强制转码为 MP3
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            self.progress_signal.emit("🔍 正在解析...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.progress_signal.emit("🎉 任务完成")
            self.finished_signal.emit()
        except Exception as e:
            self.progress_signal.emit(f"❌ 错误: {str(e)}")

class DesktopLyricWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1000, 200)
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - 1000) // 2, screen.height() - 250)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.current_font = QFont("SimSun", 30)
        self.current_font.setBold(True)
        self.labels = []
        for i in range(3):
            lbl = QLabel("")
            lbl.setAlignment(Qt.AlignCenter)
            self.labels.append(lbl)
            self.layout.addWidget(lbl)
        self.update_styles()

    def update_styles(self):
        base = self.current_font.pointSize()
        shadow = QColor(30, 205, 151, 150)
        for i, lbl in enumerate(self.labels):
            eff = QGraphicsDropShadowEffect()
            eff.setBlurRadius(8); eff.setColor(shadow); eff.setOffset(0,0)
            lbl.setGraphicsEffect(eff)
            f = QFont(self.current_font)
            if i == 1:
                f.setPointSize(base)
                lbl.setStyleSheet("color: #FFFFFF;")
            else:
                f.setPointSize(int(base * 0.6))
                lbl.setStyleSheet("color: rgba(255, 255, 255, 180);")
            lbl.setFont(f)

    def set_lyrics(self, p, c, n):
        self.labels[0].setText(p)
        self.labels[1].setText(c)
        self.labels[2].setText(n)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.dp = e.globalPos() - self.frameGeometry().topLeft()
        elif e.button() == Qt.RightButton: self.change_font()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton: self.move(e.globalPos() - self.dp)
    def wheelEvent(self, e):
        d = e.angleDelta().y()
        s = self.current_font.pointSize()
        self.current_font.setPointSize(min(100, s+2) if d>0 else max(12, s-2))
        self.update_styles()
    def change_font(self):
        f, ok = QFontDialog.getFont(self.current_font, self, "字体")
        if ok: self.current_font = f; self.update_styles()

class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 (FFmpeg修复版)")
        self.resize(1080, 720)
        self.setStyleSheet(STYLESHEET)

        self.music_folder = ""
        self.playlist = []
        self.lyrics = []
        self.current_index = -1
        self.offset = 0
        self.mode = 0 
        self.rate = 1.0 
        self.is_slider_pressed = False 

        self.player = QMediaPlayer()
        self.player.setVolume(100)
        self.player.positionChanged.connect(self.on_pos_changed)
        self.player.durationChanged.connect(self.on_dur_changed)
        self.player.stateChanged.connect(self.on_state_changed)
        self.player.mediaStatusChanged.connect(self.on_status_changed)
        self.player.error.connect(self.on_error)

        self.desktop_lyric = DesktopLyricWindow()
        self.desktop_lyric.show()

        self.init_ui()
        self.load_config()

    def init_ui(self):
        c = QWidget(); self.setCentralWidget(c)
        lay = QHBoxLayout(c); lay.setContentsMargins(0,0,0,0)
        
        side = QFrame(); side.setObjectName("Sidebar"); side.setFixedWidth(240)
        sl = QVBoxLayout(side)
        sl.addWidget(QLabel("🧼 SODA MUSIC", objectName="Logo"))
        
        btn_local = QPushButton("💿  本地乐库"); btn_local.setProperty("NavBtn",True)
        sl.addWidget(btn_local)
        
        btn_dl = QPushButton("📺  B站/合集下载"); btn_dl.setObjectName("DownloadBtn"); btn_dl.setProperty("NavBtn",True)
        btn_dl.clicked.connect(self.download_bili)
        sl.addWidget(btn_dl)
        
        sl.addStretch()
        
        btn_fd = QPushButton("📁  设置文件夹"); btn_fd.setProperty("NavBtn",True)
        btn_fd.clicked.connect(self.select_folder)
        sl.addWidget(btn_fd)
        
        btn_ly = QPushButton("💬  桌面歌词"); btn_ly.setProperty("NavBtn",True)
        btn_ly.clicked.connect(self.toggle_lyric)
        sl.addWidget(btn_ly)
        lay.addWidget(side)

        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(0,0,0,0)
        
        content = QWidget(); cl = QHBoxLayout(content)
        self.list_w = QListWidget()
        self.list_w.itemDoubleClicked.connect(self.play_item)
        self.list_w.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_w.customContextMenuRequested.connect(self.show_menu)
        cl.addWidget(self.list_w, stretch=6)
        
        self.lrc_p = QListWidget(); self.lrc_p.setFocusPolicy(Qt.NoFocus)
        self.lrc_p.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lrc_p.setStyleSheet("color:#999; border:none;")
        cl.addWidget(self.lrc_p, stretch=4)
        rl.addWidget(content)

        bar = QFrame(); bar.setObjectName("PlayerBar"); bar.setFixedHeight(110)
        bl = QVBoxLayout(bar)
        
        pl = QHBoxLayout()
        self.lbl_cur = QLabel("00:00")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderPressed.connect(self.slider_p)
        self.slider.sliderReleased.connect(self.slider_r)
        self.slider.valueChanged.connect(self.slider_m)
        self.lbl_tot = QLabel("00:00")
        pl.addWidget(self.lbl_cur); pl.addWidget(self.slider); pl.addWidget(self.lbl_tot)
        bl.addLayout(pl)
        
        cl2 = QHBoxLayout()
        self.btn_mode = QPushButton("🔁"); self.btn_mode.setProperty("CtrlBtn",True)
        self.btn_mode.clicked.connect(self.toggle_mode)
        
        btn_prv = QPushButton("⏮"); btn_prv.setProperty("CtrlBtn",True); btn_prv.clicked.connect(self.prev)
        self.btn_play = QPushButton("▶"); self.btn_play.setObjectName("PlayBtn"); self.btn_play.clicked.connect(self.toggle_play)
        btn_nxt = QPushButton("⏭"); btn_nxt.setProperty("CtrlBtn",True); btn_nxt.clicked.connect(self.next)
        
        self.btn_rate = QPushButton("1.0x"); self.btn_rate.setProperty("CtrlBtn",True)
        self.btn_rate.clicked.connect(self.toggle_rate)
        
        cl2.addStretch(); cl2.addWidget(self.btn_mode); cl2.addSpacing(15)
        cl2.addWidget(btn_prv); cl2.addSpacing(10); cl2.addWidget(self.btn_play)
        cl2.addSpacing(10); cl2.addWidget(btn_nxt); cl2.addSpacing(15)
        cl2.addWidget(self.btn_rate); cl2.addStretch()
        
        btn_off = QPushButton("Offset+0.5s"); btn_off.setStyleSheet("color:#AAA;border:none")
        btn_off.clicked.connect(lambda: self.adj_offset(0.5))
        cl2.addWidget(btn_off)
        
        bl.addLayout(cl2)
        rl.addWidget(bar); lay.addWidget(right)

    def show_menu(self, pos):
        item = self.list_w.itemAt(pos)
        if not item: return
        m = QMenu()
        a1 = m.addAction("✏️ 重命名"); a2 = m.addAction("📝 导入歌词"); a3 = m.addAction("🗑️ 删除")
        idx = self.list_w.row(item)
        a1.triggered.connect(lambda: self.ren_song(idx))
        a2.triggered.connect(lambda: self.imp_lrc(idx))
        a3.triggered.connect(lambda: self.del_song(idx))
        m.exec_(self.list_w.mapToGlobal(pos))

    def ren_song(self, idx):
        s = self.playlist[idx]; old = s["path"]
        n, ok = QInputDialog.getText(self, "重命名", "新名:", text=os.path.splitext(s["name"])[0])
        if ok and n:
            new_p = os.path.join(self.music_folder, n + os.path.splitext(s["name"])[1])
            try:
                if self.current_index == idx: self.player.stop()
                os.rename(old, new_p)
                self.scan()
            except Exception as e: QMessageBox.warning(self,"Err",str(e))

    def imp_lrc(self, idx):
        f, _ = QFileDialog.getOpenFileName(self, "选歌词", "", "LRC (*.lrc)")
        if f:
            t = os.path.join(self.music_folder, os.path.splitext(self.playlist[idx]["name"])[0]+".lrc")
            shutil.copy(f, t); QMessageBox.information(self,"OK","导入成功")

    def del_song(self, idx):
        if QMessageBox.Yes == QMessageBox.question(self,"Del","确认删除?"):
            try:
                if self.current_index == idx: self.player.stop()
                os.remove(self.playlist[idx]["path"]); self.scan()
            except: pass

    def download_bili(self):
        if not self.music_folder: return QMessageBox.warning(self,"提示","请先设置文件夹")
        if not FFMPEG_BIN: return QMessageBox.critical(self,"错误","FFmpeg 未正确加载，无法转码")
        
        u, ok = QInputDialog.getText(self,"B站下载","链接 (BV/合集):")
        if not ok or not u: return
        
        mb = QMessageBox(); mb.setText("下载模式")
        b1 = mb.addButton("仅当前视频", QMessageBox.ActionRole)
        b2 = mb.addButton("整个合集", QMessageBox.ActionRole)
        mb.addButton("取消", QMessageBox.RejectRole); mb.exec_()
        
        if mb.clickedButton() not in [b1,b2]: return
        mode = 0 if mb.clickedButton() == b1 else 1
        
        self.lbl_curr_time.setText("准备下载...")
        self.dl = BilibiliDownloader(u, self.music_folder, mode)
        self.dl.progress_signal.connect(lambda m: self.lbl_curr_time.setText(m))
        self.dl.finished_signal.connect(self.on_dl_done)
        self.dl.start()

    def on_dl_done(self):
        self.scan()
        QMessageBox.information(self,"完成","下载并转码完成！")

    def select_folder(self):
        f = QFileDialog.getExistingDirectory(self,"目录"); 
        if f: self.music_folder = f; self.scan(); self.save_cfg()

    def scan(self):
        self.playlist = []; self.list_w.clear()
        if not os.path.exists(self.music_folder): return
        for f in sorted(os.listdir(self.music_folder)):
            if f.lower().endswith(('.mp3','.wav','.m4a','.flac')):
                self.playlist.append({"path":os.path.join(self.music_folder,f),"name":f})
                self.list_w.addItem(os.path.splitext(f)[0])

    def play_item(self, item): self.play(self.list_w.row(item))

    def play(self, idx):
        if not self.playlist or idx < 0 or idx >= len(self.playlist): return
        self.current_index = idx
        p = self.playlist[idx]["path"]
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(os.path.abspath(p))))
        self.player.setPlaybackRate(self.rate)
        self.player.play()
        self.btn_play.setText("⏸")
        self.list_w.setCurrentRow(idx)
        self.parse_lrc(os.path.splitext(p)[0]+".lrc")

    def parse_lrc(self, path):
        self.lyrics = []; self.lrc_p.clear(); self.desktop_lyric.set_lyrics("","等待歌词...","")
        self.offset = 0
        if not os.path.exists(path): 
            self.lrc_p.addItem("纯音乐")
            return
        try:
            with open(path,'r',encoding='utf-8') as f: lines=f.readlines()
        except:
            try:
                with open(path,'r',encoding='gbk') as f: lines=f.readlines()
            except: return
        
        import re
        reg = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\](.*)')
        for l in lines:
            m = reg.search(l)
            if m:
                mn,sc,ms,tx = m.groups()
                ms_v = int(ms)*10 if len(ms)==2 else int(ms)
                t = int(mn)*60 + int(sc) + ms_v/1000
                if tx.strip():
                    self.lyrics.append({"t":t,"txt":tx.strip()})
                    self.lrc_p.addItem(tx.strip())

    def on_pos_changed(self, pos):
        if not self.is_slider_pressed: self.slider.setValue(pos)
        self.lbl_curr_time.setText(self.fmt(pos))
        sec = pos/1000 + self.offset
        if self.lyrics:
            idx = -1
            for i,l in enumerate(self.lyrics):
                if sec >= l["t"]: idx = i
                else: break
            if idx != -1:
                self.lrc_p.setCurrentRow(idx)
                self.lrc_p.scrollToItem(self.lrc_p.item(idx), QAbstractItemView.PositionAtCenter)
                p = self.lyrics[idx-1]["txt"] if idx>0 else ""
                c = self.lyrics[idx]["txt"]
                n = self.lyrics[idx+1]["txt"] if idx<len(self.lyrics)-1 else ""
                self.desktop_lyric.set_lyrics(p,c,n)

    def on_dur_changed(self, d): self.slider.setRange(0,d); self.lbl_tot.setText(self.fmt(d))
    def slider_p(self): self.is_slider_pressed = True
    def slider_r(self): self.is_slider_pressed = False; self.player.setPosition(self.slider.value())
    def slider_m(self, v): 
        if self.is_slider_pressed: self.lbl_curr_time.setText(self.fmt(v))
    
    def on_state_changed(self, s): self.btn_play.setText("⏸" if s==QMediaPlayer.PlayingState else "▶")
    def on_status_changed(self, s): 
        if s==QMediaPlayer.EndOfMedia: 
            if self.mode==1: self.player.play()
            else: self.next()
    def on_error(self):
        self.btn_play.setText("▶")
        QMessageBox.warning(self,"Err",f"播放失败: {self.player.errorString()}\n请确保文件未损坏或已转码为 MP3")

    def toggle_play(self):
        if self.player.state()==QMediaPlayer.PlayingState: self.player.pause()
        else: self.player.play()
    def next(self):
        if not self.playlist: return
        idx = random.randint(0,len(self.playlist)-1) if self.mode==2 else (self.current_index+1)%len(self.playlist)
        self.play(idx)
    def prev(self):
        if not self.playlist: return
        idx = random.randint(0,len(self.playlist)-1) if self.mode==2 else (self.current_index-1)%len(self.playlist)
        self.play(idx)
    def toggle_mode(self):
        self.mode = (self.mode+1)%3
        self.btn_mode.setText(["🔁","🔂","🔀"][self.mode])
    def toggle_rate(self):
        rs = [1.0,1.25,1.5,2.0,0.5]
        try: i = rs.index(self.rate)
        except: i=0
        self.rate = rs[(i+1)%len(rs)]
        self.player.setPlaybackRate(self.rate)
        self.btn_rate.setText(f"{self.rate}x")
    
    def fmt(self, ms): s=ms//1000; return f"{s//60:02}:{s%60:02}"
    def adj_offset(self, v): self.offset += v
    def toggle_lyric(self): 
        if self.desktop_lyric.isVisible(): self.desktop_lyric.hide()
        else: self.desktop_lyric.show()
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE,'r') as f:
                    self.music_folder = json.load(f).get("folder","")
                    if self.music_folder: self.scan()
            except: pass
    def save_cfg(self):
        try:
            with open(CONFIG_FILE,'w') as f: json.dump({"folder":self.music_folder},f)
        except: pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    f = QFont("SimSun"); f.setPixelSize(14); app.setFont(f)
    w = SodaPlayer(); w.show()
    sys.exit(app.exec_())

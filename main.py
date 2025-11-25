import sys
import os
import json
import shutil
import random
import threading
import traceback
import datetime

# --- 日志记录功能 (用于诊断闪退) ---
def log(msg):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    try:
        with open("debug_log.txt", "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except: pass

log("=== 程序启动 ===")

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
    log("未找到 yt_dlp 库")

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

# --- B站下载线程 ---
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
            self.progress_signal.emit("错误：缺少 yt-dlp 组件")
            return

        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '')
                filename = os.path.basename(d.get('filename', '未知'))
                if len(filename) > 20: filename = filename[:20] + "..."
                self.progress_signal.emit(f"⬇️ {p} : {filename}")
            elif d['status'] == 'finished':
                self.progress_signal.emit("✅ 下载完成")

        is_playlist = True if self.mode == 1 else False

        ydl_opts = {
            # 强制 m4a，兼容性最好，不需要 ffmpeg 也能播放
            'format': 'bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(self.folder, '%(title)s.%(ext)s'),
            'noplaylist': not is_playlist,
            'ignoreerrors': True,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'nocheckcertificate': True,
        }

        try:
            log(f"开始下载: {self.url}, 模式: {'合集' if is_playlist else '单曲'}")
            self.progress_signal.emit("🔍 正在解析...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.progress_signal.emit("🎉 任务完成")
            log("下载任务结束")
            self.finished_signal.emit()
        except Exception as e:
            err_msg = str(e)
            log(f"下载出错: {err_msg}")
            self.progress_signal.emit(f"❌ 错误: {err_msg[:30]}...")

# --- 桌面歌词 ---
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
        base_size = self.current_font.pointSize()
        shadow_color = QColor(30, 205, 151, 150)
        for i, lbl in enumerate(self.labels):
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(8)
            effect.setColor(shadow_color)
            effect.setOffset(0, 0)
            lbl.setGraphicsEffect(effect)
            f = QFont(self.current_font)
            if i == 1:
                f.setPointSize(base_size)
                lbl.setStyleSheet("color: #FFFFFF;")
            else:
                f.setPointSize(int(base_size * 0.6))
                lbl.setStyleSheet("color: rgba(255, 255, 255, 180);")
            lbl.setFont(f)

    def set_lyrics(self, p, c, n):
        self.labels[0].setText(p)
        self.labels[1].setText(c)
        self.labels[2].setText(n)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton: self.change_font()
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton: self.move(event.globalPos() - self.drag_pos)
    def wheelEvent(self, event):
        d = event.angleDelta().y()
        s = self.current_font.pointSize()
        self.current_font.setPointSize(min(100, s+2) if d>0 else max(12, s-2))
        self.update_styles()
    def change_font(self):
        f, ok = QFontDialog.getFont(self.current_font, self, "歌词字体")
        if ok: 
            self.current_font = f
            self.update_styles()

# --- 主程序 ---
class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 (防闪退稳定版)")
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

        # 初始化播放器
        try:
            self.player = QMediaPlayer()
            self.player.setVolume(100)
            self.player.positionChanged.connect(self.on_position_changed)
            self.player.durationChanged.connect(self.on_duration_changed)
            self.player.stateChanged.connect(self.on_state_changed)
            self.player.mediaStatusChanged.connect(self.on_media_status_changed)
            self.player.error.connect(self.handle_player_error)
            log("播放器组件初始化成功")
        except Exception as e:
            log(f"播放器初始化失败: {e}")
            QMessageBox.critical(self, "致命错误", "播放器组件无法加载，请检查系统环境。")

        self.desktop_lyric = DesktopLyricWindow()
        self.desktop_lyric.show()

        self.init_ui()
        self.load_config()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(sidebar)
        
        logo = QLabel("🧼 SODA MUSIC")
        logo.setObjectName("Logo")
        side_layout.addWidget(logo)

        self.btn_local = QPushButton("💿  本地乐库")
        self.btn_local.setProperty("NavBtn", True)
        side_layout.addWidget(self.btn_local)

        self.btn_bili = QPushButton("📺  B站/合集下载")
        self.btn_bili.setObjectName("DownloadBtn")
        self.btn_bili.setProperty("NavBtn", True)
        self.btn_bili.clicked.connect(self.download_from_bilibili)
        side_layout.addWidget(self.btn_bili)

        side_layout.addStretch()
        
        btn_folder = QPushButton("📁  设置文件夹")
        btn_folder.setProperty("NavBtn", True)
        btn_folder.clicked.connect(self.select_folder)
        side_layout.addWidget(btn_folder)
        
        btn_lyric = QPushButton("💬  桌面歌词")
        btn_lyric.setProperty("NavBtn", True)
        btn_lyric.clicked.connect(self.toggle_lyric)
        side_layout.addWidget(btn_lyric)
        
        layout.addWidget(sidebar)

        right_panel = QWidget()
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0, 0, 0, 0)
        
        content = QWidget()
        c_layout = QHBoxLayout(content)
        
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        c_layout.addWidget(self.list_widget, stretch=6)
        
        self.panel_lyric = QListWidget()
        self.panel_lyric.setFocusPolicy(Qt.NoFocus)
        self.panel_lyric.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.panel_lyric.setStyleSheet("color:#999; border:none;")
        c_layout.addWidget(self.panel_lyric, stretch=4)
        
        r_layout.addWidget(content)

        bar = QFrame()
        bar.setObjectName("PlayerBar")
        bar.setFixedHeight(110)
        bar_v_layout = QVBoxLayout(bar) 

        progress_layout = QHBoxLayout()
        self.lbl_curr_time = QLabel("00:00")
        self.lbl_total_time = QLabel("00:00")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderPressed.connect(self.slider_pressed)
        self.slider.sliderReleased.connect(self.slider_released)
        self.slider.valueChanged.connect(self.slider_moved)
        progress_layout.addWidget(self.lbl_curr_time)
        progress_layout.addWidget(self.slider)
        progress_layout.addWidget(self.lbl_total_time)
        bar_v_layout.addLayout(progress_layout)

        ctrl_layout = QHBoxLayout()
        self.btn_mode = QPushButton("🔁")
        self.btn_mode.setToolTip("当前: 列表循环")
        self.btn_mode.setProperty("CtrlBtn", True)
        self.btn_mode.clicked.connect(self.toggle_mode)
        
        btn_prev = QPushButton("⏮")
        btn_prev.setProperty("CtrlBtn", True)
        btn_prev.clicked.connect(self.play_prev)
        
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("PlayBtn")
        self.btn_play.clicked.connect(self.toggle_play)
        
        btn_next = QPushButton("⏭")
        btn_next.setProperty("CtrlBtn", True)
        btn_next.clicked.connect(self.play_next)

        self.btn_rate = QPushButton("1.0x")
        self.btn_rate.setProperty("CtrlBtn", True)
        self.btn_rate.clicked.connect(self.toggle_rate)
        
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_mode)
        ctrl_layout.addSpacing(15)
        ctrl_layout.addWidget(btn_prev)
        ctrl_layout.addSpacing(10)
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addSpacing(10)
        ctrl_layout.addWidget(btn_next)
        ctrl_layout.addSpacing(15)
        ctrl_layout.addWidget(self.btn_rate)
        ctrl_layout.addStretch()

        btn_offset = QPushButton("Offset+0.5s")
        btn_offset.setStyleSheet("color:#AAA; border:none;")
        btn_offset.clicked.connect(lambda: self.adjust_offset(0.5))
        ctrl_layout.addWidget(btn_offset)

        bar_v_layout.addLayout(ctrl_layout)
        r_layout.addWidget(bar)
        layout.addWidget(right_panel)

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        menu = QMenu()
        act_rename = QAction("✏️ 重命名", self)
        act_import = QAction("📝 导入歌词", self)
        act_del = QAction("🗑️ 删除", self)
        idx = self.list_widget.row(item)
        act_rename.triggered.connect(lambda: self.rename_song(idx))
        act_import.triggered.connect(lambda: self.import_lyric(idx))
        act_del.triggered.connect(lambda: self.delete_song(idx))
        menu.addAction(act_rename)
        menu.addAction(act_import)
        menu.addSeparator()
        menu.addAction(act_del)
        menu.exec_(self.list_widget.mapToGlobal(pos))

    def rename_song(self, idx):
        song = self.playlist[idx]
        old = song["path"]
        name, ok = QInputDialog.getText(self, "重命名", "新歌名:", text=os.path.splitext(song["name"])[0])
        if ok and name:
            new_name = name + os.path.splitext(song["name"])[1]
            new_path = os.path.join(self.music_folder, new_name)
            try:
                if self.current_index == idx: self.player.stop()
                os.rename(old, new_path)
                old_lrc = os.path.splitext(old)[0] + ".lrc"
                if os.path.exists(old_lrc):
                    os.rename(old_lrc, os.path.join(self.music_folder, name + ".lrc"))
                self.scan_music()
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def import_lyric(self, idx):
        song = self.playlist[idx]
        f, _ = QFileDialog.getOpenFileName(self, "选歌词", "", "LRC/TXT (*.lrc *.txt)")
        if f:
            t = os.path.join(self.music_folder, os.path.splitext(song["name"])[0] + ".lrc")
            shutil.copy(f, t)
            if self.current_index == idx:
                self.parse_lrc(t)
            QMessageBox.information(self,"成功","歌词已导入")

    def delete_song(self, idx):
        song = self.playlist[idx]
        if QMessageBox.Yes == QMessageBox.question(self, "确认", f"删除 {song['name']}?"):
            try:
                if self.current_index == idx: self.player.stop()
                os.remove(song["path"])
                lrc = os.path.splitext(song["path"])[0] + ".lrc"
                if os.path.exists(lrc):
                    os.remove(lrc)
                self.scan_music()
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def download_from_bilibili(self):
        if not self.music_folder: 
            return QMessageBox.warning(self, "提示", "请先设置音乐文件夹")
        
        url, ok = QInputDialog.getText(self, "B站下载", "视频链接 (BV号/合集):")
        if not ok or not url: return

        msg_box = QMessageBox()
        msg_box.setWindowTitle("下载选项")
        msg_box.setText("请选择下载模式：")
        btn_single = msg_box.addButton("仅当前视频", QMessageBox.ActionRole)
        btn_batch = msg_box.addButton("整个合集/列表", QMessageBox.ActionRole)
        msg_box.addButton("取消", QMessageBox.RejectRole)
        msg_box.exec_()
        
        if msg_box.clickedButton() not in [btn_single, btn_batch]: return
        dl_mode = 0 if msg_box.clickedButton() == btn_single else 1

        self.lbl_curr_time.setText("准备下载...")
        self.dl = BilibiliDownloader(url, self.music_folder, dl_mode)
        self.dl.progress_signal.connect(lambda m: self.lbl_curr_time.setText(m))
        self.dl.finished_signal.connect(self.on_dl_finish)
        self.dl.start()
    
    def on_dl_finish(self):
        self.scan_music()
        QMessageBox.information(self, "完成", "下载任务结束")

    def select_folder(self):
        f = QFileDialog.getExistingDirectory(self, "选择目录")
        if f:
            self.music_folder = f
            self.scan_music()
            self.save_config()

    def scan_music(self):
        self.playlist = []
        self.list_widget.clear()
        if not os.path.exists(self.music_folder): return
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4')
        files = [x for x in os.listdir(self.music_folder) if x.lower().endswith(exts)]
        files.sort()
        for f in files:
            self.playlist.append({"path": os.path.join(self.music_folder, f), "name": f})
            self.list_widget.addItem(os.path.splitext(f)[0])

    def play_selected(self, item):
        self.play_index(self.list_widget.row(item))

    # --- 【防闪退核心】增加 try-except ---
    def play_index(self, idx):
        if not self.playlist or idx < 0 or idx >= len(self.playlist): return
        
        try:
            self.current_index = idx
            song = self.playlist[idx]
            
            # 打印日志，如果闪退可以知道卡在哪
            log(f"尝试播放: {song['name']}")
            
            url = QUrl.fromLocalFile(song["path"])
            self.player.setMedia(QMediaContent(url))
            self.player.setPlaybackRate(self.rate)
            self.player.play()
            
            self.btn_play.setText("⏸")
            self.list_widget.setCurrentRow(idx)
            self.parse_lrc(os.path.splitext(song["path"])[0] + ".lrc")
        except Exception as e:
            log(f"播放发生严重错误: {traceback.format_exc()}")
            QMessageBox.warning(self, "错误", "播放时发生严重错误，已记录日志。")

    def parse_lrc(self, path):
        self.lyrics = []
        self.panel_lyric.clear()
        self.desktop_lyric.set_lyrics("", "等待歌词...", "")
        self.offset = 0
        if not os.path.exists(path): 
            self.panel_lyric.addItem("纯音乐")
            return
        
        lines = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except:
            try:
                with open(path, 'r', encoding='gbk') as f:
                    lines = f.readlines()
            except:
                return

        import re
        p = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\](.*)')
        for l in lines:
            m = p.search(l)
            if m:
                mn, sc, ms, txt = m.groups()
                ms_v = int(ms)*10 if len(ms)==2 else int(ms)
                t = int(mn)*60 + int(sc) + ms_v/1000
                if txt.strip():
                    self.lyrics.append({"t": t, "txt": txt.strip()})
                    self.panel_lyric.addItem(txt.strip())

    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        elif self.playlist:
            self.player.play()
    
    def toggle_mode(self):
        self.mode = (self.mode + 1) % 3
        modes = ["🔁", "🔂", "🔀"]
        self.btn_mode.setText(modes[self.mode])

    def toggle_rate(self):
        rates = [1.0, 1.25, 1.5, 2.0, 0.5]
        try:
            curr_idx = rates.index(self.rate)
        except:
            curr_idx = 0
        self.rate = rates[(curr_idx + 1) % len(rates)]
        self.player.setPlaybackRate(self.rate)
        self.btn_rate.setText(f"{self.rate}x")

    def play_next(self):
        if not self.playlist: return
        if self.mode == 2:
            nxt = random.randint(0, len(self.playlist)-1)
        else:
            nxt = (self.current_index + 1) % len(self.playlist)
        self.play_index(nxt)

    def play_prev(self):
        if not self.playlist: return
        if self.mode == 2:
            prev = random.randint(0, len(self.playlist)-1)
        else:
            prev = (self.current_index - 1) % len(self.playlist)
        self.play_index(prev)

    def on_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.btn_play.setText("⏸")
        else:
            self.btn_play.setText("▶")

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            if self.mode == 1:
                self.player.play()
            else:
                self.play_next()

    def handle_player_error(self):
        # 错误处理逻辑优化
        log(f"QMediaPlayer Error: {self.player.errorString()}")
        self.btn_play.setText("▶")
        # 如果是 m4a 且报错，基本是解码器问题
        QMessageBox.warning(self, "播放失败", f"错误详情: {self.player.errorString()}\n\n如果文件是 B站下载的，说明你的系统缺少解码器。\n建议安装 K-Lite Codec Pack。")

    def on_duration_changed(self, dur):
        self.slider.setRange(0, dur)
        self.lbl_total_time.setText(self.fmt_time(dur))

    def on_position_changed(self, pos):
        if not self.is_slider_pressed:
            self.slider.setValue(pos)
        self.lbl_curr_time.setText(self.fmt_time(pos))
        sec = pos / 1000 + self.offset
        if self.lyrics:
            idx = -1
            for i, l in enumerate(self.lyrics):
                if sec >= l["t"]: idx = i
                else: break
            if idx != -1:
                self.panel_lyric.setCurrentRow(idx)
                self.panel_lyric.scrollToItem(self.panel_lyric.item(idx), QAbstractItemView.PositionAtCenter)
                p = self.lyrics[idx-1]["txt"] if idx>0 else ""
                c = self.lyrics[idx]["txt"]
                n = self.lyrics[idx+1]["txt"] if idx<len(self.lyrics)-1 else ""
                self.desktop_lyric.set_lyrics(p, c, n)

    def slider_pressed(self): self.is_slider_pressed = True
    def slider_released(self):
        self.is_slider_pressed = False
        self.player.setPosition(self.slider.value())
    def slider_moved(self, val):
        if self.is_slider_pressed: self.lbl_curr_time.setText(self.fmt_time(val))
    def fmt_time(self, ms):
        s = ms // 1000
        return f"{s//60:02}:{s%60:02}"
    def adjust_offset(self, v): self.offset += v
    def toggle_lyric(self):
        if self.desktop_lyric.isVisible(): self.desktop_lyric.hide()
        else: self.desktop_lyric.show()
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.music_folder = data.get("folder", "")
                    if self.music_folder: self.scan_music()
            except: pass
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"folder": self.music_folder}, f)
        except: pass

if __name__ == "__main__":
    # 异常捕获，防止闪退无提示
    sys.excepthook = lambda cls, exception, trace: log(f"未捕获异常: {exception}")
    app = QApplication(sys.argv)
    f = QFont("SimSun"); f.setPixelSize(14)
    app.setFont(f)
    w = SodaPlayer()
    w.show()
    sys.exit(app.exec_())

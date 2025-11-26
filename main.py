import sys
import os
import json
import shutil
import random
import threading
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QFileDialog, QFrame, QAbstractItemView,
                             QGraphicsDropShadowEffect, QInputDialog, QMessageBox, 
                             QFontDialog, QMenu, QAction, QSlider, QDialog, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize, QCoreApplication, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# --- 强制使用 Windows 原生解码器 ---
os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"

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

QPushButton.NavBtn {
    background-color: transparent; border: none; text-align: left; 
    padding: 12px 20px; font-size: 14px; color: #666; border-radius: 8px; margin: 4px 10px;
}
QPushButton.NavBtn:hover { background-color: #E8F5E9; color: #1ECD97; }

QPushButton#DownloadBtn { color: #FF6699; }
QPushButton#DownloadBtn:hover { background-color: #FFF0F5; color: #FF6699; }

QListWidget { background-color: #FFFFFF; border: none; outline: none; }
QListWidget::item { padding: 10px; margin: 2px 10px; border-radius: 6px; border-bottom: 1px solid #F9F9F9; }
QListWidget::item:selected { background-color: #FFF8E1; color: #F9A825; }

QFrame#PlayerBar { background-color: #FFFFFF; border-top: 1px solid #F0F0F0; }

QPushButton#PlayBtn { 
    background-color: #1ECD97; color: white; border-radius: 25px; 
    font-size: 20px; min-width: 50px; min-height: 50px;
}
QPushButton#PlayBtn:hover { background-color: #18c48f; }

QPushButton.CtrlBtn { background: transparent; border: none; font-size: 16px; color: #666; }
QPushButton.CtrlBtn:hover { color: #1ECD97; background-color: #F0F0F0; border-radius: 4px; }

QSlider::groove:horizontal {
    border: 1px solid #EEE; height: 6px; background: #F0F0F0; margin: 2px 0; border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #1ECD97; border: 1px solid #1ECD97; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px;
}
QSlider::sub-page:horizontal {
    background: #1ECD97; border-radius: 3px;
}
"""

# --- 工具函数：文件名净化 ---
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

# --- 下载模式弹窗 ---
class DownloadDialog(QDialog):
    def __init__(self, parent=None, current_p=1):
        super().__init__(parent)
        self.setWindowTitle("下载选项")
        self.resize(350, 180)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"识别到当前链接为第 {current_p} 集"))
        
        self.rb_single = QRadioButton(f"单曲下载 (仅第 {current_p} 集)")
        self.rb_list = QRadioButton(f"合集下载 (从第 {current_p} 集到最后)")
        self.rb_single.setChecked(True)
        
        layout.addWidget(self.rb_single)
        layout.addWidget(self.rb_list)
        
        btn_box = QHBoxLayout()
        btn_ok = QPushButton("🚀 开始下载")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        
        layout.addLayout(btn_box)

    def get_mode(self):
        return "playlist" if self.rb_list.isChecked() else "single"

# --- B站下载线程 (带详细进度) ---
class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, url, folder, mode="single", start_p=1):
        super().__init__()
        self.url = url
        self.folder = folder
        self.mode = mode
        self.start_p = start_p

    def run(self):
        if not yt_dlp:
            self.error_signal.emit("错误：缺少 yt-dlp")
            return

        def progress_hook(d):
            if d['status'] == 'downloading':
                # 获取进度百分比
                percent = d.get('_percent_str', '0%')
                
                # 获取文件名 (当前分P标题)
                raw_name = d.get('filename', '未知')
                filename = os.path.basename(raw_name)
                if len(filename) > 15: filename = filename[:15] + "..."
                
                # 获取合集进度 (第几首 / 共几首)
                # yt-dlp 的 info_dict 里包含了 playlist_index 和 playlist_count
                info = d.get('info_dict', {})
                idx = info.get('playlist_index', 1)
                total = info.get('n_entries', '?')
                
                if total and str(total) != '?':
                    msg = f"⬇️ [{idx}/{total}] {percent} : {filename}"
                else:
                    msg = f"⬇️ {percent} : {filename}"
                    
                self.progress_signal.emit(msg)
                
            elif d['status'] == 'finished':
                self.progress_signal.emit("✅ 一首下载完成，准备下一首...")

        items_range = str(self.start_p) if self.mode == 'single' else f"{self.start_p}-"

        ydl_opts = {
            # 强制 m4a/mp4
            'format': 'bestaudio[ext=m4a]/best[ext=mp4]/best', 
            
            # 关键修改：使用 %(title)s 也就是当前选集的标题，而不是合集标题
            'outtmpl': os.path.join(self.folder, '%(title)s.%(ext)s'),
            
            # 关键修改：强制覆盖重名文件，不生成 (1)
            'overwrites': True,
            'nooverwrites': False,
            
            'noplaylist': False, 
            'playlist_items': items_range,
            
            'ignoreerrors': True,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'nocheckcertificate': True,
            'restrictfilenames': False, # 保留中文
        }

        try:
            self.progress_signal.emit(f"🔍 解析中... (模式: {self.mode})")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            self.progress_signal.emit("🎉 所有任务完成")
            self.finished_signal.emit()
            
        except Exception as e:
            self.error_signal.emit(f"❌: {str(e)}")

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
        self.setWindowTitle("汽水音乐 (旗舰版)")
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

        btn_refresh = QPushButton("🔄  刷新列表")
        btn_refresh.setProperty("NavBtn", True)
        btn_refresh.clicked.connect(self.scan_music)
        side_layout.addWidget(btn_refresh)

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
        
        # 即使没选中歌曲，也可以点右键批量操作
        menu = QMenu()
        
        # 选中项操作
        if item:
            idx = self.list_widget.row(item)
            act_rename = QAction("✏️ 重命名单曲", self)
            act_bind = QAction("🔐 绑定歌词 (整理模式)", self)
            act_del = QAction("🗑️ 删除", self)
            
            act_rename.triggered.connect(lambda: self.rename_song(idx))
            act_bind.triggered.connect(lambda: self.bind_lyrics(idx))
            act_del.triggered.connect(lambda: self.delete_song(idx))
            
            menu.addAction(act_rename)
            menu.addAction(act_bind)
            menu.addAction(act_del)
            menu.addSeparator()

        # 全局操作
        act_batch_rename = QAction("🔠 批量重命名 (查找替换)", self)
        act_batch_rename.triggered.connect(self.batch_rename)
        menu.addAction(act_batch_rename)
        
        menu.exec_(self.list_widget.mapToGlobal(pos))

    # --- 批量重命名功能 ---
    def batch_rename(self):
        if not self.playlist: return QMessageBox.warning(self, "提示", "列表为空")
        
        find_str, ok1 = QInputDialog.getText(self, "批量重命名", "输入要【查找】的字符 (例如: 【高清】):")
        if not ok1: return
        
        replace_str, ok2 = QInputDialog.getText(self, "批量重命名", f"将 '{find_str}' 【替换】为 (留空则删除):")
        if not ok2: return
        
        count = 0
        for song in self.playlist:
            if find_str in song["name"]:
                old_path = song["path"]
                new_name = song["name"].replace(find_str, replace_str)
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                
                try:
                    # 如果当前在播放这首，先停止
                    if self.current_index >= 0 and self.playlist[self.current_index]["path"] == old_path:
                        self.player.stop()
                        
                    os.rename(old_path, new_path)
                    count += 1
                    
                    # 顺便尝试改同名lrc
                    old_lrc = os.path.splitext(old_path)[0] + ".lrc"
                    if os.path.exists(old_lrc):
                        new_lrc_name = os.path.splitext(new_name)[0] + ".lrc"
                        os.rename(old_lrc, os.path.join(os.path.dirname(old_path), new_lrc_name))
                        
                except Exception as e:
                    print(f"Rename failed: {e}")
        
        self.scan_music()
        QMessageBox.information(self, "完成", f"已批量修改 {count} 个文件")

    def rename_song(self, idx):
        song = self.playlist[idx]
        old = song["path"]
        name, ok = QInputDialog.getText(self, "重命名", "新歌名:", text=os.path.splitext(song["name"])[0])
        if ok and name:
            name = sanitize_filename(name)
            new_name = name + os.path.splitext(song["name"])[1]
            new_path = os.path.join(os.path.dirname(old), new_name)
            try:
                if self.current_index == idx: self.player.stop()
                os.rename(old, new_path)
                old_lrc = os.path.splitext(old)[0] + ".lrc"
                if os.path.exists(old_lrc): 
                    os.rename(old_lrc, os.path.join(os.path.dirname(old), name + ".lrc"))
                self.scan_music()
            except Exception as e: QMessageBox.warning(self, "错误", str(e))

    def bind_lyrics(self, idx):
        song = self.playlist[idx]
        song_path = song["path"]
        song_name = os.path.splitext(song["name"])[0]
        lrc_file, _ = QFileDialog.getOpenFileName(self, "选择歌词文件 (将复制)", "", "LRC/TXT (*.lrc *.txt)")
        if not lrc_file: return
        new_folder_name = f"{song_name}"
        new_folder_path = os.path.join(self.music_folder, new_folder_name)
        try:
            if not os.path.exists(new_folder_path): os.makedirs(new_folder_path)
            new_song_path = os.path.join(new_folder_path, song["name"])
            if self.current_index == idx: self.player.stop()
            shutil.move(song_path, new_song_path)
            new_lrc_path = os.path.join(new_folder_path, song_name + ".lrc")
            shutil.copy(lrc_file, new_lrc_path)
            QMessageBox.information(self, "成功", f"已整理到文件夹:\n{new_folder_name}")
            self.scan_music() 
        except Exception as e: QMessageBox.warning(self, "操作失败", str(e))

    def delete_song(self, idx):
        song = self.playlist[idx]
        if QMessageBox.Yes == QMessageBox.question(self, "确认", f"删除 {song['name']}?"):
            try:
                if self.current_index == idx: self.player.stop()
                os.remove(song["path"])
                lrc = os.path.splitext(song["path"])[0] + ".lrc"
                if os.path.exists(lrc): os.remove(lrc)
                self.scan_music()
            except Exception as e: QMessageBox.warning(self, "错误", str(e))

    def download_from_bilibili(self):
        if not self.music_folder: return QMessageBox.warning(self, "提示", "请先设置文件夹")
        u, ok = QInputDialog.getText(self, "B站下载", "粘贴链接 (支持BV号/合集):")
        if ok and u:
            current_p = 1
            match = re.search(r'[?&]p=(\d+)', u)
            if match: current_p = int(match.group(1))
            dialog = DownloadDialog(self, current_p)
            if dialog.exec_() == QDialog.Accepted:
                mode = dialog.get_mode()
                self.lbl_curr_time.setText("启动下载...")
                self.dl = BilibiliDownloader(u, self.music_folder, mode, current_p)
                self.dl.progress_signal.connect(lambda m: self.lbl_curr_time.setText(m))
                self.dl.finished_signal.connect(self.on_dl_finish)
                self.dl.error_signal.connect(self.on_dl_error)
                self.dl.start()
    
    def on_dl_finish(self):
        self.scan_music()
        QMessageBox.information(self, "完成", "下载任务结束")
    def on_dl_error(self, msg): QMessageBox.warning(self, "下载出错", msg)
    def select_folder(self):
        f = QFileDialog.getExistingDirectory(self, "选择目录")
        if f: self.music_folder = f; self.scan_music(); self.save_config()

    def scan_music(self):
        self.playlist = []
        self.list_widget.clear()
        if not os.path.exists(self.music_folder): return
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4')
        for root, dirs, files in os.walk(self.music_folder):
            for f in files:
                if f.lower().endswith(exts):
                    full_path = os.path.abspath(os.path.join(root, f))
                    self.playlist.append({"path": full_path, "name": f})
                    self.list_widget.addItem(os.path.splitext(f)[0])

    def play_selected(self, item): self.play_index(self.list_widget.row(item))
    def play_index(self, idx):
        if not self.playlist or idx < 0 or idx >= len(self.playlist): return
        self.current_index = idx
        song = self.playlist[idx]
        try:
            url = QUrl.fromLocalFile(song["path"])
            self.player.setMedia(QMediaContent(url))
            self.player.setPlaybackRate(self.rate)
            self.player.play()
            self.btn_play.setText("⏸")
            self.list_widget.setCurrentRow(idx)
            self.parse_lrc(os.path.splitext(song["path"])[0] + ".lrc")
        except Exception as e: print(f"Play Error: {e}")

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
            with open(path, 'r', encoding='utf-8') as f: lines = f.readlines()
        except Exception:
            try: with open(path, 'r', encoding='gbk') as f: lines = f.readlines()
            except Exception: return
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
        if self.player.state() == QMediaPlayer.PlayingState: self.player.pause()
        elif self.playlist: self.player.play()
    def toggle_mode(self):
        self.mode = (self.mode + 1) % 3
        modes = ["🔁", "🔂", "🔀"]
        self.btn_mode.setText(modes[self.mode])
    def toggle_rate(self):
        rates = [1.0, 1.25, 1.5, 2.0, 0.5]
        try: curr_idx = rates.index(self.rate)
        except: curr_idx = 0
        self.rate = rates[(curr_idx + 1) % len(rates)]
        self.player.setPlaybackRate(self.rate)
        self.btn_rate.setText(f"{self.rate}x")
    def play_next(self):
        if not self.playlist: return
        if self.mode == 2: nxt = random.randint(0, len(self.playlist)-1)
        else: nxt = (self.current_index + 1) % len(self.playlist)
        self.play_index(nxt)
    def play_prev(self):
        if not self.playlist: return
        if self.mode == 2: prev = random.randint(0, len(self.playlist)-1)
        else: prev = (self.current_index - 1) % len(self.playlist)
        self.play_index(prev)
    def on_state_changed(self, state):
        if state == QMediaPlayer.PlayingState: self.btn_play.setText("⏸")
        else: self.btn_play.setText("▶")
    def on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            if self.mode == 1: self.player.play()
            else: self.play_next()
    def handle_player_error(self):
        print(f"Error: {self.player.errorString()}")
        QTimer.singleShot(1000, self.play_next)
    def on_duration_changed(self, dur):
        self.slider.setRange(0, dur)
        self.lbl_total_time.setText(self.fmt_time(dur))
    def on_position_changed(self, pos):
        if not self.is_slider_pressed: self.slider.setValue(pos)
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
                with open(CONFIG_FILE,'r') as f:
                    self.music_folder = json.load(f).get("folder","")
                    if self.music_folder: self.scan_music()
            except: pass
    def save_config(self):
        with open(CONFIG_FILE,'w') as f: json.dump({"folder":self.music_folder},f)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(app_path, 'PyQt5', 'Qt', 'plugins')
        QCoreApplication.addLibraryPath(os.path.join(app_path, 'PyQt5', 'Qt', 'plugins'))

    app = QApplication(sys.argv)
    f = QFont("SimSun"); f.setPixelSize(14)
    app.setFont(f)
    w = SodaPlayer()
    w.show()
    sys.exit(app.exec_())

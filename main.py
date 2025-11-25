import sys
import os
import json
import shutil
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QFileDialog, QFrame, QAbstractItemView,
                             QGraphicsDropShadowEffect, QInputDialog, QMessageBox, 
                             QFontDialog, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, QUrl, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QCursor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# 引入 yt_dlp
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
    font-size: 22px; min-width: 50px; min-height: 50px;
}
QPushButton#CtrlBtn { background: transparent; border: none; font-size: 18px; color: #888; }
QPushButton#CtrlBtn:hover { color: #1ECD97; }

/* 右键菜单样式 */
QMenu { background-color: #FFFFFF; border: 1px solid #EEE; }
QMenu::item { padding: 8px 25px; background-color: transparent; }
QMenu::item:selected { background-color: #E8F5E9; color: #1ECD97; }
"""

# --- 批量下载线程 ---
class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str) # 进度消息
    finished_signal = pyqtSignal()    # 完成信号

    def __init__(self, url, folder):
        super().__init__()
        self.url = url
        self.folder = folder

    def run(self):
        if not yt_dlp:
            self.progress_signal.emit("错误：缺少 yt-dlp 组件")
            return

        # 进度回调
        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%')
                # 发送正在下载的文件名（去掉多余路径）
                filename = os.path.basename(d.get('filename', '未知'))
                self.progress_signal.emit(f"正在下载: {p} - {filename}")
            elif d['status'] == 'finished':
                self.progress_signal.emit("下载完成，正在转换...")

        ydl_opts = {
            # 关键修改：强制 m4a 格式，兼容性最好
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio', 
            'outtmpl': os.path.join(self.folder, '%(title)s.%(ext)s'),
            'noplaylist': False, # 允许列表下载
            'ignoreerrors': True, # 遇到会员视频跳过不报错
            'progress_hooks': [progress_hook],
            'quiet': True,
        }

        try:
            self.progress_signal.emit("正在解析链接...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.progress_signal.emit("✅ 全部任务处理完成")
            self.finished_signal.emit()
        except Exception as e:
            self.progress_signal.emit(f"❌ 错误: {str(e)}")

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
        self.setWindowTitle("汽水音乐 (Bilibili合集版)")
        self.resize(1080, 720)
        self.setStyleSheet(STYLESHEET)

        self.music_folder = ""
        self.playlist = [] # [{path, name}]
        self.lyrics = []
        self.current_index = -1
        self.offset = 0
        
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.stateChanged.connect(self.on_state_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)

        self.desktop_lyric = DesktopLyricWindow()
        self.desktop_lyric.show()

        self.init_ui()
        self.load_config()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. 侧边栏
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

        self.btn_bili = QPushButton("📺  B站合集下载")
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

        # 2. 右侧
        right_panel = QWidget()
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0, 0, 0, 0)
        
        content = QWidget()
        c_layout = QHBoxLayout(content)
        
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        
        # 开启右键菜单
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        c_layout.addWidget(self.list_widget, stretch=6)
        
        self.panel_lyric = QListWidget()
        self.panel_lyric.setFocusPolicy(Qt.NoFocus)
        self.panel_lyric.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.panel_lyric.setStyleSheet("color:#999; border:none;")
        c_layout.addWidget(self.panel_lyric, stretch=4)
        
        r_layout.addWidget(content)

        # 播放条
        bar = QFrame()
        bar.setObjectName("PlayerBar")
        bar.setFixedHeight(100)
        b_layout = QHBoxLayout(bar)
        
        info_l = QVBoxLayout()
        self.lbl_title = QLabel("Ready")
        self.lbl_title.setStyleSheet("font-size:16px; font-weight:bold;")
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("color:#888; font-size:12px;")
        info_l.addWidget(self.lbl_title)
        info_l.addWidget(self.lbl_time)
        b_layout.addLayout(info_l)
        b_layout.addStretch()
        
        btn_prev = QPushButton("⏮")
        btn_prev.setObjectName("CtrlBtn")
        btn_prev.clicked.connect(self.play_prev)
        
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("PlayBtn")
        self.btn_play.clicked.connect(self.toggle_play)
        
        btn_next = QPushButton("⏭")
        btn_next.setObjectName("CtrlBtn")
        btn_next.clicked.connect(self.play_next)
        
        b_layout.addWidget(btn_prev)
        b_layout.addSpacing(20)
        b_layout.addWidget(self.btn_play)
        b_layout.addSpacing(20)
        b_layout.addWidget(btn_next)
        b_layout.addStretch()

        btn_adj = QPushButton("Offset +0.5s")
        btn_adj.clicked.connect(lambda: self.adjust_offset(0.5))
        b_layout.addWidget(btn_adj)
        
        r_layout.addWidget(bar)
        layout.addWidget(right_panel)

    # --- 右键菜单功能 ---
    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return

        menu = QMenu()
        act_rename = QAction("✏️ 重命名歌曲", self)
        act_import = QAction("📝 导入/匹配歌词", self)
        act_del = QAction("🗑️ 删除歌曲", self)

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
        old_path = song["path"]
        name, ok = QInputDialog.getText(self, "重命名", "输入新名称:", text=os.path.splitext(song["name"])[0])
        if ok and name:
            new_filename = name + os.path.splitext(song["name"])[1]
            new_path = os.path.join(self.music_folder, new_filename)
            try:
                # 停止播放以释放文件占用
                if self.current_index == idx:
                    self.player.stop()
                    self.btn_play.setText("▶")
                
                os.rename(old_path, new_path)
                
                # 尝试重命名同名歌词
                old_lrc = os.path.splitext(old_path)[0] + ".lrc"
                new_lrc = os.path.join(self.music_folder, name + ".lrc")
                if os.path.exists(old_lrc):
                    os.rename(old_lrc, new_lrc)
                
                self.scan_music() # 刷新
            except Exception as e:
                QMessageBox.warning(self, "错误", f"重命名失败: {str(e)}")

    def import_lyric(self, idx):
        song = self.playlist[idx]
        file, _ = QFileDialog.getOpenFileName(self, "选择歌词文件", "", "LRC Files (*.lrc);;Text Files (*.txt)")
        if file:
            try:
                target_name = os.path.splitext(song["name"])[0] + ".lrc"
                target_path = os.path.join(self.music_folder, target_name)
                shutil.copy(file, target_path)
                QMessageBox.information(self, "成功", "歌词已导入并自动匹配")
                if self.current_index == idx:
                    self.parse_lrc(target_path)
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def delete_song(self, idx):
        song = self.playlist[idx]
        ret = QMessageBox.question(self, "确认", f"确定删除 {song['name']} 吗？\n文件将被永久删除。")
        if ret == QMessageBox.Yes:
            try:
                if self.current_index == idx:
                    self.player.stop()
                os.remove(song["path"])
                # 删歌词
                lrc = os.path.splitext(song["path"])[0] + ".lrc"
                if os.path.exists(lrc): os.remove(lrc)
                self.scan_music()
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    # --- B站下载逻辑 (支持批量) ---
    def download_from_bilibili(self):
        if not self.music_folder or not os.path.exists(self.music_folder):
            QMessageBox.warning(self, "提示", "请先设置音乐保存文件夹")
            return

        url, ok = QInputDialog.getText(self, "B站/合集下载", "输入视频或列表链接 (BV/List):")
        if ok and url:
            self.lbl_title.setText("准备开始下载...")
            self.downloader = BilibiliDownloader(url, self.music_folder)
            self.downloader.progress_signal.connect(self.on_dl_progress)
            self.downloader.finished_signal.connect(self.on_dl_finished)
            self.downloader.start()

    def on_dl_progress(self, msg):
        # 实时显示正在下载哪首歌
        self.lbl_title.setText(msg)

    def on_dl_finished(self):
        self.scan_music()
        self.lbl_title.setText("所有任务已完成")
        QMessageBox.information(self, "完成", "下载任务结束")

    # --- 基础功能 ---
    def select_folder(self):
        f = QFileDialog.getExistingDirectory(self, "选择音乐目录")
        if f:
            self.music_folder = f
            self.scan_music()
            self.save_config()

    def scan_music(self):
        self.playlist = []
        self.list_widget.clear()
        if not os.path.exists(self.music_folder): return
        
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg')
        files = [x for x in os.listdir(self.music_folder) if x.lower().endswith(exts)]
        for f in files:
            path = os.path.join(self.music_folder, f)
            self.playlist.append({"path": path, "name": f})
            self.list_widget.addItem(os.path.splitext(f)[0])

    def play_selected(self, item):
        self.play_index(self.list_widget.row(item))

    def play_index(self, idx):
        if idx < 0 or idx >= len(self.playlist): return
        self.current_index = idx
        song = self.playlist[idx]
        
        url = QUrl.fromLocalFile(song["path"])
        self.player.setMedia(QMediaContent(url))
        self.player.play()
        
        self.lbl_title.setText(os.path.splitext(song["name"])[0])
        self.btn_play.setText("⏸")
        self.list_widget.setCurrentRow(idx)
        
        lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
        self.parse_lrc(lrc_path)

    def parse_lrc(self, path):
        self.lyrics = []
        self.panel_lyric.clear()
        self.desktop_lyric.set_lyrics("", "等待歌词...", "")
        self.offset = 0
        if not os.path.exists(path): 
            self.panel_lyric.addItem("纯音乐 / 无歌词")
            return
        
        lines = []
        try:
            with open(path, 'r', encoding='utf-8') as f: lines = f.readlines()
        except:
            try: with open(path, 'r', encoding='gbk') as f: lines = f.readlines()
            except: return

        import re
        reg = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\](.*)')
        for l in lines:
            m = reg.search(l)
            if m:
                mn, sc, ms, txt = m.groups()
                ms_v = int(ms)*10 if len(ms)==2 else int(ms)
                t = int(mn)*60 + int(sc) + ms_v/1000
                if txt.strip():
                    self.lyrics.append({"t": t, "txt": txt.strip()})
                    self.panel_lyric.addItem(txt.strip())

    def on_position_changed(self, position):
        seconds = position / 1000 + self.offset
        total = self.player.duration()
        self.lbl_time.setText(f"{self.fmt_time(position)} / {self.fmt_time(total)}")
        
        if self.lyrics:
            idx = -1
            for i, line in enumerate(self.lyrics):
                if seconds >= line["t"]: idx = i
                else: break
            
            if idx != -1:
                self.panel_lyric.setCurrentRow(idx)
                self.panel_lyric.scrollToItem(self.panel_lyric.item(idx), QAbstractItemView.PositionAtCenter)
                p = self.lyrics[idx-1]["txt"] if idx>0 else ""
                c = self.lyrics[idx]["txt"]
                n = self.lyrics[idx+1]["txt"] if idx<len(self.lyrics)-1 else ""
                self.desktop_lyric.set_lyrics(p, c, n)

    def on_state_changed(self, state):
        self.btn_play.setText("⏸" if state == QMediaPlayer.PlayingState else "▶")
    def on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia: self.play_next()
    def fmt_time(self, ms):
        s = ms // 1000
        return f"{s//60:02}:{s%60:02}"
    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState: self.player.pause()
        elif self.playlist: self.player.play()
    def play_next(self):
        if self.playlist: self.play_index((self.current_index + 1) % len(self.playlist))
    def play_prev(self):
        if self.playlist: self.play_index((self.current_index - 1) % len(self.playlist))
    def adjust_offset(self, v): self.offset += v
    def toggle_lyric(self):
        if self.desktop_lyric.isVisible(): self.desktop_lyric.hide()
        else: self.desktop_lyric.show()
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.music_folder = json.load(f).get("folder", "")
                    if self.music_folder: self.scan_music()
            except: pass
    def save_config(self):
        with open(CONFIG_FILE, 'w') as f: json.dump({"folder": self.music_folder}, f)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    f = QFont("SimSun"); f.setPixelSize(14)
    app.setFont(f)
    w = SodaPlayer()
    w.show()
    sys.exit(app.exec_())

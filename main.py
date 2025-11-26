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
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize, QCoreApplication, QTimer
from PyQt5.QtGui import QFont, QColor
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

# --- 样式表 ---
STYLESHEET = """
QMainWindow { background-color: #FFFFFF; }
QWidget { font-family: "Microsoft YaHei", "SimSun", sans-serif; color: #333333; }

QFrame#Sidebar { background-color: #F7F9FC; border-right: 1px solid #EEEEEE; }
QLabel#Logo { font-size: 22px; font-weight: bold; color: #1ECD97; padding: 20px; }
QLabel#SectionTitle { font-size: 12px; color: #999; padding: 10px 20px; font-weight: bold; }

QPushButton.NavBtn {
    background-color: transparent; border: none; text-align: left; 
    padding: 10px 20px; font-size: 14px; color: #555; border-radius: 6px; margin: 2px 10px;
}
QPushButton.NavBtn:hover { background-color: #E8F5E9; color: #1ECD97; }
QPushButton.NavBtn:checked { background-color: #1ECD97; color: white; font-weight: bold; }

QPushButton#DownloadBtn { color: #FF6699; font-weight: bold; }
QPushButton#DownloadBtn:hover { background-color: #FFF0F5; }

QTableWidget { background-color: #FFFFFF; border: none; outline: none; selection-background-color: #FFF8E1; selection-color: #F9A825; }
QHeaderView::section { background-color: #FFFFFF; border: none; border-bottom: 1px solid #EEE; padding: 5px; font-weight: bold; color: #888; }

QFrame#PlayerBar { background-color: #FFFFFF; border-top: 1px solid #F0F0F0; }
QPushButton#PlayBtn { 
    background-color: #1ECD97; color: white; border-radius: 25px; 
    font-size: 20px; min-width: 50px; min-height: 50px;
}
QPushButton#PlayBtn:hover { background-color: #18c48f; }

QPushButton.CtrlBtn { background: transparent; border: none; font-size: 16px; color: #666; }
QPushButton.CtrlBtn:hover { color: #1ECD97; background-color: #F0F0F0; border-radius: 4px; }

QPushButton.OffsetBtn { background: #F5F5F5; border: 1px solid #DDD; border-radius: 4px; color: #666; font-size: 10px; padding: 2px 5px; }
QPushButton.OffsetBtn:hover { background: #E8F5E9; border-color: #1ECD97; color: #1ECD97; }

QSlider::groove:horizontal { border: 1px solid #EEE; height: 6px; background: #F0F0F0; margin: 2px 0; border-radius: 3px; }
QSlider::handle:horizontal { background: #1ECD97; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }
QSlider::sub-page:horizontal { background: #1ECD97; border-radius: 3px; }
"""

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def ms_to_str(ms):
    s = ms // 1000
    return f"{s//60:02}:{s%60:02}"

# --- 1. 在线歌词搜索线程 ---
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
                    results.append({
                        'name': s['name'],
                        'artist': artist,
                        'id': s['id'],
                        'duration': duration,
                        'duration_str': ms_to_str(duration)
                    })
            self.search_finished.emit(results)
        except Exception as e:
            print(f"Search error: {e}")
            self.search_finished.emit([])

# --- 2. 手动歌词搜索弹窗 ---
class LyricSearchDialog(QDialog):
    def __init__(self, song_name, duration_ms=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("在线歌词搜索与绑定")
        self.resize(700, 500)
        self.result_id = None
        self.duration_ms = duration_ms 
        
        layout = QVBoxLayout(self)
        h = QHBoxLayout()
        self.input_key = QLineEdit(song_name)
        btn = QPushButton("搜索网易云")
        btn.clicked.connect(self.start_search)
        h.addWidget(self.input_key)
        h.addWidget(btn)
        layout.addLayout(h)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["歌名", "歌手", "时长", "ID"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemDoubleClicked.connect(self.on_select)
        layout.addWidget(self.table)
        
        if duration_ms > 0:
            layout.addWidget(QLabel(f"当前本地歌曲时长: {ms_to_str(duration_ms)} (供参考)", styleSheet="color:#666"))
        
        btn_bind = QPushButton("选中并绑定歌词")
        btn_bind.setStyleSheet("background-color:#1ECD97; color:white; font-weight:bold; padding:8px;")
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
                t_item.setForeground(QColor("#1ECD97"))
                t_item.setToolTip("时长匹配度极高")
            self.table.setItem(i, 2, t_item)
            self.table.setItem(i, 3, QTableWidgetItem(str(item['id'])))

    def on_select(self, item):
        self.confirm_bind()

    def confirm_bind(self):
        row = self.table.currentRow()
        if row >= 0:
            self.result_id = self.table.item(row, 3).text()
            self.accept()
        else:
            QMessageBox.warning(self, "提示", "请先选择一行")

# --- 歌词下载线程 ---
class LyricDownloader(QThread):
    finished_signal = pyqtSignal(str)
    
    def __init__(self, song_id, save_path):
        super().__init__()
        self.sid = song_id
        self.path = save_path
        
    def run(self):
        try:
            url = f"http://music.163.com/api/song/lyric?os=pc&id={self.sid}&lv=-1&kv=-1&tv=-1"
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as f:
                res = json.loads(f.read().decode('utf-8'))
            
            if 'lrc' in res and 'lyric' in res['lrc']:
                lrc = res['lrc']['lyric']
                with open(self.path, 'w', encoding='utf-8') as f:
                    f.write(lrc)
                self.finished_signal.emit(lrc)
        except: pass

# --- 3. 批量信息编辑弹窗 ---
class BatchInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量修改歌曲信息")
        self.resize(300, 200)
        layout = QVBoxLayout(self)
        
        self.check_artist = QCheckBox("修改歌手为:")
        self.input_artist = QLineEdit()
        
        self.check_album = QCheckBox("修改专辑为:")
        self.input_album = QLineEdit()
        
        layout.addWidget(self.check_artist)
        layout.addWidget(self.input_artist)
        layout.addSpacing(10)
        layout.addWidget(self.check_album)
        layout.addWidget(self.input_album)
        
        btn_box = QHBoxLayout()
        btn_ok = QPushButton("确定")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)
        
    def get_data(self):
        artist = self.input_artist.text() if self.check_artist.isChecked() else None
        album = self.input_album.text() if self.check_album.isChecked() else None
        return artist, album

# --- 4. 批量重命名弹窗 ---
class BatchRenameDialog(QDialog):
    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量重命名")
        self.resize(500, 600)
        self.playlist = playlist
        self.selected_indices = []
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # Tab 1
        tab_replace = QWidget()
        l1 = QVBoxLayout(tab_replace)
        h1 = QHBoxLayout()
        self.input_find = QLineEdit(); self.input_find.setPlaceholderText("查找")
        self.input_replace = QLineEdit(); self.input_replace.setPlaceholderText("替换为")
        h1.addWidget(QLabel("查找:")); h1.addWidget(self.input_find)
        h1.addWidget(QLabel("替换:")); h1.addWidget(self.input_replace)
        l1.addLayout(h1); l1.addStretch()
        self.tabs.addTab(tab_replace, "文本替换")
        
        # Tab 2
        tab_trim = QWidget()
        l2 = QVBoxLayout(tab_trim)
        h2 = QHBoxLayout()
        self.spin_head = QSpinBox(); self.spin_head.setRange(0, 50)
        self.spin_tail = QSpinBox(); self.spin_tail.setRange(0, 50)
        h2.addWidget(QLabel("删前N字:")); h2.addWidget(self.spin_head)
        h2.addWidget(QLabel("删后N字:")); h2.addWidget(self.spin_tail)
        l2.addLayout(h2); l2.addStretch()
        self.tabs.addTab(tab_trim, "字符裁剪")
        
        layout.addWidget(self.tabs)
        
        self.list_view = QListWidget()
        for song in self.playlist:
            item = QListWidgetItem(song["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list_view.addItem(item)
        layout.addWidget(self.list_view)
        
        h_sel = QHBoxLayout()
        btn_all = QPushButton("全选"); btn_all.clicked.connect(lambda: self.set_all(True))
        btn_none = QPushButton("全不选"); btn_none.clicked.connect(lambda: self.set_all(False))
        h_sel.addWidget(btn_all); h_sel.addWidget(btn_none); h_sel.addStretch()
        layout.addLayout(h_sel)
        
        btn_ok = QPushButton("执行"); btn_ok.clicked.connect(self.on_accept)
        layout.addWidget(btn_ok)

    def set_all(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.list_view.count()): self.list_view.item(i).setCheckState(state)

    def on_accept(self):
        self.selected_indices = []
        for i in range(self.list_view.count()):
            if self.list_view.item(i).checkState() == Qt.Checked:
                self.selected_indices.append(i)
        self.accept()

    def get_data(self):
        idx = self.tabs.currentIndex()
        if idx == 0: return "replace", (self.input_find.text(), self.input_replace.text()), self.selected_indices
        else: return "trim", (self.spin_head.value(), self.spin_tail.value()), self.selected_indices

# --- 5. 桌面歌词 ---
class DesktopLyricWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1200, 180)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        self.font_color = QColor(255, 255, 255)
        self.current_font = QFont("SimSun", 36, QFont.Bold)
        
        self.labels = []
        for i in range(3):
            lbl = QLabel("")
            lbl.setAlignment(Qt.AlignCenter)
            self.labels.append(lbl)
            self.layout.addWidget(lbl)
        
        self.update_styles()
        self.locked = False

    def update_styles(self):
        base_size = self.current_font.pointSize()
        shadow_color = QColor(0, 0, 0, 200)
        for i, lbl in enumerate(self.labels):
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(8); effect.setColor(shadow_color); effect.setOffset(1, 1)
            lbl.setGraphicsEffect(effect)
            f = QFont(self.current_font)
            color_css = self.font_color.name()
            if i == 1:
                f.setPointSize(base_size)
                lbl.setStyleSheet(f"color: {color_css};")
            else:
                f.setPointSize(int(base_size * 0.6))
                r,g,b = self.font_color.red(), self.font_color.green(), self.font_color.blue()
                lbl.setStyleSheet(f"color: rgba({r}, {g}, {b}, 160);")
            lbl.setFont(f)

    def set_lyrics(self, p, c, n):
        self.labels[0].setText(p); self.labels[1].setText(c); self.labels[2].setText(n)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.locked:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton: self.show_menu(event.globalPos())
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.locked:
            self.move(event.globalPos() - self.drag_pos)
    def wheelEvent(self, event):
        d = event.angleDelta().y()
        s = self.current_font.pointSize()
        self.current_font.setPointSize(min(120, s+2) if d>0 else max(15, s-2))
        self.update_styles()

    def show_menu(self, pos):
        menu = QMenu()
        act_color = menu.addAction("🎨 修改颜色")
        act_font = menu.addAction("🅰️ 修改字体")
        lock_text = "🔒 解锁位置" if self.locked else "🔒 锁定位置"
        act_lock = menu.addAction(lock_text)
        act_close = menu.addAction("❌ 隐藏歌词")
        action = menu.exec_(pos)
        if action == act_color:
            c = QColorDialog.getColor(self.font_color, self)
            if c.isValid(): self.font_color = c; self.update_styles()
        elif action == act_font:
            f, ok = QFontDialog.getFont(self.current_font, self)
            if ok: self.current_font = f; self.update_styles()
        elif action == act_lock: self.locked = not self.locked
        elif action == act_close: self.hide()

# --- 6. 下载选项弹窗 ---
class DownloadDialog(QDialog):
    def __init__(self, parent=None, current_p=1, collections=[]):
        super().__init__(parent)
        self.setWindowTitle("下载选项")
        self.resize(400, 350)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"包含分P (第 {current_p} 集)，请选择："))
        self.rb_single = QRadioButton(f"单曲 (P{current_p})")
        self.rb_list = QRadioButton(f"合集 (P{current_p} - 结尾)")
        self.rb_single.setChecked(True)
        layout.addWidget(self.rb_single); layout.addWidget(self.rb_list)
        
        layout.addSpacing(10)
        layout.addWidget(QLabel("存入合集："))
        self.combo_coll = QComboBox()
        self.combo_coll.addItem("根目录", "")
        for c in collections: self.combo_coll.addItem(f"📁 {c}", c)
        self.combo_coll.addItem("➕ 新建合集...", "NEW")
        layout.addWidget(self.combo_coll)
        self.input_new = QLineEdit(); self.input_new.setPlaceholderText("新合集名称"); self.input_new.hide()
        layout.addWidget(self.input_new)
        self.combo_coll.currentIndexChanged.connect(self.on_combo_change)

        layout.addSpacing(10)
        layout.addWidget(QLabel("预设信息 (可选):"))
        self.input_artist = QLineEdit(); self.input_artist.setPlaceholderText("歌手 (例如: 周杰伦)")
        self.input_album = QLineEdit(); self.input_album.setPlaceholderText("专辑 (例如: 七里香)")
        layout.addWidget(self.input_artist); layout.addWidget(self.input_album)
        
        btn_box = QHBoxLayout()
        btn_ok = QPushButton("开始下载"); btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消"); btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_ok); btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def on_combo_change(self):
        if self.combo_coll.currentData() == "NEW": self.input_new.show(); self.input_new.setFocus()
        else: self.input_new.hide()
    def get_data(self):
        mode = "playlist" if self.rb_list.isChecked() else "single"
        folder = self.combo_coll.currentData()
        if folder == "NEW": folder = self.input_new.text().strip()
        return mode, folder, self.input_artist.text(), self.input_album.text()

# --- B站下载线程 ---
class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str, str) 
    error_signal = pyqtSignal(str)

    def __init__(self, url, save_path, mode="single", start_p=1):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.mode = mode
        self.start_p = start_p

    def run(self):
        if not yt_dlp: return self.error_signal.emit("错误：缺少 yt-dlp")
        if not os.path.exists(self.save_path):
            try: os.makedirs(self.save_path)
            except Exception as e: return self.error_signal.emit(f"无法建文件夹: {e}")

        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%')
                fn = os.path.basename(d.get('filename', '未知'))
                if len(fn)>20: fn = fn[:20]+"..."
                self.progress_signal.emit(f"⬇️ {p} : {fn}")
            elif d['status'] == 'finished':
                self.progress_signal.emit("✅ 下载完成，处理中...")

        items_range = str(self.start_p) if self.mode == 'single' else f"{self.start_p}-"
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/best[ext=mp4]/best', 
            'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
            'overwrites': True, 'noplaylist': False, 'playlist_items': items_range,
            'ignoreerrors': True, 'progress_hooks': [progress_hook], 'quiet': True,
            'nocheckcertificate': True, 'restrictfilenames': False,
        }
        try:
            self.progress_signal.emit(f"🔍 开始解析...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([self.url])
            self.progress_signal.emit("🎉 任务完成")
            self.finished_signal.emit(self.save_path, "{}") 
        except Exception as e: self.error_signal.emit(f"❌: {str(e)}")

# --- 主程序 ---
class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 (最终完全体)")
        self.resize(1150, 780)
        self.setStyleSheet(STYLESHEET)

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
        
        # 侧边栏
        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(250)
        self.side_layout = QVBoxLayout(sidebar)
        self.side_layout.addWidget(QLabel("🧼 SODA MUSIC", objectName="Logo"))

        self.btn_bili = QPushButton("📺  B站下载"); self.btn_bili.setObjectName("DownloadBtn"); self.btn_bili.setProperty("NavBtn", True)
        self.btn_bili.clicked.connect(self.download_from_bilibili)
        self.side_layout.addWidget(self.btn_bili)

        btn_refresh = QPushButton("🔄  刷新数据"); btn_refresh.setProperty("NavBtn", True)
        btn_refresh.clicked.connect(self.full_scan)
        self.side_layout.addWidget(btn_refresh)
        
        # 导航
        self.side_layout.addWidget(QLabel("我的音乐", objectName="SectionTitle"))
        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet("background:transparent; border:none;")
        self.nav_list.itemClicked.connect(self.switch_collection)
        self.side_layout.addWidget(self.nav_list)
        
        # 底部按钮
        self.side_layout.addStretch()
        btn_move = QPushButton("🚚  批量移动"); btn_move.setProperty("NavBtn", True)
        btn_move.clicked.connect(self.open_batch_move_dialog)
        self.side_layout.addWidget(btn_move)
        
        btn_folder = QPushButton("📁  根目录"); btn_folder.setProperty("NavBtn", True)
        btn_folder.clicked.connect(self.select_folder)
        self.side_layout.addWidget(btn_folder)
        btn_lyric = QPushButton("💬  桌面歌词"); btn_lyric.setProperty("NavBtn", True)
        btn_lyric.clicked.connect(self.toggle_lyric)
        self.side_layout.addWidget(btn_lyric)
        layout.addWidget(sidebar)

        # 右侧
        right_panel = QWidget(); r_layout = QVBoxLayout(right_panel); r_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_collection_title = QLabel("全部音乐")
        self.lbl_collection_title.setStyleSheet("font-size:18px; font-weight:bold; padding:15px; color:#444;")
        r_layout.addWidget(self.lbl_collection_title)

        content = QWidget(); c_layout = QHBoxLayout(content)
        
        # 列表
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["歌曲标题", "歌手", "专辑", "时长"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.itemDoubleClicked.connect(self.play_selected)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        c_layout.addWidget(self.table, stretch=6)
        
        self.panel_lyric = QListWidget(); self.panel_lyric.setFocusPolicy(Qt.NoFocus)
        self.panel_lyric.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.panel_lyric.setStyleSheet("color:#999; border:none;")
        c_layout.addWidget(self.panel_lyric, stretch=4)
        r_layout.addWidget(content)

        # 播放条
        bar = QFrame(); bar.setObjectName("PlayerBar"); bar.setFixedHeight(120)
        bar_v = QVBoxLayout(bar)
        progress = QHBoxLayout()
        self.lbl_curr_time = QLabel("00:00"); self.lbl_total_time = QLabel("00:00")
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(0, 0)
        self.slider.sliderPressed.connect(self.slider_pressed)
        self.slider.sliderReleased.connect(self.slider_released)
        self.slider.valueChanged.connect(self.slider_moved)
        progress.addWidget(self.lbl_curr_time); progress.addWidget(self.slider); progress.addWidget(self.lbl_total_time)
        bar_v.addLayout(progress)
        
        ctrl = QHBoxLayout()
        self.btn_mode = QPushButton("🔁"); self.btn_mode.setProperty("CtrlBtn", True); self.btn_mode.clicked.connect(self.toggle_mode)
        btn_prev = QPushButton("⏮"); btn_prev.setProperty("CtrlBtn", True); btn_prev.clicked.connect(self.play_prev)
        self.btn_play = QPushButton("▶"); self.btn_play.setObjectName("PlayBtn"); self.btn_play.clicked.connect(self.toggle_play)
        btn_next = QPushButton("⏭"); btn_next.setProperty("CtrlBtn", True); btn_next.clicked.connect(self.play_next)
        self.btn_rate = QPushButton("1.0x"); self.btn_rate.setProperty("CtrlBtn", True); self.btn_rate.clicked.connect(self.toggle_rate)
        ctrl.addStretch(); ctrl.addWidget(self.btn_mode); ctrl.addSpacing(15); ctrl.addWidget(btn_prev)
        ctrl.addWidget(self.btn_play); ctrl.addWidget(btn_next); ctrl.addSpacing(15); ctrl.addWidget(self.btn_rate); ctrl.addStretch()
        
        offset_l = QHBoxLayout()
        btn_slow = QPushButton("⏪"); btn_slow.setProperty("OffsetBtn", True); btn_slow.clicked.connect(lambda: self.adjust_offset(-0.5))
        self.lbl_offset = QLabel("0.0s"); self.lbl_offset.setStyleSheet("color:#999; font-size:10px;")
        btn_fast = QPushButton("⏩"); btn_fast.setProperty("OffsetBtn", True); btn_fast.clicked.connect(lambda: self.adjust_offset(0.5))
        offset_l.addStretch(); offset_l.addWidget(btn_slow); offset_l.addWidget(self.lbl_offset); offset_l.addWidget(btn_fast)
        
        bar_v.addLayout(ctrl); bar_v.addLayout(offset_l)
        r_layout.addWidget(bar); layout.addWidget(right_panel)

    # --- 扫描逻辑 ---
    def full_scan(self):
        if not self.music_folder or not os.path.exists(self.music_folder): return
        self.collections = []
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4')
        
        for item in os.listdir(self.music_folder):
            full_path = os.path.join(self.music_folder, item)
            if os.path.isdir(full_path):
                files = [x for x in os.listdir(full_path) if x.lower().endswith(exts)]
                if len(files) <= 1:
                    if len(files) == 1:
                        song_base = os.path.splitext(files[0])[0]
                        if item in song_base or song_base in item: continue
                self.collections.append(item)
        
        self.nav_list.clear()
        self.nav_list.addItem("💿  所有歌曲") 
        self.nav_list.addItem("🕒  最近播放")
        for c in self.collections: self.nav_list.addItem(f"📁  {c}")
        
        if self.current_collection == "HISTORY":
            self.load_history_view()
        elif not self.current_collection or self.current_collection not in self.collections:
            self.current_collection = ""
            self.load_songs_for_collection()
        else:
            self.load_songs_for_collection()

    def switch_collection(self, item):
        text = item.text()
        if "所有歌曲" in text:
            self.current_collection = ""
            self.lbl_collection_title.setText("全部音乐")
            self.load_songs_for_collection()
        elif "最近播放" in text:
            self.current_collection = "HISTORY"
            self.lbl_collection_title.setText("最近播放")
            self.load_history_view()
        else:
            self.current_collection = text.replace("📁  ", "")
            self.lbl_collection_title.setText(f"合集：{self.current_collection}")
            self.load_songs_for_collection()

    def load_songs_for_collection(self):
        self.playlist = []
        self.table.setRowCount(0)
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4')
        
        target_dirs = []
        if self.current_collection:
            target_dirs = [os.path.join(self.music_folder, self.current_collection)]
        else:
            target_dirs = [self.music_folder]
            for item in os.listdir(self.music_folder):
                p = os.path.join(self.music_folder, item)
                if os.path.isdir(p): target_dirs.append(p)

        row = 0
        for d in target_dirs:
            if not os.path.exists(d): continue
            for f in os.listdir(d):
                if f.lower().endswith(exts):
                    full = os.path.abspath(os.path.join(d, f))
                    meta = self.metadata.get(f, {"artist": "未知", "album": "未知"})
                    
                    song_data = {"path": full, "name": f, "artist": meta.get("artist"), "album": meta.get("album")}
                    self.playlist.append(song_data)
                    
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(os.path.splitext(f)[0]))
                    self.table.setItem(row, 1, QTableWidgetItem(meta.get("artist", "")))
                    self.table.setItem(row, 2, QTableWidgetItem(meta.get("album", "")))
                    self.table.setItem(row, 3, QTableWidgetItem("-"))
                    row += 1

    def load_history_view(self):
        self.playlist = []
        self.table.setRowCount(0)
        row = 0
        for song in self.history:
            if os.path.exists(song["path"]):
                self.playlist.append(song)
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(os.path.splitext(song["name"])[0]))
                self.table.setItem(row, 1, QTableWidgetItem(song.get("artist", "")))
                self.table.setItem(row, 2, QTableWidgetItem(song.get("album", "")))
                row += 1

    # --- 右键菜单 ---
    def show_context_menu(self, pos):
        items = self.table.selectedItems()
        if not items: return
        selected_rows = sorted(list(set(i.row() for i in items)))
        menu = QMenu()
        
        # 批量移动
        act_move = QMenu("📂 批量移动到...", self)
        act_root = QAction("💿 根目录", self)
        act_root.triggered.connect(lambda: self.batch_move(selected_rows, ""))
        act_move.addAction(act_root)
        act_move.addSeparator()
        for c in self.collections:
            if c != self.current_collection:
                a = QAction(f"📁 {c}", self)
                a.triggered.connect(lambda ch, t=c: self.batch_move(selected_rows, t))
                act_move.addAction(a)
        menu.addMenu(act_move)

        menu.addAction("🔠 批量重命名", self.open_batch_rename)
        menu.addAction("✏️ 批量修改信息", lambda: self.batch_edit_info(selected_rows))
        menu.addSeparator()

        if len(selected_rows) == 1:
            idx = selected_rows[0]
            menu.addAction("🔐 绑定歌词 (整理)", lambda: self.bind_lyrics(idx))
            menu.addAction("🔍 手动搜索歌词", lambda: self.open_manual_search(idx))
            menu.addAction("❌ 删除/解绑歌词", lambda: self.remove_lyric(idx))
        
        menu.addAction(f"🗑️ 删除 ({len(selected_rows)}首)", lambda: self.delete_songs(selected_rows))
        
        menu.exec_(self.table.mapToGlobal(pos))

    def open_batch_move_dialog(self):
        selected_rows = sorted(list(set(i.row() for i in self.table.selectedItems())))
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先在列表中选择要移动的歌曲")
            return
        dest_list = ["根目录"] + self.collections
        target, ok = QInputDialog.getItem(self, "批量移动", "选择目标合集:", dest_list, 0, False)
        if ok and target:
            target_folder = "" if target == "根目录" else target
            self.batch_move(selected_rows, target_folder)

    def batch_move(self, rows, target_name):
        self.player.setMedia(QMediaContent())
        target_path = self.music_folder if not target_name else os.path.join(self.music_folder, target_name)
        if not os.path.exists(target_path): os.makedirs(target_path)
        files_to_move = [self.playlist[i] for i in rows]
        count = 0
        for song in files_to_move:
            try:
                src = song["path"]
                dst = os.path.join(target_path, song["name"])
                if src == dst: continue
                shutil.move(src, dst)
                lrc_src = os.path.splitext(src)[0] + ".lrc"
                if os.path.exists(lrc_src):
                    shutil.move(lrc_src, os.path.join(target_path, os.path.basename(lrc_src)))
                count += 1
            except: pass
        self.full_scan(); QMessageBox.information(self, "成功", f"已移动 {count} 首")

    def batch_edit_info(self, rows):
        d = BatchInfoDialog(self)
        if d.exec_() == QDialog.Accepted:
            artist, album = d.get_data()
            for i in rows:
                if i < len(self.playlist):
                    fname = self.playlist[i]["name"]
                    if artist: self.metadata.setdefault(fname, {})["artist"] = artist
                    if album: self.metadata.setdefault(fname, {})["album"] = album
            self.save_metadata()
            self.full_scan()

    def download_from_bilibili(self):
        if not self.music_folder: return QMessageBox.warning(self, "提示", "请先设置根文件夹")
        u, ok = QInputDialog.getText(self, "B站下载", "粘贴链接:")
        if ok and u:
            p=1
            m=re.search(r'[?&]p=(\d+)', u)
            if m: p=int(m.group(1))
            dialog = DownloadDialog(self, p, self.collections)
            if dialog.exec_() == QDialog.Accepted:
                mode, folder, artist, album = dialog.get_data()
                path = self.music_folder
                if folder: path = os.path.join(path, folder)
                self.temp_dl_artist = artist
                self.temp_dl_album = album
                self.lbl_collection_title.setText("⏳ 下载中...")
                self.dl = BilibiliDownloader(u, path, mode, p)
                self.dl.progress_signal.connect(lambda s: self.lbl_collection_title.setText(s))
                self.dl.finished_signal.connect(self.on_dl_finish)
                self.dl.error_signal.connect(self.on_dl_error)
                self.dl.start()
    
    def on_dl_finish(self, folder, info_json):
        for f in os.listdir(folder):
            if f.lower().endswith(('.m4a', '.mp4')):
                if f not in self.metadata:
                    if self.temp_dl_artist or self.temp_dl_album:
                        self.metadata[f] = {}
                        if self.temp_dl_artist: self.metadata[f]["artist"] = self.temp_dl_artist
                        if self.temp_dl_album: self.metadata[f]["album"] = self.temp_dl_album
        self.save_metadata()
        self.full_scan()
        self.lbl_collection_title.setText("下载完成")

    def on_dl_error(self, m): QMessageBox.warning(self, "错", m)

    def open_manual_search(self, idx):
        song = self.playlist[idx]
        duration = self.player.duration() if self.current_index == idx else 0
        d = LyricSearchDialog(os.path.splitext(song["name"])[0], duration, self)
        if d.exec_() == QDialog.Accepted and d.result_id:
            lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
            self.lrc_dl = LyricDownloader(d.result_id, lrc_path)
            self.lrc_dl.finished_signal.connect(lambda c: self.on_lrc_bound(c, idx))
            self.lrc_dl.start()

    def on_lrc_bound(self, content, idx):
        if self.current_index == idx: self.parse_lrc_content(content)
        QMessageBox.information(self, "成功", "歌词已绑定")

    def open_batch_rename(self):
        if not self.playlist: return
        self.player.setMedia(QMediaContent())
        d = BatchRenameDialog(self.playlist, self)
        if d.exec_() == QDialog.Accepted:
            mode, p, idxs = d.get_data()
            count = 0
            targets = [self.playlist[i] for i in idxs if i < len(self.playlist)]
            for s in targets:
                old = s["path"]; base, ext = os.path.splitext(s["name"])
                new_base = base
                if mode=="replace": 
                    if p[0] in new_base: new_base = new_base.replace(p[0], p[1])
                elif mode=="trim":
                    if p[0]>0: new_base = new_base[p[0]:]
                    if p[1]>0: new_base = new_base[:-p[1]]
                nn = new_base.strip()+ext; np = os.path.join(os.path.dirname(old), nn)
                if np!=old:
                    try: os.rename(old, np); count+=1
                    except: pass
            self.full_scan()
            QMessageBox.information(self, "完成", f"重命名 {count} 个")

    def rename_song(self, idx):
        self.player.setMedia(QMediaContent())
        s = self.playlist[idx]; old=s["path"]
        n, ok = QInputDialog.getText(self, "重命名", "新名:", text=os.path.splitext(s["name"])[0])
        if ok and n:
            np = os.path.join(os.path.dirname(old), sanitize_filename(n)+os.path.splitext(s["name"])[1])
            try: os.rename(old, np); self.full_scan()
            except Exception as e: print(e)

    def delete_songs(self, rows):
        if QMessageBox.Yes == QMessageBox.question(self, "确认", f"删除 {len(rows)} 首歌？"):
            self.player.setMedia(QMediaContent())
            for i in rows:
                if i < len(self.playlist):
                    try: os.remove(self.playlist[i]["path"])
                    except: pass
            self.full_scan()

    def bind_lyrics(self, idx):
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

    def remove_lyric(self, idx):
        p = os.path.splitext(self.playlist[idx]["path"])[0] + ".lrc"
        if os.path.exists(p):
            os.remove(p)
            if self.current_index == idx: self.parse_lrc_content("")
            QMessageBox.information(self, "完成", "已删除")

    def select_folder(self):
        f = QFileDialog.getExistingDirectory(self, "根目录")
        if f: self.music_folder=f; self.full_scan(); self.save_config()

    def create_collection(self):
        if not self.music_folder: return
        n, ok = QInputDialog.getText(self, "新建", "名称:")
        if ok and n:
            os.makedirs(os.path.join(self.music_folder, sanitize_filename(n)), exist_ok=True)
            self.full_scan()

    def play_selected(self, item): self.play_index(item.row())
    def play_index(self, idx):
        if not self.playlist or idx >= len(self.playlist): return
        self.current_index = idx
        song = self.playlist[idx]
        
        if song not in self.history:
            self.history.insert(0, song)
            if len(self.history) > 50: self.history.pop()
            self.save_history()
            
        try:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(song["path"])))
            self.player.setPlaybackRate(self.rate); self.player.play()
            self.btn_play.setText("⏸")
            
            self.offset = self.saved_offsets.get(song["name"], 0.0)
            self.update_offset_lbl()
            
            lrc = os.path.splitext(song["path"])[0]+".lrc"
            if os.path.exists(lrc): self.parse_lrc_file(lrc)
            else:
                self.panel_lyric.clear(); self.panel_lyric.addItem("搜索中...")
                self.searcher = LyricListSearchWorker(song["name"])
                self.searcher.search_finished.connect(self.on_auto_lrc_result)
                self.searcher.start()
        except: pass

    def on_auto_lrc_result(self, results):
        if results and self.current_index >= 0:
            best = results[0]
            lrc_path = os.path.splitext(self.playlist[self.current_index]["path"])[0] + ".lrc"
            self.adl = LyricDownloader(best['id'], lrc_path)
            self.adl.finished_signal.connect(self.parse_lrc_content)
            self.adl.start()
        else:
            self.panel_lyric.clear(); self.panel_lyric.addItem("无歌词")

    def parse_lrc_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f: self.parse_lrc_content(f.read())
        except:
            try:
                with open(path, 'r', encoding='gbk') as f: self.parse_lrc_content(f.read())
            except: pass

    def parse_lrc_content(self, content):
        self.lyrics = []
        self.panel_lyric.clear()
        p = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\](.*)')
        for l in content.splitlines():
            m = p.search(l)
            if m:
                mn, sc, ms, t = m.groups()
                ms_v = int(ms)*10 if len(ms)==2 else int(ms)
                tm = int(mn)*60 + int(sc) + ms_v/1000
                if t.strip():
                    self.lyrics.append({"t": tm, "txt": t.strip()})
                    self.panel_lyric.addItem(t.strip())
    def adjust_offset(self, v):
        self.offset += v
        self.update_offset_lbl()
        if self.current_index >= 0:
            self.saved_offsets[self.playlist[self.current_index]["name"]] = self.offset
            self.save_offsets()
    def update_offset_lbl(self):
        s = "+" if self.offset >= 0 else ""
        self.lbl_offset.setText(f"偏移: {s}{self.offset:.1f}s")
    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState: self.player.pause()
        else: self.player.play()
    def toggle_mode(self):
        self.mode = (self.mode + 1) % 3; modes = ["🔁", "🔂", "🔀"]; self.btn_mode.setText(modes[self.mode])
    def toggle_rate(self):
        rs=[1.0,1.25,1.5,2.0,0.5]; 
        try: i=rs.index(self.rate)
        except: i=0
        self.rate=rs[(i+1)%5]; self.player.setPlaybackRate(self.rate); self.btn_rate.setText(f"{self.rate}x")
    def play_next(self):
        if not self.playlist: return
        n = random.randint(0, len(self.playlist)-1) if self.mode==2 else (self.current_index+1)%len(self.playlist)
        self.play_index(n)
    def play_prev(self):
        if not self.playlist: return
        p = random.randint(0, len(self.playlist)-1) if self.mode==2 else (self.current_index-1)%len(self.playlist)
        self.play_index(p)
    def on_state_changed(self, s): self.btn_play.setText("⏸" if s==QMediaPlayer.PlayingState else "▶")
    def on_media_status_changed(self, s): 
        if s==QMediaPlayer.EndOfMedia: 
            if self.mode==1: self.player.play() 
            else: self.play_next()
    def on_position_changed(self, pos):
        if not self.is_slider_pressed: self.slider.setValue(pos)
        self.lbl_curr_time.setText(ms_to_str(pos))
        sec = pos/1000 + self.offset
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
    def slider_released(self): self.is_slider_pressed = False; self.player.setPosition(self.slider.value())
    def slider_moved(self, v): 
        if self.is_slider_pressed: self.lbl_curr_time.setText(ms_to_str(v))
    def on_duration_changed(self, d): 
        self.slider.setRange(0, d); self.lbl_total_time.setText(ms_to_str(d))
        if self.current_index >= 0:
            self.table.setItem(self.current_index, 3, QTableWidgetItem(ms_to_str(d)))
    def toggle_lyric(self): 
        if self.desktop_lyric.isVisible(): self.desktop_lyric.hide()
        else: self.desktop_lyric.show()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try: 
                with open(CONFIG_FILE,'r') as f: 
                    d = json.load(f)
                    self.music_folder=d.get("folder","")
                    geo = d.get("lyric_geo")
                    if geo: self.desktop_lyric.setGeometry(*geo)
                    col = d.get("lyric_color")
                    if col: self.desktop_lyric.font_color = QColor(*col); self.desktop_lyric.update_styles()
                if self.music_folder: self.full_scan()
            except:pass
        if os.path.exists(OFFSET_FILE):
            try: with open(OFFSET_FILE,'r') as f: self.saved_offsets=json.load(f)
            except:pass
        if os.path.exists(METADATA_FILE):
            try: with open(METADATA_FILE,'r') as f: self.metadata=json.load(f)
            except:pass
        if os.path.exists(HISTORY_FILE):
            try: with open(HISTORY_FILE,'r') as f: self.history=json.load(f)
            except:pass

    def save_config(self): 
        data = {
            "folder": self.music_folder,
            "lyric_geo": self.desktop_lyric.geometry().getRect(),
            "lyric_color": self.desktop_lyric.font_color.getRgb()[:3]
        }
        with open(CONFIG_FILE,'w') as f: json.dump(data,f)
    def save_offsets(self): with open(OFFSET_FILE,'w') as f: json.dump(self.saved_offsets,f)
    def save_metadata(self): with open(METADATA_FILE,'w') as f: json.dump(self.metadata,f)
    def save_history(self): with open(HISTORY_FILE,'w') as f: json.dump(self.history,f)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(app_path, 'PyQt5', 'Qt', 'plugins')
        QCoreApplication.addLibraryPath(os.path.join(app_path, 'PyQt5', 'Qt', 'plugins'))
    app = QApplication(sys.argv)
    f = QFont("Microsoft YaHei", 10); app.setFont(f)
    w = SodaPlayer(); w.show(); sys.exit(app.exec_())

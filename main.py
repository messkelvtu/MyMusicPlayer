import sys
import os
import json
import shutil
import random
import threading
import re
import urllib.request
import urllib.parse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QFileDialog, QFrame, QAbstractItemView, QCheckBox,
                             QGraphicsDropShadowEffect, QInputDialog, QMessageBox, 
                             QFontDialog, QMenu, QAction, QSlider, QDialog, QRadioButton, 
                             QComboBox, QLineEdit, QTabWidget, QSpinBox, QColorDialog, QTableWidget, QTableWidgetItem, QHeaderView)
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
OFFSET_FILE = "offsets.json"

# --- 样式表 ---
STYLESHEET = """
QMainWindow { background-color: #FFFFFF; }
QWidget { font-family: "Microsoft YaHei", "SimSun", sans-serif; color: #333333; }

/* 侧边栏 */
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

/* 列表 */
QListWidget { background-color: #FFFFFF; border: none; outline: none; }
QListWidget::item { padding: 8px; margin: 1px 10px; border-bottom: 1px solid #FAFAFA; }
QListWidget::item:selected { background-color: #FFF8E1; color: #F9A825; }

/* 播放条 */
QFrame#PlayerBar { background-color: #FFFFFF; border-top: 1px solid #F0F0F0; }
QPushButton#PlayBtn { 
    background-color: #1ECD97; color: white; border-radius: 25px; 
    font-size: 20px; min-width: 50px; min-height: 50px;
}
QPushButton#PlayBtn:hover { background-color: #18c48f; }

QPushButton.CtrlBtn { background: transparent; border: none; font-size: 16px; color: #666; }
QPushButton.CtrlBtn:hover { color: #1ECD97; background-color: #F0F0F0; border-radius: 4px; }

/* 歌词微调按钮 */
QPushButton.OffsetBtn { background: #F5F5F5; border: 1px solid #DDD; border-radius: 4px; color: #666; font-size: 10px; padding: 2px 5px; }
QPushButton.OffsetBtn:hover { background: #E8F5E9; border-color: #1ECD97; color: #1ECD97; }

QSlider::groove:horizontal { border: 1px solid #EEE; height: 6px; background: #F0F0F0; margin: 2px 0; border-radius: 3px; }
QSlider::handle:horizontal { background: #1ECD97; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }
QSlider::sub-page:horizontal { background: #1ECD97; border-radius: 3px; }
"""

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

# --- 1. 增强版批量重命名弹窗 ---
class BatchRenameDialog(QDialog):
    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量重命名工具")
        self.resize(550, 650)
        self.playlist = playlist
        self.selected_indices = []
        
        layout = QVBoxLayout(self)
        
        # 模式选择标签页
        self.tabs = QTabWidget()
        
        # Tab 1: 替换模式
        tab_replace = QWidget()
        l1 = QVBoxLayout(tab_replace)
        h1 = QHBoxLayout()
        self.input_find = QLineEdit(); self.input_find.setPlaceholderText("查找内容 (如：【高清】)")
        self.input_replace = QLineEdit(); self.input_replace.setPlaceholderText("替换为 (留空删除)")
        h1.addWidget(QLabel("查找:")); h1.addWidget(self.input_find)
        h1.addWidget(QLabel("替换:")); h1.addWidget(self.input_replace)
        l1.addLayout(h1)
        l1.addStretch()
        self.tabs.addTab(tab_replace, "文本替换")
        
        # Tab 2: 裁剪模式 (解决前缀数字)
        tab_trim = QWidget()
        l2 = QVBoxLayout(tab_trim)
        h2 = QHBoxLayout()
        self.spin_head = QSpinBox(); self.spin_head.setRange(0, 50)
        self.spin_tail = QSpinBox(); self.spin_tail.setRange(0, 50)
        h2.addWidget(QLabel("删除前 N 个字符:")); h2.addWidget(self.spin_head)
        h2.addWidget(QLabel("删除后 N 个字符:")); h2.addWidget(self.spin_tail)
        l2.addLayout(h2)
        l2.addWidget(QLabel("提示：常用于去除 '01. ' 这种序号前缀", styleSheet="color:#888"))
        l2.addStretch()
        self.tabs.addTab(tab_trim, "字符裁剪")
        
        layout.addWidget(self.tabs)
        
        # 列表区
        layout.addWidget(QLabel("选择要处理的文件:"))
        self.list_view = QListWidget()
        self.populate_list()
        layout.addWidget(self.list_view)
        
        # 全选控制
        h_sel = QHBoxLayout()
        btn_all = QPushButton("全选"); btn_all.clicked.connect(self.select_all)
        btn_none = QPushButton("全不选"); btn_none.clicked.connect(self.select_none)
        h_sel.addWidget(btn_all); h_sel.addWidget(btn_none); h_sel.addStretch()
        layout.addLayout(h_sel)
        
        # 底部
        btn_ok = QPushButton("执行重命名")
        btn_ok.setFixedHeight(40)
        btn_ok.setStyleSheet("background-color: #1ECD97; color: white; font-weight: bold; border-radius: 5px;")
        btn_ok.clicked.connect(self.on_accept)
        layout.addWidget(btn_ok)

    def populate_list(self):
        for song in self.playlist:
            item = QListWidgetItem(song["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list_view.addItem(item)

    def select_all(self):
        for i in range(self.list_view.count()): self.list_view.item(i).setCheckState(Qt.Checked)
    def select_none(self):
        for i in range(self.list_view.count()): self.list_view.item(i).setCheckState(Qt.Unchecked)

    def on_accept(self):
        self.selected_indices = []
        for i in range(self.list_view.count()):
            if self.list_view.item(i).checkState() == Qt.Checked:
                self.selected_indices.append(i)
        self.accept()

    def get_data(self):
        idx = self.tabs.currentIndex()
        if idx == 0: # Replace
            return "replace", (self.input_find.text(), self.input_replace.text()), self.selected_indices
        else: # Trim
            return "trim", (self.spin_head.value(), self.spin_tail.value()), self.selected_indices

# --- 2. 手动歌词搜索弹窗 ---
class LyricSearchDialog(QDialog):
    def __init__(self, song_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("在线歌词搜索")
        self.resize(600, 400)
        self.result_id = None
        
        layout = QVBoxLayout(self)
        h = QHBoxLayout()
        self.input_key = QLineEdit(song_name)
        btn = QPushButton("搜索网易云")
        btn.clicked.connect(self.search)
        h.addWidget(self.input_key); h.addWidget(btn)
        layout.addLayout(h)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["歌名", "歌手", "ID"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemDoubleClicked.connect(self.on_select)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("双击选中以应用歌词"))

    def search(self):
        key = self.input_key.text()
        if not key: return
        self.table.setRowCount(0)
        # 简单同步请求避免复杂性，网易云API很快
        threading.Thread(target=self._do_search, args=(key,), daemon=True).start()

    def _do_search(self, key):
        try:
            url = "http://music.163.com/api/search/get/web?csrf_token="
            headers = {'User-Agent': 'Mozilla/5.0'}
            data = urllib.parse.urlencode({'s': key, 'type': 1, 'offset': 0, 'total': 'true', 'limit': 15}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req) as f:
                res = json.loads(f.read().decode('utf-8'))
            if res.get('result') and res['result'].get('songs'):
                QCoreApplication.postEvent(self, DataEvent(res['result']['songs']))
        except: pass

    def customEvent(self, e):
        # 线程回调更新UI
        for s in e.data:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(s['name']))
            artist = s['artists'][0]['name'] if s['artists'] else "未知"
            self.table.setItem(r, 1, QTableWidgetItem(artist))
            self.table.setItem(r, 2, QTableWidgetItem(str(s['id'])))

    def on_select(self, item):
        row = item.row()
        self.result_id = self.table.item(row, 2).text()
        self.accept()

class DataEvent(pyqtSignal): # 简单的事件封装
    def __init__(self, data):
        super().__init__()
        self.type = QCoreApplication.User
        self.data = data

# --- 3. 桌面歌词 (增强交互) ---
class DesktopLyricWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1200, 200)
        
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - 1200) // 2, screen.height() - 250)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)
        
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
        # 阴影
        shadow_color = QColor(0, 0, 0, 180) # 黑色阴影更通用
        for i, lbl in enumerate(self.labels):
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(10); effect.setColor(shadow_color); effect.setOffset(1, 1)
            lbl.setGraphicsEffect(effect)
            
            f = QFont(self.current_font)
            color_css = self.font_color.name()
            
            if i == 1: # 当前句
                f.setPointSize(base_size)
                lbl.setStyleSheet(f"color: {color_css};")
            else: # 上下句
                f.setPointSize(int(base_size * 0.6))
                # 半透明
                r,g,b = self.font_color.red(), self.font_color.green(), self.font_color.blue()
                lbl.setStyleSheet(f"color: rgba({r}, {g}, {b}, 150);")
            lbl.setFont(f)

    def set_lyrics(self, p, c, n):
        self.labels[0].setText(p); self.labels[1].setText(c); self.labels[2].setText(n)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.locked:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self.show_menu(event.globalPos())

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
        
        act_close = menu.addAction("❌ 关闭歌词")
        
        action = menu.exec_(pos)
        if action == act_color:
            c = QColorDialog.getColor(self.font_color, self, "选择歌词颜色")
            if c.isValid(): self.font_color = c; self.update_styles()
        elif action == act_font:
            f, ok = QFontDialog.getFont(self.current_font, self)
            if ok: self.current_font = f; self.update_styles()
        elif action == act_lock:
            self.locked = not self.locked
        elif action == act_close:
            self.hide()

# --- B站下载线程 (保持之前修复的) ---
class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
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
            self.finished_signal.emit()
        except Exception as e: self.error_signal.emit(f"❌: {str(e)}")

# --- 主程序 ---
class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 (终极进化版)")
        self.resize(1100, 750)
        self.setStyleSheet(STYLESHEET)

        self.music_folder = ""
        self.current_collection = "" 
        self.collections = [] 
        self.playlist = []
        self.lyrics = []
        self.current_index = -1
        self.offset = 0.0
        self.saved_offsets = {}
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
        sidebar.setFixedWidth(250)
        self.side_layout = QVBoxLayout(sidebar)
        self.side_layout.addWidget(QLabel("🧼 SODA MUSIC", objectName="Logo"))

        self.btn_bili = QPushButton("📺  B站下载")
        self.btn_bili.setObjectName("DownloadBtn"); self.btn_bili.setProperty("NavBtn", True)
        self.btn_bili.clicked.connect(self.download_from_bilibili)
        self.side_layout.addWidget(self.btn_bili)

        btn_new_coll = QPushButton("➕  新建合集")
        btn_new_coll.setProperty("NavBtn", True)
        btn_new_coll.clicked.connect(self.create_collection)
        self.side_layout.addWidget(btn_new_coll)

        btn_refresh = QPushButton("🔄  刷新数据")
        btn_refresh.setProperty("NavBtn", True)
        btn_refresh.clicked.connect(self.full_scan)
        self.side_layout.addWidget(btn_refresh)

        self.side_layout.addWidget(QLabel("合集列表", objectName="SectionTitle"))
        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet("background:transparent; border:none;")
        self.nav_list.itemClicked.connect(self.switch_collection)
        self.side_layout.addWidget(self.nav_list)

        self.side_layout.addStretch()
        
        btn_folder = QPushButton("📁  根目录")
        btn_folder.setProperty("NavBtn", True)
        btn_folder.clicked.connect(self.select_folder)
        self.side_layout.addWidget(btn_folder)
        
        btn_lyric = QPushButton("💬  桌面歌词")
        btn_lyric.setProperty("NavBtn", True)
        btn_lyric.clicked.connect(self.toggle_lyric)
        self.side_layout.addWidget(btn_lyric)
        layout.addWidget(sidebar)

        right_panel = QWidget()
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_collection_title = QLabel("全部音乐")
        self.lbl_collection_title.setStyleSheet("font-size:18px; font-weight:bold; padding:15px; color:#444;")
        r_layout.addWidget(self.lbl_collection_title)

        content = QWidget()
        c_layout = QHBoxLayout(content)
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        c_layout.addWidget(self.list_widget, stretch=6)
        
        self.panel_lyric = QListWidget()
        self.panel_lyric.setFocusPolicy(Qt.NoFocus)
        self.panel_lyric.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.panel_lyric.setStyleSheet("color:#999; border:none;")
        c_layout.addWidget(self.panel_lyric, stretch=4)
        r_layout.addWidget(content)

        bar = QFrame()
        bar.setObjectName("PlayerBar"); bar.setFixedHeight(120)
        bar_v = QVBoxLayout(bar)

        progress = QHBoxLayout()
        self.lbl_curr_time = QLabel("00:00"); self.lbl_total_time = QLabel("00:00")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderPressed.connect(self.slider_pressed)
        self.slider.sliderReleased.connect(self.slider_released)
        self.slider.valueChanged.connect(self.slider_moved)
        progress.addWidget(self.lbl_curr_time); progress.addWidget(self.slider); progress.addWidget(self.lbl_total_time)
        bar_v.addLayout(progress)

        ctrl = QHBoxLayout()
        self.btn_mode = QPushButton("🔁"); self.btn_mode.setProperty("CtrlBtn", True)
        self.btn_mode.clicked.connect(self.toggle_mode)
        btn_prev = QPushButton("⏮"); btn_prev.setProperty("CtrlBtn", True)
        btn_prev.clicked.connect(self.play_prev)
        self.btn_play = QPushButton("▶"); self.btn_play.setObjectName("PlayBtn")
        self.btn_play.clicked.connect(self.toggle_play)
        btn_next = QPushButton("⏭"); btn_next.setProperty("CtrlBtn", True)
        btn_next.clicked.connect(self.play_next)
        self.btn_rate = QPushButton("1.0x"); self.btn_rate.setProperty("CtrlBtn", True)
        self.btn_rate.clicked.connect(self.toggle_rate)
        ctrl.addStretch()
        ctrl.addWidget(self.btn_mode); ctrl.addSpacing(15)
        ctrl.addWidget(btn_prev); ctrl.addWidget(self.btn_play); ctrl.addWidget(btn_next); ctrl.addSpacing(15)
        ctrl.addWidget(self.btn_rate); ctrl.addStretch()
        
        # 歌词微调
        offset_layout = QHBoxLayout()
        btn_slow = QPushButton("⏪ 慢0.5s"); btn_slow.setProperty("OffsetBtn", True)
        btn_slow.clicked.connect(lambda: self.adjust_offset(-0.5))
        self.lbl_offset = QLabel("偏移: 0.0s")
        self.lbl_offset.setStyleSheet("color:#999; font-size:10px;")
        btn_fast = QPushButton("⏩ 快0.5s"); btn_fast.setProperty("OffsetBtn", True)
        btn_fast.clicked.connect(lambda: self.adjust_offset(0.5))
        offset_layout.addStretch()
        offset_layout.addWidget(btn_slow); offset_layout.addWidget(self.lbl_offset); offset_layout.addWidget(btn_fast)
        
        bar_v.addLayout(ctrl); bar_v.addLayout(offset_layout)
        r_layout.addWidget(bar); layout.addWidget(right_panel)

    # --- 4. 修复的合集扫描逻辑 ---
    def full_scan(self):
        if not self.music_folder or not os.path.exists(self.music_folder): return
        self.collections = []
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4')
        
        for item in os.listdir(self.music_folder):
            full_path = os.path.join(self.music_folder, item)
            if os.path.isdir(full_path):
                # 关键修改：检测里面有多少首歌
                files = [x for x in os.listdir(full_path) if x.lower().endswith(exts)]
                # 如果只有 <= 1 首歌，且文件夹名包含歌名，认为是绑定文件夹，不显示
                if len(files) <= 1:
                    if len(files) == 1:
                        song_base = os.path.splitext(files[0])[0]
                        # 模糊匹配：如果文件夹名包含歌名，或反之，则跳过
                        if item in song_base or song_base in item:
                            continue
                # 否则认为是合集
                self.collections.append(item)
        
        self.nav_list.clear()
        self.nav_list.addItem("💿  所有歌曲") 
        for c in self.collections:
            self.nav_list.addItem(f"📁  {c}")
        
        if not self.current_collection or self.current_collection not in self.collections:
            self.load_songs_for_collection() # 回到根
        else:
            self.load_songs_for_collection()

    def create_collection(self):
        if not self.music_folder: return
        name, ok = QInputDialog.getText(self, "新建合集", "请输入名称:")
        if ok and name:
            name = sanitize_filename(name)
            path = os.path.join(self.music_folder, name)
            if not os.path.exists(path):
                os.makedirs(path)
                self.full_scan()
                QMessageBox.information(self, "成功", "合集已创建")

    def switch_collection(self, item):
        text = item.text()
        if "所有歌曲" in text:
            self.current_collection = ""
            self.lbl_collection_title.setText("全部音乐")
        else:
            self.current_collection = text.replace("📁  ", "")
            self.lbl_collection_title.setText(f"合集：{self.current_collection}")
        self.load_songs_for_collection()

    def load_songs_for_collection(self):
        self.playlist = []
        self.list_widget.clear()
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4')
        
        target_dirs = []
        if self.current_collection:
            target_dirs = [os.path.join(self.music_folder, self.current_collection)]
        else:
            target_dirs = [self.music_folder]
            for item in os.listdir(self.music_folder):
                p = os.path.join(self.music_folder, item)
                if os.path.isdir(p): target_dirs.append(p)

        for d in target_dirs:
            if not os.path.exists(d): continue
            for f in os.listdir(d):
                if f.lower().endswith(exts):
                    full = os.path.abspath(os.path.join(d, f))
                    self.playlist.append({"path": full, "name": f})
                    self.list_widget.addItem(os.path.splitext(f)[0])

    def show_context_menu(self, pos):
        items = self.list_widget.selectedItems()
        menu = QMenu()
        
        # 1. 批量移动
        act_move = QMenu("📂 批量移动到...", self)
        act_root = QAction("💿 根目录", self)
        act_root.triggered.connect(lambda: self.batch_move(items, ""))
        act_move.addAction(act_root)
        act_move.addSeparator()
        for c in self.collections:
            if c != self.current_collection:
                a = QAction(f"📁 {c}", self)
                a.triggered.connect(lambda ch, t=c: self.batch_move(items, t))
                act_move.addAction(a)
        menu.addMenu(act_move)

        act_ren = QAction("🔠 批量重命名", self)
        act_ren.triggered.connect(self.open_batch_rename)
        menu.addAction(act_ren)
        menu.addSeparator()

        if items and len(items) == 1:
            idx = self.list_widget.row(items[0])
            menu.addAction("✏️ 重命名单曲", lambda: self.rename_song(idx))
            menu.addAction("🔐 绑定歌词 (整理)", lambda: self.bind_lyrics(idx))
            menu.addAction("🔍 手动搜索歌词", lambda: self.open_manual_search(idx))
            menu.addAction("❌ 删除/解绑歌词", lambda: self.remove_lyric(idx))
        
        if items:
            menu.addAction(f"🗑️ 删除 ({len(items)}首)", lambda: self.delete_songs(items))
        
        menu.exec_(self.list_widget.mapToGlobal(pos))

    # --- 修复：批量移动 ---
    def batch_move(self, items, target_name):
        self.player.setMedia(QMediaContent()) # 释放锁
        
        target_path = self.music_folder
        if target_name: target_path = os.path.join(self.music_folder, target_name)
        if not os.path.exists(target_path): os.makedirs(target_path)
        
        # 收集源数据，防止循环时索引变化
        files_to_move = []
        for item in items:
            idx = self.list_widget.row(item)
            if idx < len(self.playlist):
                files_to_move.append(self.playlist[idx])
        
        count = 0
        for song in files_to_move:
            try:
                src = song["path"]
                dst = os.path.join(target_path, song["name"])
                # 如果目标已存在，跳过
                if src == dst: continue
                shutil.move(src, dst)
                
                lrc_src = os.path.splitext(src)[0] + ".lrc"
                if os.path.exists(lrc_src):
                    lrc_dst = os.path.join(target_path, os.path.basename(lrc_src))
                    shutil.move(lrc_src, lrc_dst)
                count += 1
            except Exception as e: print(e)
        
        self.full_scan()
        QMessageBox.information(self, "成功", f"已移动 {count} 首歌曲")

    # --- 修复：批量重命名 ---
    def open_batch_rename(self):
        if not self.playlist: return
        self.player.setMedia(QMediaContent()) # 释放锁
        
        dialog = BatchRenameDialog(self.playlist, self)
        if dialog.exec_() == QDialog.Accepted:
            mode, params, indices = dialog.get_data()
            count = 0
            
            # 收集要修改的文件，避免索引动态变化
            targets = []
            for i in indices:
                if i < len(self.playlist): targets.append(self.playlist[i])
            
            for song in targets:
                old_path = song["path"]
                old_name = song["name"]
                name_no_ext, ext = os.path.splitext(old_name)
                
                new_name_base = name_no_ext
                
                if mode == "replace":
                    find_str, repl_str = params
                    if find_str in new_name_base:
                        new_name_base = new_name_base.replace(find_str, repl_str)
                elif mode == "trim":
                    head, tail = params
                    if head > 0: new_name_base = new_name_base[head:]
                    if tail > 0: new_name_base = new_name_base[:-tail]
                
                new_filename = new_name_base.strip() + ext
                new_path = os.path.join(os.path.dirname(old_path), new_filename)
                
                if new_path != old_path:
                    try:
                        os.rename(old_path, new_path)
                        # 改LRC
                        old_lrc = os.path.splitext(old_path)[0] + ".lrc"
                        if os.path.exists(old_lrc):
                            new_lrc = os.path.splitext(new_path)[0] + ".lrc"
                            os.rename(old_lrc, new_lrc)
                        count += 1
                    except: pass
            
            self.load_songs_for_collection()
            QMessageBox.information(self, "完成", f"已重命名 {count} 个文件")

    def open_manual_search(self, idx):
        song = self.playlist[idx]
        name = os.path.splitext(song["name"])[0]
        d = LyricSearchDialog(name, self)
        if d.exec_() == QDialog.Accepted and d.result_id:
            lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
            # 启动下载线程
            self.lrc_dl = LyricDownloader(d.result_id, lrc_path)
            self.lrc_dl.finished_signal.connect(lambda c: self.on_lrc_downloaded(c, idx))
            self.lrc_dl.start()

    def on_lrc_downloaded(self, content, idx):
        # 如果当前正好在播放这首，立即刷新
        if self.current_index == idx:
            self.parse_lrc_content(content)
        QMessageBox.information(self, "成功", "歌词已下载并应用")

    def remove_lyric(self, idx):
        song = self.playlist[idx]
        lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
        if os.path.exists(lrc_path):
            try:
                os.remove(lrc_path)
                if self.current_index == idx:
                    self.lyrics = []
                    self.panel_lyric.clear()
                    self.desktop_lyric.set_lyrics("", "无歌词", "")
                QMessageBox.information(self, "成功", "歌词已解绑/删除")
            except: pass
        else:
            QMessageBox.information(self, "提示", "当前没有绑定本地歌词")

    # ... (其余函数 rename_song, bind_lyrics, delete_songs, download..., select_folder, play_index 等保持不变) ...
    # 为了篇幅，这里只列出关键修改点。请确保下面的核心播放逻辑完整。

    def download_from_bilibili(self):
        if not self.music_folder: return QMessageBox.warning(self, "提示", "请先设置文件夹")
        u, ok = QInputDialog.getText(self, "B站下载", "粘贴链接:")
        if ok and u:
            p=1
            m=re.search(r'[?&]p=(\d+)', u)
            if m: p=int(m.group(1))
            dialog = DownloadDialog(self, p, self.collections)
            if dialog.exec_() == QDialog.Accepted:
                mode, folder = dialog.get_data()
                path = self.music_folder
                if folder: path = os.path.join(path, folder)
                self.lbl_collection_title.setText("⏳ 下载中...")
                self.dl = BilibiliDownloader(u, path, mode, p)
                self.dl.progress_signal.connect(lambda s: self.lbl_collection_title.setText(s))
                self.dl.finished_signal.connect(self.on_dl_finish)
                self.dl.error_signal.connect(self.on_dl_error)
                self.dl.start()
    def on_dl_finish(self): self.full_scan(); self.lbl_collection_title.setText("下载完成")
    def on_dl_error(self, m): QMessageBox.warning(self, "错", m)
    def rename_song(self, idx):
        self.player.setMedia(QMediaContent())
        s = self.playlist[idx]; old=s["path"]
        n, ok = QInputDialog.getText(self, "重命名", "新名:", text=os.path.splitext(s["name"])[0])
        if ok and n:
            nn = sanitize_filename(n) + os.path.splitext(s["name"])[1]
            np = os.path.join(os.path.dirname(old), nn)
            try:
                os.rename(old, np)
                ol = os.path.splitext(old)[0]+".lrc"
                if os.path.exists(ol): os.rename(ol, os.path.join(os.path.dirname(old), sanitize_filename(n)+".lrc"))
                self.load_songs_for_collection()
            except Exception as e: print(e)
    def delete_songs(self, items):
        if QMessageBox.Yes == QMessageBox.question(self, "删?", f"删 {len(items)} 首?"):
            self.player.setMedia(QMediaContent())
            for i in items:
                idx=self.list_widget.row(i)
                if idx<len(self.playlist):
                    try:
                        p=self.playlist[idx]["path"]
                        os.remove(p)
                        l=os.path.splitext(p)[0]+".lrc"
                        if os.path.exists(l): os.remove(l)
                    except:pass
            self.load_songs_for_collection()
    def bind_lyrics(self, idx):
        self.player.setMedia(QMediaContent())
        s = self.playlist[idx]; p=s["path"]; n=os.path.splitext(s["name"])[0]
        f, _ = QFileDialog.getOpenFileName(self, "选词", "", "LRC (*.lrc)")
        if f:
            d = os.path.join(os.path.dirname(p), n)
            try:
                if not os.path.exists(d): os.makedirs(d)
                np = os.path.join(d, s["name"])
                shutil.move(p, np)
                shutil.copy(f, os.path.join(d, n+".lrc"))
                self.full_scan(); QMessageBox.information(self,"ok","ok")
            except:pass
    def select_folder(self):
        f=QFileDialog.getExistingDirectory(self,"选目录")
        if f: self.music_folder=f; self.full_scan(); self.save_config()
    def play_selected(self, item): self.play_index(self.list_widget.row(item))
    def play_index(self, idx):
        if not self.playlist or idx >= len(self.playlist): return
        self.current_index = idx
        song = self.playlist[idx]
        try:
            url = QUrl.fromLocalFile(song["path"])
            self.player.setMedia(QMediaContent(url))
            self.player.setPlaybackRate(self.rate)
            self.player.play()
            self.btn_play.setText("⏸")
            
            self.offset = self.saved_offsets.get(song["name"], 0.0)
            self.update_offset_lbl()
            
            lrc = os.path.splitext(song["path"])[0]+".lrc"
            if os.path.exists(lrc): self.parse_lrc_file(lrc)
            else:
                self.panel_lyric.clear(); self.panel_lyric.addItem("搜索歌词...")
                self.searcher = OnlineLyricSearcher(song["name"], lrc)
                self.searcher.finished_signal.connect(self.on_auto_lrc)
                self.searcher.start()
        except: pass
    def on_auto_lrc(self, content, path): self.parse_lrc_content(content)
    def parse_lrc_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f: c = f.read()
            self.parse_lrc_content(c)
        except:
            try:
                with open(path, 'r', encoding='gbk') as f: c = f.read()
                self.parse_lrc_content(c)
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
        elif self.playlist: self.player.play()
    def toggle_mode(self):
        self.mode = (self.mode + 1) % 3; modes = ["🔁", "🔂", "🔀"]; self.btn_mode.setText(modes[self.mode])
    def toggle_rate(self):
        rs=[1.0,1.25,1.5,2.0,0.5]; 
        try: i=rs.index(self.rate)
        except: i=0
        self.rate=rs[(i+1)%5]; self.player.setPlaybackRate(self.rate); self.btn_rate.setText(f"{self.rate}x")
    def play_next(self):
        if not self.playlist: return
        if self.mode==2: n=random.randint(0, len(self.playlist)-1)
        else: n=(self.current_index+1)%len(self.playlist)
        self.play_index(n)
    def play_prev(self):
        if not self.playlist: return
        if self.mode==2: p=random.randint(0, len(self.playlist)-1)
        else: p=(self.current_index-1)%len(self.playlist)
        self.play_index(p)
    def on_state_changed(self, s): self.btn_play.setText("⏸" if s==QMediaPlayer.PlayingState else "▶")
    def on_media_status_changed(self, s): 
        if s==QMediaPlayer.EndOfMedia: 
            if self.mode==1: self.player.play() 
            else: self.play_next()
    def on_position_changed(self, pos):
        if not self.is_slider_pressed: self.slider.setValue(pos)
        self.lbl_curr_time.setText(self.fmt_time(pos))
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
        if self.is_slider_pressed: self.lbl_curr_time.setText(self.fmt_time(v))
    def on_duration_changed(self, d): self.slider.setRange(0, d); self.lbl_total_time.setText(self.fmt_time(d))
    def fmt_time(self, ms): s=ms//1000; return f"{s//60:02}:{s%60:02}"
    def toggle_lyric(self): 
        if self.desktop_lyric.isVisible(): self.desktop_lyric.hide()
        else: self.desktop_lyric.show()
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try: 
                with open(CONFIG_FILE,'r') as f: self.music_folder=json.load(f).get("folder",""); 
                if self.music_folder: self.full_scan()
            except:pass
        if os.path.exists(OFFSET_FILE):
            try: 
                with open(OFFSET_FILE,'r') as f: self.saved_offsets=json.load(f)
            except:pass
    def save_config(self): 
        with open(CONFIG_FILE,'w') as f: json.dump({"folder":self.music_folder},f)
    def save_offsets(self):
        with open(OFFSET_FILE,'w') as f: json.dump(self.saved_offsets,f)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(app_path, 'PyQt5', 'Qt', 'plugins')
        QCoreApplication.addLibraryPath(os.path.join(app_path, 'PyQt5', 'Qt', 'plugins'))
    app = QApplication(sys.argv)
    f = QFont("SimSun"); f.setPixelSize(14); app.setFont(f)
    w = SodaPlayer(); w.show(); sys.exit(app.exec_())

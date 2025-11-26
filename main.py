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
                             QFontDialog, QMenu, QAction, QSlider, QDialog, QRadioButton, QComboBox, QLineEdit)
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

# --- 样式表 ---
STYLESHEET = """
QMainWindow { background-color: #FFFFFF; }
QWidget { font-family: "SimSun", "宋体", serif; color: #333333; }

/* 侧边栏 */
QFrame#Sidebar { background-color: #F7F9FC; border-right: 1px solid #EEEEEE; }
QLabel#Logo { font-size: 22px; font-weight: bold; color: #1ECD97; padding: 20px; }
QLabel#SectionTitle { font-size: 12px; color: #999; padding: 10px 20px; font-weight: bold; }

/* 导航按钮 */
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
QListWidget::item { padding: 10px; margin: 2px 10px; border-radius: 6px; border-bottom: 1px solid #F9F9F9; }
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

QSlider::groove:horizontal { border: 1px solid #EEE; height: 6px; background: #F0F0F0; margin: 2px 0; border-radius: 3px; }
QSlider::handle:horizontal { background: #1ECD97; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }
QSlider::sub-page:horizontal { background: #1ECD97; border-radius: 3px; }
"""

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

# --- 下载选项弹窗 (增加合集选择) ---
class DownloadDialog(QDialog):
    def __init__(self, parent=None, current_p=1, collections=[]):
        super().__init__(parent)
        self.setWindowTitle("下载与归档")
        self.resize(400, 250)
        layout = QVBoxLayout(self)
        
        # 1. 模式选择
        layout.addWidget(QLabel(f"链接包含分P信息 (第 {current_p} 集)，请选择模式："))
        self.rb_single = QRadioButton(f"仅下载当前单曲 (P{current_p})")
        self.rb_list = QRadioButton(f"下载合集 (P{current_p} - 结尾)")
        self.rb_single.setChecked(True)
        layout.addWidget(self.rb_single)
        layout.addWidget(self.rb_list)
        
        layout.addSpacing(10)
        
        # 2. 合集/文件夹选择
        layout.addWidget(QLabel("存入合集 (文件夹)："))
        self.combo_coll = QComboBox()
        self.combo_coll.addItem("根目录 (不分类)", "")
        for c in collections:
            self.combo_coll.addItem(f"📁 {c}", c)
        self.combo_coll.addItem("➕ 新建合集...", "NEW")
        layout.addWidget(self.combo_coll)
        
        self.input_new = QLineEdit()
        self.input_new.setPlaceholderText("输入新合集名称 (例如: 周杰伦)")
        self.input_new.hide()
        layout.addWidget(self.input_new)
        
        self.combo_coll.currentIndexChanged.connect(self.on_combo_change)
        
        # 按钮
        btn_box = QHBoxLayout()
        btn_ok = QPushButton("开始下载")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def on_combo_change(self):
        if self.combo_coll.currentData() == "NEW":
            self.input_new.show()
            self.input_new.setFocus()
        else:
            self.input_new.hide()

    def get_data(self):
        mode = "playlist" if self.rb_list.isChecked() else "single"
        folder_name = self.combo_coll.currentData()
        if folder_name == "NEW":
            folder_name = self.input_new.text().strip()
        return mode, folder_name

# --- B站下载线程 ---
class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, url, save_path, mode="single", start_p=1):
        super().__init__()
        self.url = url
        self.save_path = save_path # 具体的合集文件夹路径
        self.mode = mode
        self.start_p = start_p

    def run(self):
        if not yt_dlp:
            self.error_signal.emit("错误：缺少 yt-dlp")
            return

        if not os.path.exists(self.save_path):
            try:
                os.makedirs(self.save_path)
            except Exception as e:
                self.error_signal.emit(f"无法创建文件夹: {e}")
                return

        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%')
                filename = os.path.basename(d.get('filename', '未知'))
                if len(filename) > 20: filename = filename[:20] + "..."
                self.progress_signal.emit(f"⬇️ {p} : {filename}")
            elif d['status'] == 'finished':
                self.progress_signal.emit("✅ 下载完成，处理中...")

        items_range = str(self.start_p) if self.mode == 'single' else f"{self.start_p}-"

        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/best[ext=mp4]/best', 
            'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
            'overwrites': True,
            'noplaylist': False, 
            'playlist_items': items_range,
            'ignoreerrors': True,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'nocheckcertificate': True,
            'restrictfilenames': False,
        }

        try:
            self.progress_signal.emit(f"🔍 开始解析...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.progress_signal.emit("🎉 任务完成")
            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(f"❌: {str(e)}")

# --- 桌面歌词 (保持不变) ---
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
        self.setWindowTitle("汽水音乐 (合集管理旗舰版)")
        self.resize(1100, 750)
        self.setStyleSheet(STYLESHEET)

        self.music_folder = ""
        self.current_collection = "" # 当前选中的合集文件夹名，空代表根目录
        self.collections = [] # 文件夹列表
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
        
        # 1. 侧边栏
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)
        self.side_layout = QVBoxLayout(sidebar)
        
        logo = QLabel("🧼 SODA MUSIC")
        logo.setObjectName("Logo")
        self.side_layout.addWidget(logo)

        # 固定功能区
        self.btn_bili = QPushButton("📺  B站下载")
        self.btn_bili.setObjectName("DownloadBtn")
        self.btn_bili.setProperty("NavBtn", True)
        self.btn_bili.clicked.connect(self.download_from_bilibili)
        self.side_layout.addWidget(self.btn_bili)

        btn_refresh = QPushButton("🔄  刷新数据")
        btn_refresh.setProperty("NavBtn", True)
        btn_refresh.clicked.connect(self.full_scan)
        self.side_layout.addWidget(btn_refresh)

        # 合集列表区
        self.side_layout.addWidget(QLabel("我的合集", objectName="SectionTitle"))
        
        # 使用 ListWidget 作为合集导航，方便管理
        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet("background:transparent; border:none;")
        self.nav_list.itemClicked.connect(self.switch_collection)
        self.side_layout.addWidget(self.nav_list)

        # 底部设置
        self.side_layout.addStretch()
        btn_folder = QPushButton("📁  根目录设置")
        btn_folder.setProperty("NavBtn", True)
        btn_folder.clicked.connect(self.select_folder)
        self.side_layout.addWidget(btn_folder)
        
        btn_lyric = QPushButton("💬  桌面歌词")
        btn_lyric.setProperty("NavBtn", True)
        btn_lyric.clicked.connect(self.toggle_lyric)
        self.side_layout.addWidget(btn_lyric)
        
        layout.addWidget(sidebar)

        # 2. 右侧内容
        right_panel = QWidget()
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0, 0, 0, 0)
        
        # 顶部当前合集标题
        self.lbl_collection_title = QLabel("全部音乐")
        self.lbl_collection_title.setStyleSheet("font-size:18px; font-weight:bold; padding:15px; color:#444;")
        r_layout.addWidget(self.lbl_collection_title)

        content = QWidget()
        c_layout = QHBoxLayout(content)
        
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection) # 支持多选
        c_layout.addWidget(self.list_widget, stretch=6)
        
        self.panel_lyric = QListWidget()
        self.panel_lyric.setFocusPolicy(Qt.NoFocus)
        self.panel_lyric.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.panel_lyric.setStyleSheet("color:#999; border:none;")
        c_layout.addWidget(self.panel_lyric, stretch=4)
        
        r_layout.addWidget(content)

        # 播放条 (保持不变)
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
        ctrl_layout.addWidget(self.btn_play)
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

    # --- 核心：扫描与合集管理 ---
    def full_scan(self):
        """扫描根目录和一级子文件夹"""
        if not self.music_folder or not os.path.exists(self.music_folder): return
        
        self.collections = []
        # 扫描一级子文件夹作为合集
        for item in os.listdir(self.music_folder):
            full_path = os.path.join(self.music_folder, item)
            if os.path.isdir(full_path):
                self.collections.append(item)
        
        # 刷新侧边栏
        self.nav_list.clear()
        self.nav_list.addItem("💿  所有歌曲") # 默认项
        for c in self.collections:
            self.nav_list.addItem(f"📁  {c}")
            
        # 刷新当前视图
        self.load_songs_for_collection()

    def switch_collection(self, item):
        text = item.text()
        if "所有歌曲" in text:
            self.current_collection = ""
            self.lbl_collection_title.setText("全部音乐")
        else:
            # 提取文件夹名
            self.current_collection = text.replace("📁  ", "")
            self.lbl_collection_title.setText(f"合集：{self.current_collection}")
        
        self.load_songs_for_collection()

    def load_songs_for_collection(self):
        self.playlist = []
        self.list_widget.clear()
        
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4')
        
        # 确定扫描路径
        if self.current_collection:
            target_dir = os.path.join(self.music_folder, self.current_collection)
            scan_dirs = [target_dir]
        else:
            # 扫描根目录 + 所有子目录
            scan_dirs = [self.music_folder] + [os.path.join(self.music_folder, c) for c in self.collections]

        for d in scan_dirs:
            if not os.path.exists(d): continue
            for f in os.listdir(d):
                if f.lower().endswith(exts):
                    full_path = os.path.abspath(os.path.join(d, f))
                    self.playlist.append({"path": full_path, "name": f})
                    self.list_widget.addItem(os.path.splitext(f)[0])

    # --- 右键菜单 (支持批量移动) ---
    def show_context_menu(self, pos):
        items = self.list_widget.selectedItems()
        if not items: return
        
        menu = QMenu()
        
        # 批量操作
        act_move = QMenu("🚚 移动到合集...", self)
        # 添加根目录选项
        act_root = QAction("💿 根目录", self)
        act_root.triggered.connect(lambda: self.batch_move(items, ""))
        act_move.addAction(act_root)
        act_move.addSeparator()
        
        # 添加现有合集
        for c in self.collections:
            # 排除当前所在的合集
            if c != self.current_collection:
                act_sub = QAction(f"📁 {c}", self)
                # 使用闭包捕获变量
                act_sub.triggered.connect(lambda checked, target=c: self.batch_move(items, target))
                act_move.addAction(act_sub)
        
        # 新建合集并移动
        act_new = QAction("➕ 新建合集并移动...", self)
        act_new.triggered.connect(lambda: self.batch_move_new(items))
        act_move.addAction(act_new)
        
        menu.addMenu(act_move)
        menu.addSeparator()
        
        # 单项操作
        if len(items) == 1:
            idx = self.list_widget.row(items[0])
            act_rename = QAction("✏️ 重命名", self)
            act_bind = QAction("🔐 绑定歌词 (整理)", self)
            act_rename.triggered.connect(lambda: self.rename_song(idx))
            act_bind.triggered.connect(lambda: self.bind_lyrics(idx))
            menu.addAction(act_rename)
            menu.addAction(act_bind)
        
        act_del = QAction(f"🗑️ 删除 ({len(items)}首)", self)
        act_del.triggered.connect(lambda: self.delete_songs(items))
        menu.addAction(act_del)
        
        menu.exec_(self.list_widget.mapToGlobal(pos))

    # --- 移动逻辑 ---
    def batch_move(self, items, target_folder_name):
        target_path = self.music_folder if not target_folder_name else os.path.join(self.music_folder, target_folder_name)
        if not os.path.exists(target_path): os.makedirs(target_path)
        
        count = 0
        for item in items:
            idx = self.list_widget.row(item)
            if idx >= len(self.playlist): continue
            song = self.playlist[idx]
            
            # 如果正在播放，停止
            if self.current_index == idx: self.player.stop()
            
            try:
                src = song["path"]
                dst = os.path.join(target_path, song["name"])
                shutil.move(src, dst)
                
                # 尝试移动同名歌词
                lrc_src = os.path.splitext(src)[0] + ".lrc"
                if os.path.exists(lrc_src):
                    lrc_dst = os.path.join(target_path, os.path.splitext(song["name"])[0] + ".lrc")
                    shutil.move(lrc_src, lrc_dst)
                
                count += 1
            except Exception as e:
                print(f"Move error: {e}")
        
        self.full_scan() # 刷新全部
        QMessageBox.information(self, "成功", f"已移动 {count} 首歌曲")

    def batch_move_new(self, items):
        name, ok = QInputDialog.getText(self, "新建合集", "请输入新合集名称:")
        if ok and name:
            name = sanitize_filename(name)
            self.batch_move(items, name)

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
                self.load_songs_for_collection()
            except Exception as e: QMessageBox.warning(self, "错误", str(e))

    def bind_lyrics(self, idx):
        song = self.playlist[idx]
        song_path = song["path"]
        song_name = os.path.splitext(song["name"])[0]
        lrc_file, _ = QFileDialog.getOpenFileName(self, "选择歌词文件", "", "LRC/TXT (*.lrc *.txt)")
        if not lrc_file: return
        
        # 在当前目录下建立文件夹
        parent_dir = os.path.dirname(song_path)
        new_folder_path = os.path.join(parent_dir, song_name)
        
        try:
            if not os.path.exists(new_folder_path): os.makedirs(new_folder_path)
            new_song_path = os.path.join(new_folder_path, song["name"])
            if self.current_index == idx: self.player.stop()
            shutil.move(song_path, new_song_path)
            new_lrc_path = os.path.join(new_folder_path, song_name + ".lrc")
            shutil.copy(lrc_file, new_lrc_path)
            QMessageBox.information(self, "成功", "整理完成")
            self.full_scan()
        except Exception as e: QMessageBox.warning(self, "错误", str(e))

    def delete_songs(self, items):
        if QMessageBox.Yes == QMessageBox.question(self, "确认", f"删除选中的 {len(items)} 首歌？"):
            for item in items:
                idx = self.list_widget.row(item)
                if idx < len(self.playlist):
                    song = self.playlist[idx]
                    try:
                        if self.current_index == idx: self.player.stop()
                        os.remove(song["path"])
                        lrc = os.path.splitext(song["path"])[0] + ".lrc"
                        if os.path.exists(lrc): os.remove(lrc)
                    except: pass
            self.load_songs_for_collection()

    # --- B站下载 ---
    def download_from_bilibili(self):
        if not self.music_folder: return QMessageBox.warning(self, "提示", "请先设置根文件夹")
        u, ok = QInputDialog.getText(self, "B站下载", "粘贴链接:")
        if ok and u:
            current_p = 1
            match = re.search(r'[?&]p=(\d+)', u)
            if match: current_p = int(match.group(1))
            
            # 传入当前合集列表给弹窗
            dialog = DownloadDialog(self, current_p, self.collections)
            if dialog.exec_() == QDialog.Accepted:
                mode, folder_name = dialog.get_data()
                
                # 确定保存路径
                save_path = self.music_folder
                if folder_name:
                    save_path = os.path.join(self.music_folder, folder_name)
                
                self.lbl_curr_time.setText("启动下载...")
                self.dl = BilibiliDownloader(u, save_path, mode, current_p)
                self.dl.progress_signal.connect(lambda m: self.lbl_curr_time.setText(m))
                self.dl.finished_signal.connect(self.on_dl_finish)
                self.dl.error_signal.connect(self.on_dl_error)
                self.dl.start()
    
    def on_dl_finish(self):
        self.full_scan()
        QMessageBox.information(self, "完成", "下载结束")
    def on_dl_error(self, msg): QMessageBox.warning(self, "错误", msg)

    # --- 基础功能 ---
    def select_folder(self):
        f = QFileDialog.getExistingDirectory(self, "选择根目录")
        if f: 
            self.music_folder = f
            self.full_scan()
            self.save_config()

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
            self.parse_lrc(os.path.splitext(song["path"])[0] + ".lrc")
        except Exception as e: print(f"Error: {e}")

    def parse_lrc(self, path):
        self.lyrics = []
        self.panel_lyric.clear()
        self.desktop_lyric.set_lyrics("", "等待歌词...", "")
        self.offset = 0
        if not os.path.exists(path): 
            self.panel_lyric.addItem("纯音乐")
            return
        
        lines = []
        # --- 严格的语法 ---
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            try:
                with open(path, 'r', encoding='gbk') as f:
                    lines = f.readlines()
            except Exception:
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
                    if self.music_folder: self.full_scan()
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

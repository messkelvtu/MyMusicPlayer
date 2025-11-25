import sys
import os
import json
import pygame
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QFileDialog, QSlider, QFrame, QAbstractItemView,
                             QGraphicsDropShadowEffect, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, QUrl, QSize, QPoint
from PyQt5.QtGui import QFont, QColor, QIcon, QCursor, QLinearGradient, QPalette, QBrush

# --- 配置文件路径 ---
CONFIG_FILE = "config.json"

# --- 样式表 (CSS风格) ---
STYLESHEET = """
QMainWindow { background-color: #2b2b2b; }
QWidget { color: #e0e0e0; font-family: "Microsoft YaHei"; }

/* 侧边栏 */
QFrame#Sidebar { background-color: #1e1e1e; border-right: 1px solid #333; }
QPushButton.NavBtn {
    background-color: transparent; border: none; text-align: left; padding: 12px 20px; font-size: 14px; color: #aaa;
}
QPushButton.NavBtn:hover { background-color: #333; color: white; border-left: 4px solid #1db954; }
QPushButton.NavBtn:checked { background-color: #282828; color: #1db954; border-left: 4px solid #1db954; font-weight: bold; }

/* 歌曲列表 */
QListWidget { background-color: #2b2b2b; border: none; outline: none; font-size: 14px; }
QListWidget::item { padding: 10px; border-bottom: 1px solid #333; }
QListWidget::item:selected { background-color: #333; color: #1db954; }
QListWidget::item:hover { background-color: #303030; }

/* 底部播放条 */
QFrame#PlayerBar { background-color: #181818; border-top: 1px solid #333; }
QLabel#SongTitle { font-size: 16px; font-weight: bold; color: white; }
QLabel#SongArtist { font-size: 12px; color: #888; }

/* 滚动条美化 */
QScrollBar:vertical { border: none; background: #2b2b2b; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #555; min-height: 20px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* 按钮 */
QPushButton#CtrlBtn { background: transparent; border: none; font-size: 24px; color: #ccc; }
QPushButton#CtrlBtn:hover { color: white; }
QPushButton#PlayBtn { font-size: 40px; color: #1db954; }
QPushButton#PlayBtn:hover { color: #1ed760; }

/* 歌词区 */
QLabel#LyricLine { color: #666; font-size: 14px; }
QLabel#LyricLineCurrent { color: #1db954; font-size: 22px; font-weight: bold; }
"""

# --- 桌面歌词窗口 (透明、置顶、可拖拽) ---
class DesktopLyricWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground) # 背景透明
        self.resize(800, 150)
        
        # 放到屏幕下方
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - 800) // 2, screen.height() - 200)

        # 布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # 歌词标签 (双行)
        self.label1 = QLabel("") # 上一句/下一句
        self.label2 = QLabel("桌面歌词准备就绪") # 当前句

        for lbl in [self.label1, self.label2]:
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #E0E0E0; font-family: 'Microsoft YaHei'; font-weight: bold;")
            # 文字阴影 (描边效果，防止背景干扰)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(5)
            shadow.setColor(QColor(0, 0, 0))
            shadow.setOffset(1, 1)
            lbl.setGraphicsEffect(shadow)
            layout.addWidget(lbl)

        self.font_size = 30
        self.update_font()
        
        self.is_locked = False # 是否锁定位置

    def update_font(self):
        # 渐变逻辑：主歌词大且亮，副歌词小且暗
        f1 = QFont("Microsoft YaHei", int(self.font_size * 0.6))
        f2 = QFont("Microsoft YaHei", int(self.font_size))
        self.label1.setFont(f1)
        self.label2.setFont(f2)
        
        # 颜色透明度 (rgba)
        self.label1.setStyleSheet(f"color: rgba(255, 255, 255, 150); font-weight: bold;") 
        self.label2.setStyleSheet(f"color: rgba(100, 255, 150, 255); font-weight: bold;") # 亮绿色

    def set_text(self, current, next_line=""):
        self.label2.setText(current)
        self.label1.setText(next_line)

    # --- 鼠标交互 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.is_locked:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def wheelEvent(self, event):
        # 滚轮调整大小
        delta = event.angleDelta().y()
        if delta > 0:
            self.font_size = min(80, self.font_size + 2)
        else:
            self.font_size = max(15, self.font_size - 2)
        self.update_font()

# --- 主程序 ---
class MusicApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("极客云音乐 (PyQt5 Pro)")
        self.resize(1100, 700)
        self.setStyleSheet(STYLESHEET)

        # 数据
        self.music_folder = ""
        self.playlist = [] # [{path, name}]
        self.lyrics = [] # [{time, text}]
        self.current_index = -1
        self.is_playing = False
        self.offset = 0

        # 初始化模块
        pygame.mixer.init()
        self.desktop_lyric = DesktopLyricWindow()
        self.desktop_lyric.show()

        # UI初始化
        self.init_ui()
        
        # 定时器 (用于更新进度和歌词)
        self.timer = QTimer()
        self.timer.setInterval(100) # 0.1秒刷新一次
        self.timer.timeout.connect(self.update_playback_status)
        self.timer.start()

        # 加载配置
        self.load_config()

    def init_ui(self):
        # 主窗口容器
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_widget.setLayout(main_layout)

        # 1. 侧边栏
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 20, 0, 20)
        
        logo = QLabel(" 🎵  GEEK MUSIC")
        logo.setStyleSheet("font-size: 20px; font-weight: bold; color: #1db954; padding-left: 20px;")
        side_layout.addWidget(logo)
        side_layout.addSpacing(30)

        self.btn_local = QPushButton("  📂  本地音乐")
        self.btn_local.setProperty("NavBtn", True)
        self.btn_local.setCheckable(True)
        self.btn_local.setChecked(True)
        side_layout.addWidget(self.btn_local)

        side_layout.addStretch()
        
        # 绑定文件夹按钮 (放底部)
        btn_bind = QPushButton("  ⚙️  设置音乐文件夹")
        btn_bind.setProperty("NavBtn", True)
        btn_bind.clicked.connect(self.select_folder)
        side_layout.addWidget(btn_bind)
        
        # 桌面歌词开关
        btn_dl = QPushButton("  🖥️  桌面歌词 (开/关)")
        btn_dl.setProperty("NavBtn", True)
        btn_dl.clicked.connect(self.toggle_desktop_lyric)
        side_layout.addWidget(btn_dl)

        main_layout.addWidget(sidebar)

        # 2. 右侧主区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # 中间内容 (列表 + 歌词)
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        
        # 歌曲列表
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.NoFrame)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        content_layout.addWidget(self.list_widget, stretch=3)

        # 内部歌词显示 (静态展示区)
        self.lyric_panel = QListWidget()
        self.lyric_panel.setObjectName("LyricPanel")
        self.lyric_panel.setStyleSheet("background-color: #222; border-left: 1px solid #333;")
        self.lyric_panel.setFocusPolicy(Qt.NoFocus) # 禁止获取焦点
        self.lyric_panel.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # 隐藏滚动条
        content_layout.addWidget(self.lyric_panel, stretch=2)

        right_layout.addWidget(content_area)

        # 3. 底部播放条
        player_bar = QFrame()
        player_bar.setObjectName("PlayerBar")
        player_bar.setFixedHeight(90)
        bar_layout = QHBoxLayout(player_bar)
        
        # 信息
        info_layout = QVBoxLayout()
        self.lbl_title = QLabel("未播放")
        self.lbl_title.setObjectName("SongTitle")
        self.lbl_artist = QLabel("本地音乐")
        self.lbl_artist.setObjectName("SongArtist")
        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_artist)
        bar_layout.addLayout(info_layout)
        bar_layout.addStretch()

        # 控制
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setObjectName("CtrlBtn")
        self.btn_prev.clicked.connect(self.play_prev)
        
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("PlayBtn") # 特殊样式
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_play.setCursor(Qt.PointingHandCursor)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setObjectName("CtrlBtn")
        self.btn_next.clicked.connect(self.play_next)

        bar_layout.addWidget(self.btn_prev)
        bar_layout.addSpacing(20)
        bar_layout.addWidget(self.btn_play)
        bar_layout.addSpacing(20)
        bar_layout.addWidget(self.btn_next)
        bar_layout.addStretch()

        # 音量/校准
        bar_layout.addWidget(QLabel("校准:", styleSheet="color:#888"))
        btn_off_sub = QPushButton("-0.5", clicked=lambda: self.adjust_offset(-0.5))
        btn_off_add = QPushButton("+0.5", clicked=lambda: self.adjust_offset(0.5))
        for b in [btn_off_sub, btn_off_add]:
            b.setStyleSheet("background:#333; color:white; border:none; padding:4px; margin:2px;")
            bar_layout.addWidget(b)
        
        right_layout.addWidget(player_bar)
        main_layout.addWidget(right_panel)

    # --- 逻辑处理 ---
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择音乐文件夹")
        if folder:
            self.music_folder = folder
            self.scan_music()
            self.save_config()

    def scan_music(self):
        self.playlist = []
        self.list_widget.clear()
        
        if not os.path.exists(self.music_folder): return

        files = [f for f in os.listdir(self.music_folder) if f.lower().endswith(('.mp3', '.wav'))]
        for f in files:
            self.playlist.append({"name": f, "path": os.path.join(self.music_folder, f)})
            # 去掉后缀显示
            display_name = os.path.splitext(f)[0]
            self.list_widget.addItem(display_name)
        
        if not files:
            self.list_widget.addItem("文件夹内没有 MP3 文件")

    def play_selected(self, item):
        idx = self.list_widget.row(item)
        self.play_music(idx)

    def play_music(self, idx):
        if idx < 0 or idx >= len(self.playlist): return
        
        self.current_index = idx
        song = self.playlist[idx]
        
        try:
            pygame.mixer.music.load(song["path"])
            pygame.mixer.music.play()
            self.is_playing = True
            self.btn_play.setText("⏸")
            
            # 更新信息
            self.lbl_title.setText(os.path.splitext(song["name"])[0])
            self.list_widget.setCurrentRow(idx)
            
            # 加载歌词
            lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
            self.load_lyrics(lrc_path)
            
        except Exception as e:
            print(f"Play Error: {e}")

    def toggle_play(self):
        if not self.playlist: return
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.btn_play.setText("▶")
        else:
            if self.current_index == -1: self.play_music(0)
            else:
                pygame.mixer.music.unpause()
                self.is_playing = True
                self.btn_play.setText("⏸")

    def play_next(self):
        if not self.playlist: return
        idx = (self.current_index + 1) % len(self.playlist)
        self.play_music(idx)

    def play_prev(self):
        if not self.playlist: return
        idx = (self.current_index - 1) % len(self.playlist)
        self.play_music(idx)

    # --- 歌词系统 ---
    def load_lyrics(self, path):
        self.lyrics = []
        self.lyric_panel.clear()
        self.offset = 0
        
        if os.path.exists(path):
            try:
                # 尝试不同编码
                try:
                    with open(path, 'r', encoding='utf-8') as f: lines = f.readlines()
                except:
                    with open(path, 'r', encoding='gbk') as f: lines = f.readlines()
                
                import re
                p = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\](.*)')
                for line in lines:
                    m = p.search(line)
                    if m:
                        mm, ss, ms, txt = m.groups()
                        ms_val = int(ms) if len(ms)==3 else int(ms)*10
                        t = int(mm)*60 + int(ss) + ms_val/1000
                        if txt.strip():
                            self.lyrics.append({"time": t, "text": txt.strip()})
                            
                # 填充面板
                for l in self.lyrics:
                    self.lyric_panel.addItem(l["text"])
                    
            except:
                self.lyrics = []
                self.lyric_panel.addItem("歌词读取失败")
        else:
            self.lyric_panel.addItem("纯音乐 / 无歌词")

    def update_playback_status(self):
        if self.is_playing and pygame.mixer.music.get_busy() and self.lyrics:
            pos = pygame.mixer.music.get_pos() / 1000 + self.offset
            
            # 找到当前句
            cur_idx = -1
            for i, l in enumerate(self.lyrics):
                if pos >= l["time"]: cur_idx = i
                else: break
            
            if cur_idx != -1:
                # 1. 更新主界面列表高亮
                self.lyric_panel.setCurrentRow(cur_idx)
                # 自动滚动让当前行居中
                self.lyric_panel.scrollToItem(self.lyric_panel.item(cur_idx), QAbstractItemView.PositionAtCenter)
                
                # 2. 更新桌面歌词
                txt = self.lyrics[cur_idx]["text"]
                # 尝试获取下一句
                next_txt = ""
                if cur_idx + 1 < len(self.lyrics):
                    next_txt = self.lyrics[cur_idx+1]["text"]
                self.desktop_lyric.set_text(txt, next_txt)

    def adjust_offset(self, delta):
        self.offset += delta

    def toggle_desktop_lyric(self):
        if self.desktop_lyric.isVisible():
            self.desktop_lyric.hide()
        else:
            self.desktop_lyric.show()

    # --- 配置保存 ---
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.music_folder = data.get("folder", "")
                    if self.music_folder: self.scan_music()
            except: pass

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"folder": self.music_folder}, f)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = MusicApp()
    window.show()
    sys.exit(app.exec_())

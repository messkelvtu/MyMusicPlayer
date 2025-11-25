import sys
import os
import json
import pygame
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QFileDialog, QFrame, QAbstractItemView,
                             QGraphicsDropShadowEffect, QSystemTrayIcon, QFontDialog)
from PyQt5.QtCore import Qt, QTimer, QSize, QPoint
from PyQt5.QtGui import QFont, QColor, QCursor, QIcon, QPainter, QLinearGradient

# --- 配置文件 ---
CONFIG_FILE = "config.json"

# --- 汽水风样式表 (QSS) ---
# 核心设计：白底、圆角、柔和阴影、宋体
STYLESHEET = """
QMainWindow { background-color: #FFFFFF; }
QWidget { font-family: "SimSun", "宋体", serif; color: #333333; }

/* 侧边栏 */
QFrame#Sidebar { 
    background-color: #F7F9FC; 
    border-right: 1px solid #EEEEEE; 
}
QLabel#Logo {
    font-size: 24px; font-weight: bold; color: #1ECD97; /* 薄荷绿 */
    padding: 20px;
}

/* 导航按钮 */
QPushButton.NavBtn {
    background-color: transparent; border: none; text-align: left; 
    padding: 15px 25px; font-size: 15px; color: #666; border-radius: 10px;
    margin: 5px 10px;
}
QPushButton.NavBtn:hover { background-color: #E8F5E9; color: #1ECD97; }
QPushButton.NavBtn:checked { 
    background-color: #1ECD97; color: white; 
    font-weight: bold; box-shadow: 0 4px 10px rgba(30,205,151,0.3);
}

/* 歌曲列表 */
QListWidget { background-color: #FFFFFF; border: none; outline: none; }
QListWidget::item { 
    padding: 12px; margin: 2px 10px; border-radius: 8px; border-bottom: 1px solid #F0F0F0; 
}
QListWidget::item:hover { background-color: #FAFAFA; }
QListWidget::item:selected { 
    background-color: #FFF8E1; /* 柠檬黄淡色背景 */
    color: #F9A825; border: 1px solid #FFE082;
}

/* 底部播放条 (悬浮卡片感) */
QFrame#PlayerBar { 
    background-color: #FFFFFF; 
    border-top: 1px solid #F0F0F0;
}
QLabel#SongTitle { font-size: 18px; font-weight: bold; color: #333; }
QLabel#SongArtist { font-size: 13px; color: #999; }

/* 控制按钮 */
QPushButton#CtrlBtn { 
    background: transparent; border: none; font-size: 20px; color: #888; 
}
QPushButton#CtrlBtn:hover { color: #1ECD97; transform: scale(1.1); }

QPushButton#PlayBtn { 
    background-color: #1ECD97; color: white; border-radius: 25px; 
    font-size: 24px; padding: 0; min-width: 50px; min-height: 50px;
}
QPushButton#PlayBtn:hover { background-color: #16b383; }

/* 歌词面板 (静态) */
QListWidget#LyricPanel { 
    background-color: #FFFFFF; color: #999; font-size: 14px; border:none;
}
QListWidget#LyricPanel::item:selected { 
    color: #1ECD97; font-size: 18px; font-weight: bold; background: transparent;
}

/* 滚动条 */
QScrollBar:vertical { background: transparent; width: 6px; }
QScrollBar::handle:vertical { background: #E0E0E0; border-radius: 3px; }
"""

# --- 桌面歌词窗口 (清新版) ---
class DesktopLyricWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1000, 200)
        
        # 屏幕下方显示
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - 1000) // 2, screen.height() - 250)

        # 布局：三行 (上、中、下)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5) # 行间距
        self.setLayout(self.layout)

        # 字体设置
        self.current_font = QFont("SimSun", 30) # 默认宋体
        self.current_font.setBold(True)

        # 创建三个标签：0=上一句, 1=当前句, 2=下一句
        self.labels = []
        for i in range(3):
            lbl = QLabel("")
            lbl.setAlignment(Qt.AlignCenter)
            self.labels.append(lbl)
            self.layout.addWidget(lbl)

        self.update_styles()

    def update_styles(self):
        # 样式逻辑：中间大，两边小且透明
        base_size = self.current_font.pointSize()
        
        # 颜色：白色填充，带有一点点清新的绿色阴影（不用黑色，防脏）
        shadow_color = QColor(30, 205, 151, 150) # 薄荷绿阴影

        for i, lbl in enumerate(self.labels):
            # 阴影特效
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(8)
            effect.setColor(shadow_color)
            effect.setOffset(0, 0)
            lbl.setGraphicsEffect(effect)
            
            # 字体大小和颜色
            f = QFont(self.current_font)
            if i == 1: # 中间 (当前句)
                f.setPointSize(base_size)
                # 纯白字
                lbl.setStyleSheet("color: #FFFFFF;")
            else: # 上下句
                f.setPointSize(int(base_size * 0.6))
                # 半透明白
                lbl.setStyleSheet("color: rgba(255, 255, 255, 180);")
            
            lbl.setFont(f)

    def set_lyrics(self, prev, curr, next_l):
        self.labels[0].setText(prev)
        self.labels[1].setText(curr)
        self.labels[2].setText(next_l)

    # --- 交互 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            # 右键菜单改字体
            self.change_font_dialog()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)

    def wheelEvent(self, event):
        # 滚轮改大小
        delta = event.angleDelta().y()
        size = self.current_font.pointSize()
        if delta > 0: size = min(100, size + 2)
        else: size = max(12, size - 2)
        
        self.current_font.setPointSize(size)
        self.update_styles()

    def change_font_dialog(self):
        # 字体选择器
        font, ok = QFontDialog.getFont(self.current_font, self, "选择歌词字体")
        if ok:
            # 保持大小不变，只变样式
            current_size = self.current_font.pointSize()
            self.current_font = font
            self.current_font.setPointSize(current_size)
            self.update_styles()

# --- 主程序 ---
class SodaMusicApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 (Lite)")
        self.resize(1080, 720)
        self.setStyleSheet(STYLESHEET)

        # 核心变量
        self.music_folder = ""
        self.playlist = []
        self.lyrics = []
        self.current_index = -1
        self.is_playing = False
        self.offset = 0

        pygame.mixer.init()
        self.desktop_lyric = DesktopLyricWindow()
        self.desktop_lyric.show()

        self.init_ui()
        
        self.timer = QTimer()
        self.timer.setInterval(150)
        self.timer.timeout.connect(self.update_status)
        self.timer.start()

        self.load_config()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. 侧边栏 (清新白)
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 30, 10, 30)

        logo = QLabel("🧼 SODA MUSIC")
        logo.setObjectName("Logo")
        logo.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(logo)
        side_layout.addSpacing(20)

        self.btn_all = QPushButton("💿  本地乐库")
        self.btn_all.setProperty("NavBtn", True)
        self.btn_all.setCheckable(True)
        self.btn_all.setChecked(True)
        side_layout.addWidget(self.btn_all)

        side_layout.addStretch()

        btn_folder = QPushButton("📁  管理文件夹")
        btn_folder.setProperty("NavBtn", True)
        btn_folder.clicked.connect(self.select_folder)
        side_layout.addWidget(btn_folder)
        
        btn_lyric = QPushButton("💬  桌面歌词")
        btn_lyric.setProperty("NavBtn", True)
        btn_lyric.clicked.connect(self.toggle_lyric)
        side_layout.addWidget(btn_lyric)

        layout.addWidget(sidebar)

        # 2. 右侧区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 中间内容：列表 + 内置歌词
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 0)
        
        # 列表
        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        content_layout.addWidget(self.list_widget, stretch=6)

        # 右侧内置歌词预览 (仅显示，不可动)
        self.panel_lyric = QListWidget()
        self.panel_lyric.setObjectName("LyricPanel")
        self.panel_lyric.setFocusPolicy(Qt.NoFocus)
        self.panel_lyric.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_layout.addWidget(self.panel_lyric, stretch=4)
        
        right_layout.addWidget(content)

        # 3. 底部播放条
        bar = QFrame()
        bar.setObjectName("PlayerBar")
        bar.setFixedHeight(100)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(30, 10, 30, 10)

        # 信息
        info_layout = QVBoxLayout()
        self.lbl_title = QLabel("Ready to Play")
        self.lbl_title.setObjectName("SongTitle")
        self.lbl_artist = QLabel("Local Music")
        self.lbl_artist.setObjectName("SongArtist")
        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_artist)
        bar_layout.addLayout(info_layout)
        bar_layout.addStretch()

        # 控制器
        btn_prev = QPushButton("⏮")
        btn_prev.setObjectName("CtrlBtn")
        btn_prev.clicked.connect(self.prev_song)
        
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("PlayBtn")
        self.btn_play.clicked.connect(self.toggle_play)
        
        btn_next = QPushButton("⏭")
        btn_next.setObjectName("CtrlBtn")
        btn_next.clicked.connect(self.next_song)

        bar_layout.addWidget(btn_prev)
        bar_layout.addSpacing(20)
        bar_layout.addWidget(self.btn_play)
        bar_layout.addSpacing(20)
        bar_layout.addWidget(btn_next)
        bar_layout.addStretch()

        # 微调
        bar_layout.addWidget(QLabel("Offset:", styleSheet="color:#ccc;"))
        btn_adj = QPushButton("±0.5s")
        btn_adj.clicked.connect(lambda: self.adjust_offset(0.5))
        btn_adj.setStyleSheet("border:1px solid #eee; border-radius:4px; padding:5px; color:#999;")
        bar_layout.addWidget(btn_adj)

        right_layout.addWidget(bar)
        layout.addWidget(right_panel)

    # --- 逻辑 ---
    def select_folder(self):
        f = QFileDialog.getExistingDirectory(self, "选择音乐目录")
        if f:
            self.music_folder = f
            self.scan()
            self.save_config()

    def scan(self):
        self.playlist = []
        self.list_widget.clear()
        if not os.path.exists(self.music_folder): return
        
        files = [x for x in os.listdir(self.music_folder) if x.lower().endswith(('.mp3','.wav'))]
        for f in files:
            path = os.path.join(self.music_folder, f)
            self.playlist.append({"path": path, "name": f})
            
            # 列表项显示
            name = os.path.splitext(f)[0]
            if "-" in name:
                parts = name.split("-")
                disp = f"{parts[1].strip()} - {parts[0].strip()}"
            else:
                disp = name
            
            self.list_widget.addItem(disp)

    def play_selected(self, item):
        idx = self.list_widget.row(item)
        self.play_index(idx)

    def play_index(self, idx):
        if idx < 0 or idx >= len(self.playlist): return
        self.current_index = idx
        song = self.playlist[idx]
        
        try:
            pygame.mixer.music.load(song["path"])
            pygame.mixer.music.play()
            self.is_playing = True
            self.btn_play.setText("⏸")
            
            name = os.path.splitext(song["name"])[0]
            self.lbl_title.setText(name)
            self.list_widget.setCurrentRow(idx)
            
            # 读取歌词
            lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
            self.parse_lrc(lrc_path)
            
        except Exception as e:
            print(e)

    def parse_lrc(self, path):
        self.lyrics = []
        self.panel_lyric.clear()
        self.desktop_lyric.set_lyrics("", "等待歌词...", "")
        self.offset = 0
        
        if not os.path.exists(path):
            self.panel_lyric.addItem("纯音乐 / 无歌词")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f: lines = f.readlines()
        except:
            try:
                with open(path, 'r', encoding='gbk') as f: lines = f.readlines()
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

    def update_status(self):
        if self.is_playing and pygame.mixer.music.get_busy() and self.lyrics:
            now = pygame.mixer.music.get_pos() / 1000 + self.offset
            
            # 找当前句
            idx = -1
            for i, line in enumerate(self.lyrics):
                if now >= line["t"]: idx = i
                else: break
            
            if idx != -1:
                # 1. 内置面板滚动
                self.panel_lyric.setCurrentRow(idx)
                self.panel_lyric.scrollToItem(self.panel_lyric.item(idx), QAbstractItemView.PositionAtCenter)
                
                # 2. 桌面歌词 (三行逻辑)
                prev_txt = self.lyrics[idx-1]["txt"] if idx > 0 else ""
                curr_txt = self.lyrics[idx]["txt"]
                next_txt = self.lyrics[idx+1]["txt"] if idx < len(self.lyrics)-1 else ""
                
                self.desktop_lyric.set_lyrics(prev_txt, curr_txt, next_txt)

    def toggle_play(self):
        if not self.playlist: return
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.btn_play.setText("▶")
        else:
            if self.current_index == -1: self.play_index(0)
            else:
                pygame.mixer.music.unpause()
                self.is_playing = True
                self.btn_play.setText("⏸")

    def next_song(self):
        if self.playlist:
            self.play_index((self.current_index + 1) % len(self.playlist))
            
    def prev_song(self):
        if self.playlist:
            self.play_index((self.current_index - 1) % len(self.playlist))

    def adjust_offset(self, val):
        self.offset += val

    def toggle_lyric(self):
        if self.desktop_lyric.isVisible(): self.desktop_lyric.hide()
        else: self.desktop_lyric.show()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.music_folder = json.load(f).get("folder", "")
                    if self.music_folder: self.scan()
            except: pass

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"folder": self.music_folder}, f)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 全局强制宋体
    font = QFont("SimSun")
    font.setPixelSize(14) # 默认大小
    app.setFont(font)
    
    window = SodaMusicApp()
    window.show()
    sys.exit(app.exec_())

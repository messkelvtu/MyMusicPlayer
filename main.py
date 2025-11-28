import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFrame, QLabel, QPushButton, 
                            QLineEdit, QTableWidget, QTableWidgetItem, QListWidget, 
                            QListWidgetItem, QSlider, QVBoxLayout, QHBoxLayout, 
                            QWidget, QSplitter, QScrollArea)
from PyQt5.QtCore import Qt, QUrl, QSize
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
from theme_manager import ThemeManager
from utils import LyricListSearchWorker
from bilibili_downloader import BilibiliDownloader

# 屏幕缩放管理器（处理不同分辨率适配）
class UIScaleManager:
    def get_scaled_font_size(self, screen_width, screen_height):
        base_size = 14
        scale = min(screen_width / 1920, screen_height / 1080)
        return int(base_size * scale)
    
    def get_scaled_padding(self, screen_width, screen_height):
        base_pad = 8
        scale = min(screen_width / 1920, screen_height / 1080)
        return int(base_pad * scale)
    
    def get_scaled_margin(self, screen_width, screen_height):
        base_margin = 4
        scale = min(screen_width / 1920, screen_height / 1080)
        return int(base_margin * scale)
    
    def get_scaled_icon_size(self, screen_width, screen_height):
        base_size = 24
        scale = min(screen_width / 1920, screen_height / 1080)
        return int(base_size * scale)
    
    def get_scaled_size(self, screen_width, screen_height, base_value):
        scale = min(screen_width / 1920, screen_height / 1080)
        return int(base_value * scale)

# 主窗口类
class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        # 初始化主题和缩放管理器
        self.theme_manager = ThemeManager()
        self.scale_manager = UIScaleManager()
        self.current_theme = self.theme_manager.get_theme()
        
        # 初始化UI
        self.init_ui()
        
        # 绑定信号与槽
        self.bind_signals()

    def init_ui(self):
        # 窗口基本设置
        self.setWindowTitle("音乐播放器")
        self.setGeometry(100, 100, 1200, 800)
        self.screen_width = self.width()
        self.screen_height = self.height()

        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # 1. 创建侧边栏
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setMinimumWidth(220)
        self.init_sidebar()
        main_layout.addWidget(self.sidebar)

        # 2. 创建主内容区
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        
        # 2.1 搜索栏
        self.search_box = QLineEdit()
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText("搜索歌曲、歌手...")
        content_layout.addWidget(self.search_box)
        
        # 2.2 歌曲列表表格
        self.song_table = QTableWidget()
        self.song_table.setObjectName("SongTable")
        self.song_table.setColumnCount(4)
        self.song_table.setHorizontalHeaderLabels(["歌曲", "歌手", "时长", "操作"])
        content_layout.addWidget(self.song_table)
        
        main_layout.addWidget(content_area, 3)  # 占3份宽度

        # 3. 创建右侧面板
        self.right_panel = QFrame()
        self.right_panel.setObjectName("RightPanel")
        self.right_panel.setMinimumWidth(300)
        self.init_right_panel()
        main_layout.addWidget(self.right_panel, 1)  # 占1份宽度

        # 4. 创建底部播放控制栏
        self.player_bar = QFrame()
        self.player_bar.setObjectName("PlayerBar")
        self.player_bar.setMinimumHeight(80)
        self.init_player_bar()
        content_layout.addWidget(self.player_bar)

        # 应用样式表
        self.update_stylesheet()

    def init_sidebar(self):
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        # Logo
        logo = QLabel("音乐空间")
        logo.setObjectName("Logo")
        sidebar_layout.addWidget(logo)
        
        # 导航按钮
        nav_buttons = [
            ("本地音乐", "LocalBtn"),
            ("在线推荐", "RecommendBtn"),
            ("我的收藏", "CollectionBtn"),
            ("最近播放", "RecentBtn")
        ]
        for text, obj_name in nav_buttons:
            btn = QPushButton(text)
            btn.setObjectName(obj_name)
            btn.setProperty("class", "NavBtn")
            sidebar_layout.addWidget(btn)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {self.current_theme['border']};")
        sidebar_layout.addWidget(line)
        
        # 工具按钮
        tool_buttons = [
            ("下载管理", "DownloadBtn"),
            ("设置", "SettingBtn")
        ]
        for text, obj_name in tool_buttons:
            if obj_name == "DownloadBtn":
                btn = QPushButton(text)
                btn.setObjectName(obj_name)
            else:
                btn = QPushButton(text)
                btn.setProperty("class", "ToolBtn")
            sidebar_layout.addWidget(btn)
        
        # 填充剩余空间
        sidebar_layout.addStretch()

    def init_right_panel(self):
        panel_layout = QVBoxLayout(self.right_panel)
        
        # 歌词面板
        lyric_title = QLabel("歌词")
        lyric_title.setProperty("class", "SectionTitle")
        panel_layout.addWidget(lyric_title)
        
        self.lyric_panel = QListWidget()
        self.lyric_panel.setObjectName("LyricPanel")
        panel_layout.addWidget(self.lyric_panel)
        
        # 歌单列表
        playlist_title = QLabel("我的歌单")
        playlist_title.setProperty("class", "SectionTitle")
        panel_layout.addWidget(playlist_title)
        
        self.playlist = QListWidget()
        self.playlist.setObjectName("CollectionList")
        panel_layout.addWidget(self.playlist)

    def init_player_bar(self):
        bar_layout = QHBoxLayout(self.player_bar)
        
        # 播放按钮
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("PlayBtn")
        bar_layout.addWidget(self.play_btn)
        
        # 控制按钮（上一曲、下一曲）
        prev_btn = QPushButton("◀")
        prev_btn.setProperty("class", "CtrlBtn")
        next_btn = QPushButton("▶")
        next_btn.setProperty("class", "CtrlBtn")
        bar_layout.addWidget(prev_btn)
        bar_layout.addWidget(next_btn)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Horizontal)
        bar_layout.addWidget(self.progress_slider)
        
        # 音量按钮和滑块
        vol_btn = QPushButton("🔊")
        vol_btn.setProperty("class", "CtrlBtn")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setMaximumWidth(100)
        bar_layout.addWidget(vol_btn)
        bar_layout.addWidget(self.vol_slider)

    def update_stylesheet(self):
        """更新整个界面的样式表"""
        self.setStyleSheet(generate_stylesheet(
            self.theme_manager.get_theme(),
            self.scale_manager,
            self.screen_width,
            self.screen_height
        ))

    def bind_signals(self):
        """绑定所有信号与槽函数"""
        # 搜索框回车事件
        self.search_box.returnPressed.connect(self.search_songs)
        
        # 下载按钮点击事件（示例）
        download_btn = self.findChild(QPushButton, "DownloadBtn")
        if download_btn:
            download_btn.clicked.connect(self.show_download_dialog)
        
        # 播放按钮点击事件
        self.play_btn.clicked.connect(self.toggle_play)

    def search_songs(self):
        """搜索歌曲"""
        keyword = self.search_box.text().strip()
        if not keyword:
            return
        
        # 使用线程搜索歌词（来自utils.py）
        self.search_worker = LyricListSearchWorker(keyword)
        self.search_worker.search_finished.connect(self.update_song_table)
        self.search_worker.start()

    def update_song_table(self, results):
        """更新歌曲列表表格"""
        self.song_table.setRowCount(len(results))
        for row, song in enumerate(results):
            self.song_table.setItem(row, 0, QTableWidgetItem(song['name']))
            self.song_table.setItem(row, 1, QTableWidgetItem(song['artist']))
            self.song_table.setItem(row, 2, QTableWidgetItem(song['duration_str']))
            
            # 添加播放按钮
            play_btn = QPushButton("播放")
            play_btn.setProperty("class", "ActionBtn")
            play_btn.clicked.connect(lambda checked, s=song: self.play_song(s))
            self.song_table.setCellWidget(row, 3, play_btn)

    def play_song(self, song):
        """播放歌曲（示例实现）"""
        self.play_btn.setText("⏸")
        print(f"播放: {song['name']} - {song['artist']}")

    def toggle_play(self):
        """切换播放/暂停状态"""
        if self.play_btn.text() == "▶":
            self.play_btn.setText("⏸")
            print("继续播放")
        else:
            self.play_btn.setText("▶")
            print("暂停播放")

    def show_download_dialog(self):
        """显示下载对话框（示例）"""
        url = "https://www.bilibili.com/video/BV1xx411c7mG"  # 示例URL
        save_path = os.path.join(os.path.expanduser("~"), "Music")
        
        # 创建下载线程（来自bilibili_downloader.py）
        self.downloader = BilibiliDownloader(url, save_path, 'single', 1)
        self.downloader.progress_signal.connect(self.update_download_progress)
        self.downloader.finished_signal.connect(self.download_finished)
        self.downloader.error_signal.connect(self.show_error)
        self.downloader.start()

    def update_download_progress(self, msg):
        """更新下载进度"""
        print(f"下载进度: {msg}")

    def download_finished(self, path, filename):
        """下载完成回调"""
        print(f"下载完成，保存至: {path}")

    def show_error(self, msg):
        """显示错误信息"""
        print(f"错误: {msg}")

# 样式表生成函数（来自之前的代码片段）
def generate_stylesheet(theme, scale_manager=None, screen_width=1920, screen_height=1080):
    if scale_manager is None:
        scale_manager = UIScaleManager()

    # 获取缩放后的尺寸
    font_size = scale_manager.get_scaled_font_size(screen_width, screen_height)
    padding = scale_manager.get_scaled_padding(screen_width, screen_height)
    margin = scale_manager.get_scaled_margin(screen_width, screen_height)
    icon_size = scale_manager.get_scaled_icon_size(screen_width, screen_height)

    button_height = scale_manager.get_scaled_size(screen_width, screen_height, 40)
    input_height = scale_manager.get_scaled_size(screen_width, screen_height, 44)
    table_row_height = scale_manager.get_scaled_size(screen_width, screen_height, 50)

    return f"""
/* 全局样式 */
QMainWindow {{ 
    background: {theme['background']};
    color: {theme['text_primary']};
}} 

QWidget {{ 
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    color: {theme['text_primary']};
    font-size: {font_size}px;
}}

/* 侧边栏 */
QFrame#Sidebar {{ 
    background-color: {theme['surface']};
    border-right: 1px solid {theme['border']};
}} 

QLabel#Logo {{ 
    font-size: {font_size + 10}px;
    font-weight: 900;
    color: {theme['primary']};
    padding: {padding * 3}px {padding * 2}px;
    letter-spacing: 1px;
    border-bottom: 1px solid {theme['border']};
}} 

QLabel#SectionTitle {{ 
    font-size: {font_size - 2}px;
    color: {theme['text_secondary']};
    padding: {padding * 2}px {padding * 2.5}px {padding}px {padding * 2.5}px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* 导航按钮 - 边框强调方案 */
QPushButton.NavBtn {{
    background: transparent;
    border: none;
    text-align: left;
    padding: {padding}px {padding * 2.5}px;
    font-size: {font_size}px;
    color: {theme['text_secondary']};
    border-radius: 8px;
    margin: 2px {margin * 1.5}px;
    border-left: 3px solid transparent;
    min-height: {button_height}px;
}}

QPushButton.NavBtn:hover {{
    background-color: {theme['hover']};
    color: {theme['primary']};
    border-left: 3px solid {theme['primary']};
}}

QPushButton.NavBtn:checked {{
    background: {theme['selected']};
    color: {theme['primary']};
    font-weight: 600;
    border-left: 3px solid {theme['primary']};
}}

/* 下载按钮 - 渐变方案 */
QPushButton#DownloadBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme['primary']}, stop:1 {theme['primary-light']});
    color: white;
    font-weight: bold;
    border-radius: 20px;
    text-align: center;
    margin: {margin * 2}px {margin * 2.5}px;
    padding: {padding}px;
    border: none;
    font-size: {font_size}px;
    min-height: {button_height}px;
}}

QPushButton#DownloadBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme['primary-dark']}, stop:1 {theme['primary']});
}}

/* 工具按钮 - 边框强调方案 */
QPushButton.ToolBtn {{
    background: transparent;
    border: none;
    text-align: left;
    padding: {padding}px {padding * 2.5}px;
    font-size: {font_size}px;
    color: {theme['text_secondary']};
    border-radius: 8px;
    margin: 2px {margin * 1.5}px;
    border-left: 3px solid transparent;
    min-height: {button_height}px;
}}

QPushButton.ToolBtn:hover {{
    background: {theme['hover']};
    color: {theme['primary']};
    border-left: 3px solid {theme['primary']};
}}

/* 搜索框 */
QLineEdit#SearchBox {{
    background-color: {theme['background']};
    border: 1px solid {theme['border']};
    border-radius: 20px;
    color: {theme['text_primary']};
    padding: {padding}px {padding * 2}px;
    font-size: {font_size}px;
    min-height: {input_height}px;
}}

QLineEdit#SearchBox:focus {{
    background-color: white;
    border: 1px solid {theme['primary']};
}}

/* 表格样式 */
QHeaderView::section {{ 
    background-color: {theme['background']};
    border: none;
    border-bottom: 1px solid {theme['border']};
    padding: {padding}px;
    font-weight: bold;
    color: {theme['text_secondary']};
    font-size: {font_size}px;
    min-height: {table_row_height}px; 
}}

QTableWidget {{ 
    background-color: transparent;
    border: none;
    outline: none;
    gridline-color: transparent;
    selection-background-color: transparent;
    border: 1px solid {theme['border']};
    border-radius: 12px;
    font-size: {font_size}px; 
}}

QTableWidget::item {{ 
    padding: {padding}px;
    border-bottom: 1px solid {theme['border']};
    color: {theme['text_primary']};
    min-height: {table_row_height}px; 
}}

QTableWidget::item:hover {{ 
    background-color: {theme['hover']};
}}

QTableWidget::item:selected {{ 
    background-color: {theme['selected']};
    color: {theme['primary']};
    border-radius: 6px; 
}}

/* 歌词页面 */
QWidget#LyricsPage {{ 
    background-color: {theme['background']};
}}

QListWidget#BigLyric {{ 
    background: transparent; 
    border: none; 
    outline: none; 
    font-size: {font_size + 10}px; 
    color: {theme['text_secondary']}; 
    font-weight: 600;
}}

QListWidget#BigLyric::item {{ 
    padding: {padding * 2}px; 
    text-align: center; 
    min-height: {table_row_height + 20}px;
}}

QListWidget#BigLyric::item:selected {{ 
    color: {theme['primary']}; 
    font-size: {font_size + 18}px; 
    font-weight: bold;
}}

/* 右侧面板 */
QFrame#RightPanel {{ 
    background-color: {theme['surface']}; 
    border-left: 1px solid {theme['border']};
}}

QListWidget#LyricPanel {{ 
    background: transparent; 
    border: none; 
    outline: none; 
    font-size: {font_size}px; 
    color: {theme['text_secondary']}; 
    border: 1px solid {theme['border']}; 
    border-radius: 12px;
}}

QListWidget#LyricPanel::item {{ 
    padding: {padding}px 0; 
    text-align: center; 
    min-height: {table_row_height - 10}px;
}}

QListWidget#LyricPanel::item:selected {{ 
    color: {theme['primary']}; 
    font-size: {font_size + 2}px; 
    font-weight: bold; 
    background: transparent; 
}}

/* 播放控制栏 */
QFrame#PlayerBar {{ 
    background-color: {theme['surface']}; 
    border-top: 1px solid {theme['border']};
}}

/* 播放按钮 - 渐变方案 */
QPushButton#PlayBtn {{ 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme['primary']}, stop:1 {theme['primary-light']});
    color: white;
    border: none;
    border-radius: 25px;
    font-size: {font_size + 6}px;
    min-width: {icon_size + 32}px;
    min-height: {icon_size + 32}px;
}}

QPushButton#PlayBtn:hover {{ 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme['primary-dark']}, stop:1 {theme['primary']});
}}

/* 控制按钮 - 边框强调方案 */
QPushButton.CtrlBtn {{ 
    background: transparent;
    border: 1px solid transparent;
    font-size: {font_size + 4}px;
    color: {theme['text_secondary']};
    min-width: {icon_size + 16}px;
    min-height: {icon_size + 16}px;
    border-radius: 6px;
}}

QPushButton.CtrlBtn:hover {{ 
    color: {theme['primary']};
    background: {theme['hover']};
}}

/* 偏移按钮 - 边框强调方案 */
QPushButton.OffsetBtn {{
    background: transparent;
    border: 1px solid {theme['border']};
    color: {theme['text_secondary']};
    padding: {padding}px {padding * 2}px;
    border-radius: 8px;
    font-size: {font_size - 1}px;
    min-height: {button_height - 5}px;
}}

QPushButton.OffsetBtn:hover {{
    border: 1px solid {theme['primary']};
    color: {theme['primary']};
    background: {theme['hover']};
}}

/* 进度条 */
QSlider::groove:horizontal {{
    height: {padding / 2}px;
    background: {theme['border']};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {theme['primary']};
    width: {icon_size - 10}px;
    height: {icon_size - 10}px;
    margin: {padding / 2}px 0;
    border-radius: {icon_size / 2 - 5}px;
}}

QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme['primary']}, stop:1 {theme['primary-light']});
    border-radius: 3px;
}}

/* 滚动条 */
QScrollBar:vertical {{
    border: none;
    background: {theme['background']};
    width: {padding}px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {theme['border']};
    min-height: {icon_size}px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {theme['text_tertiary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* 歌单列表 */
QListWidget#CollectionList {{
    background: transparent;
    border: none;
    font-size: {font_size}px;
    color: {theme['text_secondary']};
    outline: none;
}}

QListWidget#CollectionList::item {{
    padding: {padding}px {padding * 1.5}px;
    border-left: 2px solid transparent;
    margin: 0 {margin}px;
    border-radius: 8px;
    min-height: {table_row_height - 15}px;
}}

QListWidget#CollectionList::item:hover {{
    background: {theme['hover']};
    color: {theme['primary']};
    border-left: 2px solid {theme['primary']};
}}

QListWidget#CollectionList::item:selected {{
    background: {theme['selected']};
    color: {theme['primary']};
    font-weight: 600;
}}

/* 操作按钮 */
QPushButton.ActionBtn {{
    background: transparent;
    border: 1px solid {theme['border']};
    color: {theme['text_secondary']};
    padding: {padding}px {padding * 2}px;
    border-radius: 8px;
    font-size: {font_size - 1}px;
    min-height: {button_height - 5}px;
}}

QPushButton.ActionBtn:hover {{
    border-color: {theme['primary']};
    color: {theme['primary']};
    background: {theme['hover']};
}}

/* 歌词控制按钮 */
QPushButton.LyricControlBtn {{
    background: transparent;
    border: 1px solid {theme['border']};
    color: {theme['text_secondary']};
    padding: {padding - 2}px {padding * 1.5}px;
    border-radius: 8px;
    font-size: {font_size - 2}px;
    min-height: {button_height - 10}px;
}}

QPushButton.LyricControlBtn:hover {{
    border-color: {theme['primary']};
    color: {theme['primary']};
}}
"""

if __name__ == "__main__":
    # 确保中文显示正常
    font = QFont("SimHei")
    app = QApplication(sys.argv)
    app.setFont(font)
    
    # 创建并显示窗口
    player = MusicPlayer()
    player.show()
    
    sys.exit(app.exec_())

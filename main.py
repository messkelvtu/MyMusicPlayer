# soda_player_ac_full.py
# 完整 PyQt5 示例：AC 混合 UI + Light/Dark 切换（带动画）+ 歌词面板/桌面歌词 +
# 波形可视化(示例动画) + 卡片模式播放列表
#
# 注意：波形为示例（模拟）。要显示真实波形，请在播放线程中实时调用:
#    waveform_widget.set_waveform(your_float_array_samples)
#
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QPalette
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QFrame, QLabel, QPushButton, QHBoxLayout,
    QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QStackedWidget, QSlider,
    QSizePolicy, QTextEdit, QDialog
)
import sys, math, random, time

# --------------------------
# Waveform widget (示例动画)
# --------------------------
class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._samples = [0.0] * 256  # normalized -1..1
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)  # 25 FPS
        self._phase = 0.0
        self.setMinimumHeight(48)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_waveform(self, samples):
        """外部调用实时更新波形。samples 应为 -1..1 的浮点数组（长度不限）"""
        if not samples:
            return
        # 归一化并采样到显示数组长度
        N = len(self._samples)
        step = max(1, len(samples)//N)
        out = []
        for i in range(0, len(samples), step):
            out.append(max(-1.0, min(1.0, samples[i])))
            if len(out) >= N:
                break
        # pad/truncate
        if len(out) < N:
            out += [0.0] * (N - len(out))
        self._samples = out[:N]
        self.update()

    def _tick(self):
        # 示例模式：当没有外部数据时，生成动态正弦 + 噪声以模拟播放时的 waveform
        if all(abs(v) < 1e-6 for v in self._samples):
            N = len(self._samples)
            self._phase += 0.18
            for i in range(N):
                x = i / N * 8.0 + self._phase
                self._samples[i] = 0.2 * math.sin(x) + 0.12 * (random.random() - 0.5)
        else:
            # 微幅衰减使动画更平滑（保留外部提供的数据）
            self._samples = [s * 0.96 for s in self._samples]
        self.update()

    def paintEvent(self, ev):
        w = self.width()
        h = self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bg = self.palette().color(QPalette.Window)
        painter.fillRect(0, 0, w, h, bg)
        pen_color = self.palette().color(QPalette.Highlight)
        painter.setPen(pen_color)
        painter.setBrush(pen_color)
        N = len(self._samples)
        if N == 0:
            return
        bar_w = max(1, w / N)
        cx = h / 2.0
        for i, s in enumerate(self._samples):
            x = int(i * bar_w)
            amp = abs(s) * (h/2.0) * 0.95
            rect = QRect(int(x), int(cx - amp), int(bar_w*0.8), int(amp*2))
            painter.drawRoundedRect(rect, 2, 2)

# --------------------------
# Desktop Lyric Window
# --------------------------
class DesktopLyricWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("桌面歌词")
        self.resize(520, 140)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        layout = QVBoxLayout(self)
        self.lyric_label = QLabel("桌面歌词示例：\n—— 歌词将在这里滚动显示 ——")
        self.lyric_label.setStyleSheet("color: white; font-size:18px;")
        self.lyric_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lyric_label)
        # 拖拽支持（简单实现）
        self._drag_pos = None

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag_pos = ev.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, ev):
        if self._drag_pos:
            self.move(ev.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, ev):
        self._drag_pos = None

    def set_lyric_text(self, text):
        self.lyric_label.setText(text)

# --------------------------
# Custom Playlist Card Item
# --------------------------
class SongCard(QWidget):
    def __init__(self, title, artist, duration, cover_pixmap=None, parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(8,6,8,6)
        # cover thumbnail
        cover = QLabel()
        cover.setFixedSize(64, 64)
        if cover_pixmap and not cover_pixmap.isNull():
            cover.setPixmap(cover_pixmap.scaled(64,64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # placeholder
            cover.setStyleSheet("border-radius:8px;background:linear-gradient(45deg,#6A8BFF,#4361EE);")
        h.addWidget(cover)
        # info
        v = QVBoxLayout()
        t = QLabel(title)
        t.setStyleSheet("font-weight:700;")
        a = QLabel(f"{artist} · {duration}")
        a.setStyleSheet("color: #8b95a6; font-size:12px;")
        v.addWidget(t)
        v.addWidget(a)
        h.addLayout(v)
        # spacer
        h.addStretch()
        # play icon
        btn = QPushButton("▶")
        btn.setFixedSize(36, 36)
        btn.setObjectName("CardPlayBtn")
        h.addWidget(btn)

# --------------------------
# 主窗口
# --------------------------
class SodaMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SodaPlayer - AC 混合 (PyQt5 Demo)")
        self.resize(1180, 760)

        # central container
        central = QFrame()
        central.setObjectName("CentralFrame")
        self.setCentralWidget(central)
        self.main_layout = QHBoxLayout(central)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.setSpacing(0)

        # ---------------- Sidebar ----------------
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(12,12,12,12)
        sb_layout.setSpacing(6)

        logo = QLabel("♫ 汽水音乐")
        logo.setObjectName("Logo")
        logo.setStyleSheet("font-weight:900; font-size:18px;")
        sb_layout.addWidget(logo)

        self.download_btn = QPushButton("📺 B站音频下载")
        self.download_btn.setObjectName("DownloadBtn")
        self.download_btn.setFixedHeight(36)
        sb_layout.addWidget(self.download_btn)

        # nav buttons
        self.btn_all = QPushButton("💿 全部音乐")
        self.btn_recent = QPushButton("🕒 最近播放")
        for b in (self.btn_all, self.btn_recent):
            b.setFlat(True)
            b.setObjectName("NavBtn")
            b.setFixedHeight(36)
            sb_layout.addWidget(b)

        sb_layout.addStretch()

        # theme toggle
        self.theme_toggle_btn = QPushButton("切换主题")
        self.theme_toggle_btn.setObjectName("ThemeToggle")
        self.theme_toggle_btn.setFixedHeight(36)
        sb_layout.addWidget(self.theme_toggle_btn)

        self.main_layout.addWidget(self.sidebar)

        # ---------------- Main area ----------------
        right_area = QFrame()
        right_area.setObjectName("RightArea")
        r_layout = QVBoxLayout(right_area)
        r_layout.setContentsMargins(0,0,0,0)
        r_layout.setSpacing(0)

        # topbar
        topbar = QFrame()
        topbar.setObjectName("TopBar")
        topbar.setFixedHeight(68)
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(20,8,20,8)
        self.title_label = QLabel("正在播放")
        self.title_label.setObjectName("TitleLabel")
        tb_layout.addWidget(self.title_label)
        tb_layout.addStretch()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 搜索歌曲、歌手或专辑...")
        self.search_box.setFixedWidth(360)
        self.search_box.setObjectName("SearchBox")
        tb_layout.addWidget(self.search_box)
        r_layout.addWidget(topbar)

        # center stack (main stage / lyric)
        self.stacked_widget = QStackedWidget()
        # -- page 0: main stage (cover + controls)
        page_main = QFrame()
        page_main_layout = QHBoxLayout(page_main)
        page_main_layout.setContentsMargins(20,20,20,20)
        page_main_layout.setSpacing(20)

        # stage (left)
        self.stage_frame = QFrame()
        self.stage_frame.setObjectName("Stage")
        s_layout = QVBoxLayout(self.stage_frame)
        s_layout.setAlignment(Qt.AlignCenter)
        s_layout.setSpacing(12)

        # cover_button (使用 QLabel 以便 setPixmap)
        self.cover_button = QLabel()
        self.cover_button.setObjectName("cover_big")
        self.cover_button.setFixedSize(360,360)
        self.cover_button.setStyleSheet("border-radius:20px; background: linear-gradient(135deg,#4361EE,#6A8BFF);")
        self.song_title = QLabel("示例歌曲名 - Title")
        self.song_title.setObjectName("song_title")
        self.song_title.setAlignment(Qt.AlignCenter)
        self.song_title.setFixedHeight(36)
        self.artist_label = QLabel("示例歌手 Artist")
        self.artist_label.setObjectName("artist_label")
        self.artist_label.setAlignment(Qt.AlignCenter)

        s_layout.addWidget(self.cover_button)
        s_layout.addWidget(self.song_title)
        s_layout.addWidget(self.artist_label)

        # controls (prev/play/next)
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(18)
        self.prev_button = QPushButton("⏮")
        self.prev_button.setObjectName("PrevBtn")
        self.play_button = QPushButton("▶")
        self.play_button.setObjectName("PlayBtn")
        self.play_button.setFixedSize(78,78)
        self.next_button = QPushButton("⏭")
        self.next_button.setObjectName("NextBtn")
        ctrl_row.addWidget(self.prev_button)
        ctrl_row.addWidget(self.play_button)
        ctrl_row.addWidget(self.next_button)
        s_layout.addLayout(ctrl_row)

        # waveform under cover
        self.waveform = WaveformWidget()
        s_layout.addWidget(self.waveform)

        page_main_layout.addWidget(self.stage_frame, 3)

        # right panel (playlist as card list)
        right_panel = QFrame()
        right_panel.setObjectName("RightPanel")
        right_panel.setFixedWidth(360)
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0,0,0,0)
        rp_layout.setSpacing(6)
        rp_layout.addWidget(QLabel("播放列表", objectName="QueueTitle"))

        self.song_table = QListWidget()
        self.song_table.setObjectName("SongTable")
        self.song_table.setSpacing(6)
        self.song_table.setStyleSheet("QListWidget::item{margin:0;padding:0;border:none;}")
        rp_layout.addWidget(self.song_table)

        # lyric toggle + desktop lyric
        btn_row = QHBoxLayout()
        self.toggle_lyric_btn = QPushButton("📜 歌词")
        self.toggle_lyric_btn.setObjectName("LyricSwitch")
        self.desktop_lyric_btn = QPushButton("📺 桌面歌词")
        self.desktop_lyric_btn.setObjectName("DesktopLyric")
        btn_row.addWidget(self.toggle_lyric_btn)
        btn_row.addWidget(self.desktop_lyric_btn)
        rp_layout.addLayout(btn_row)

        page_main_layout.addWidget(right_panel, 1)

        # -- page 1: lyric page (示例)
        page_lyric = QFrame()
        ly_layout = QVBoxLayout(page_lyric)
        self.lyric_textedit = QTextEdit()
        self.lyric_textedit.setReadOnly(True)
        self.lyric_textedit.setText("这里显示歌词...\nLine 1\nLine 2\nLine 3")
        ly_layout.addWidget(self.lyric_textedit)

        self.stacked_widget.addWidget(page_main)
        self.stacked_widget.addWidget(page_lyric)

        r_layout.addWidget(self.stacked_widget)

        # bottom player bar (progress + mini info)
        player_bar = QFrame()
        player_bar.setObjectName("PlayerBar")
        player_bar.setFixedHeight(96)
        pb_layout = QVBoxLayout(player_bar)
        pb_layout.setContentsMargins(18,8,18,8)
        # progress row
        progress_row = QHBoxLayout()
        self.time_label_left = QLabel("00:00")
        self.time_label_left.setObjectName("TimeLeft")
        self.time_label_right = QLabel("04:01")
        self.time_label_right.setObjectName("TimeRight")
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setObjectName("Progress")
        progress_row.addWidget(self.time_label_left)
        progress_row.addWidget(self.progress_slider)
        progress_row.addWidget(self.time_label_right)
        pb_layout.addLayout(progress_row)
        # bottom control row (mini info + control center + volume)
        bottom_row = QHBoxLayout()
        # mini info
        mini = QHBoxLayout()
        self.mini_cover = QLabel()
        self.mini_cover.setFixedSize(46,46)
        self.mini_cover.setStyleSheet("border-radius:8px;background:linear-gradient(45deg,#4361EE,#6A8BFF);")
        mini.addWidget(self.mini_cover)
        self.mini_title = QLabel("--")
        mini.addWidget(self.mini_title)
        mini.addStretch()
        bottom_row.addLayout(mini)
        # center controls placeholder (keeps space)
        center_ctrl = QHBoxLayout()
        center_ctrl.addStretch()
        bottom_row.addLayout(center_ctrl)
        # volume
        vol_layout = QHBoxLayout()
        self.volume_label = QLabel("🔊")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setFixedWidth(120)
        vol_layout.addWidget(self.volume_label)
        vol_layout.addWidget(self.volume_slider)
        bottom_row.addLayout(vol_layout)

        pb_layout.addLayout(bottom_row)
        r_layout.addWidget(player_bar)

        self.main_layout.addWidget(right_area)
        self.main_layout.addWidget(right_area)  # placeholder overwritten below

        # replace placeholder: we want sidebar + right_area as main layout
        self.main_layout.removeWidget(right_area)
        self.main_layout.addWidget(right_area)

        # ---------- desktop lyric window ----------
        self.desktop_lyric_window = DesktopLyricWindow(self)

        # ---------- fill sample playlist ----------
        for i in range(1,13):
            item = QListWidgetItem()
            card = SongCard(f"Song {i:02d}", f"Artist {i}", f"0{3+i%2}:{10+i%50:02d}")
            item.setSizeHint(card.sizeHint())
            self.song_table.addItem(item)
            self.song_table.setItemWidget(item, card)

        # ---------- state ----------
        self._dark = False
        self.apply_theme(self._dark)  # initial theme
        self.connect_signals()

    # ----------------- signal connections -----------------
    def connect_signals(self):
        self.theme_toggle_btn.clicked.connect(self.toggle_theme_animated)
        self.toggle_lyric_btn.clicked.connect(self.toggle_lyric_panel)
        self.desktop_lyric_btn.clicked.connect(self.show_desktop_lyric)
        self.play_button.clicked.connect(self.play_pause_toggle)
        # simulate progress timer
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._simulate_progress)
        self._playing = False
        self.progress_slider.setRange(0, 240)
        self.progress_slider.setValue(0)

    # ----------------- theme handling -----------------
    def apply_theme(self, dark=False):
        """应用 Light / Dark 主题（直接替换 QSS 变量）"""
        if dark:
            var = {
                "primary":"#6A8BFF",
                "primary_light":"#8BA4FF",
                "background":"#0F1115",
                "surface":"#1C1F24",
                "border":"#2D3036",
                "text_primary":"#E4E6EB",
                "text_secondary":"#A1A5AE",
                "hover":"rgba(130,150,255,0.12)"
            }
        else:
            var = {
                "primary":"#4361EE",
                "primary_light":"#6A8BFF",
                "background":"#F8FAFC",
                "surface":"#FFFFFF",
                "border":"#E2E8F0",
                "text_primary":"#2D3748",
                "text_secondary":"#718096",
                "hover":"rgba(67,97,238,0.08)"
            }

        qss = f"""
        /* root-like variables via simple string replacement */
        QMainWindow, QFrame#CentralFrame {{ background: {var['background']}; color: {var['text_primary']}; }}
        QFrame#Sidebar {{ background: {var['surface']}; border-right: 1px solid {var['border']}; }}
        QLabel#Logo {{ color: {var['primary']}; }}
        QPushButton#DownloadBtn {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {var['primary']}, stop:1 {var['primary_light']}); color: white; border-radius:8px; }}
        QPushButton#NavBtn {{ text-align:left; padding-left:6px; color: {var['text_secondary']}; }}
        QFrame#TopBar {{ background: transparent; }}
        QLineEdit#SearchBox {{ background: transparent; border:1px solid {var['border']}; border-radius:18px; padding:8px; color: {var['text_primary']}; }}
        QLabel#TitleLabel {{ color: {var['primary']}; font-weight:700; font-size:18px; }}
        QFrame#RightPanel {{ background: {var['surface']}; border-left:1px solid {var['border']}; }}
        QListWidget#SongTable {{ background: transparent; border: none; }}
        QPushButton#PlayBtn {{ border-radius:39px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {var['primary']}, stop:1 {var['primary_light']}); color: white; font-size:20px; }}
        QPushButton#LyricSwitch, QPushButton#DesktopLyric, QPushButton#ThemeToggle {{ background: transparent; border:1px solid {var['border']}; padding:6px; border-radius:8px; }}
        QFrame#PlayerBar {{ background: {var['surface']}; border-top:1px solid {var['border']}; }}
        QLabel#TimeLeft, QLabel#TimeRight {{ color: {var['text_secondary']}; }}
        /* small card play btn */
        QPushButton#CardPlayBtn {{ background: {var['primary']}; color: white; border-radius:6px; }}
        """
        self.setStyleSheet(qss)
        # palette adjust for Waveform / Desktop lyric background
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(var['background']))
        pal.setColor(QPalette.WindowText, QColor(var['text_primary']))
        pal.setColor(QPalette.Highlight, QColor(var['primary']))
        self.setPalette(pal)

    def toggle_theme_animated(self):
        # 简单淡色/深色切换动画（这里用定时器模拟渐变：直接切换样式更稳定）
        self._dark = not self._dark
        # 如果你想更复杂动画，可以在此实现 QPropertyAnimation 显示蒙版渐变，当前直接切换主题
        self.apply_theme(self._dark)

    # ----------------- play / progress (模拟) -----------------
    def play_pause_toggle(self):
        if not self._playing:
            self.play_button.setText("▮▮")
            self._play_timer.start(800)
            self._playing = True
        else:
            self.play_button.setText("▶")
            self._play_timer.stop()
            self._playing = False

    def _simulate_progress(self):
        v = self.progress_slider.value()
        if v >= self.progress_slider.maximum():
            self.progress_slider.setValue(0)
            self.play_button.setText("▶")
            self._play_timer.stop()
            self._playing = False
        else:
            self.progress_slider.setValue(v + 1)
            # 模拟实时波形：生成一段小波形并推送到 waveform
            N = 256
            t = time.time()
            samples = [0.3 * math.sin(2*math.pi*(i/40.0) + t*5.0) * (0.8 + 0.2*random.random()) for i in range(N)]
            self.waveform.set_waveform(samples)
            # desktop lyric demo更新（你会用实际歌词逻辑替换）
            if (v % 20) == 0:
                self.desktop_lyric_window.set_lyric_text(f"正在播放: {self.song_title.text()}\n进度 {v}/{self.progress_slider.maximum()}")

    # ----------------- lyric / desktop lyric -----------------
    def toggle_lyric_panel(self):
        idx = self.stacked_widget.currentIndex()
        if idx == 0:
            self.stacked_widget.setCurrentIndex(1)
            self.toggle_lyric_btn.setText("🎵 播放界面")
        else:
            self.stacked_widget.setCurrentIndex(0)
            self.toggle_lyric_btn.setText("📜 歌词")

    def show_desktop_lyric(self):
        # 在真正项目中，把当前歌词文本和高亮行传入 desktop window
        self.desktop_lyric_window.set_lyric_text(self.lyric_textedit.toPlainText())
        self.desktop_lyric_window.show()

# --------------------------
# 启动
# --------------------------
def main():
    app = QApplication(sys.argv)
    w = SodaMainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

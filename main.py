# 在原有代码基础上，替换 STYLESHEET 变量为以下现代化样式：

# --- 2025年现代化UI样式表 ---
STYLESHEET = """
/* 主窗口样式 - 现代化毛玻璃效果 */
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                               stop:0 #0f0f23, stop:0.5 #1a1a2e, stop:1 #16213e);
    font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif;
    color: #ffffff;
    border-radius: 16px;
}

/* 现代化标题栏 */
QMainWindow::title {
    background: transparent;
    color: white;
    font-weight: 600;
}

/* 侧边栏样式 - 现代化毛玻璃效果 */
QFrame#Sidebar {
    background: rgba(255, 255, 255, 0.08);
    border-right: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px 0 0 16px;
    backdrop-filter: blur(20px);
}

QLabel#Logo {
    font-size: 24px;
    font-weight: 700;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #00d2ff, stop:1 #3a7bd5);
    -webkit-background-clip: text;
    color: transparent;
    padding: 25px 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

QLabel#SectionTitle {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.5);
    padding: 20px 20px 8px 20px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* 现代化导航按钮 */
QPushButton.NavBtn {
    background: transparent;
    border: none;
    text-align: left;
    padding: 14px 20px;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.8);
    border-radius: 12px;
    margin: 4px 15px;
    transition: all 0.3s ease;
    font-weight: 500;
}

QPushButton.NavBtn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #ffffff;
    transform: translateX(5px);
}

QPushButton.NavBtn:checked {
    background: rgba(58, 123, 213, 0.3);
    color: #00d2ff;
    font-weight: 600;
    border-left: 3px solid #00d2ff;
    backdrop-filter: blur(10px);
}

/* 现代化下载按钮 */
QPushButton#DownloadBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #00d2ff, stop:1 #3a7bd5);
    color: white;
    font-weight: 600;
    border-radius: 25px;
    margin: 20px 15px;
    padding: 14px;
    border: none;
    font-size: 14px;
    min-height: 25px;
    box-shadow: 0 4px 15px rgba(0, 210, 255, 0.3);
    transition: all 0.3s ease;
}

QPushButton#DownloadBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #3a7bd5, stop:1 #00d2ff);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 210, 255, 0.4);
}

/* 现代化表格样式 */
QTableWidget {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    margin: 15px;
    selection-background-color: rgba(0, 210, 255, 0.2);
    selection-color: #00d2ff;
    gridline-color: rgba(255, 255, 255, 0.05);
    outline: none;
    font-size: 13px;
    backdrop-filter: blur(10px);
}

QHeaderView::section {
    background: rgba(255, 255, 255, 0.08);
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding: 15px 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
    font-size: 12px;
}

QTableWidget::item {
    padding: 12px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.9);
}

QTableWidget::item:selected {
    background: rgba(0, 210, 255, 0.15);
    color: #00d2ff;
    border-radius: 6px;
}

QTableWidget::item:hover {
    background: rgba(255, 255, 255, 0.05);
}

/* 现代化歌词面板 */
QListWidget#LyricPanel {
    background: transparent;
    border: none;
    outline: none;
    font-size: 15px;
    color: rgba(255, 255, 255, 0.6);
    backdrop-filter: blur(5px);
}

QListWidget#LyricPanel::item {
    padding: 16px 20px;
    border: none;
    background: transparent;
    text-align: center;
    color: rgba(255, 255, 255, 0.6);
    border-radius: 8px;
    margin: 2px 10px;
}

QListWidget#LyricPanel::item:selected {
    background: rgba(0, 210, 255, 0.2);
    color: #00d2ff;
    font-weight: 700;
    font-size: 18px;
    transform: scale(1.02);
}

QListWidget#LyricPanel::item:hover {
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.8);
}

/* 现代化播放控制栏 */
QFrame#PlayerBar {
    background: rgba(255, 255, 255, 0.08);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(25px);
    border-radius: 0 0 16px 0;
}

QPushButton#PlayBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                               stop:0 #00d2ff, stop:1 #3a7bd5);
    color: white;
    border-radius: 50%;
    font-size: 18px;
    min-width: 60px;
    min-height: 60px;
    border: none;
    box-shadow: 0 8px 25px rgba(0, 210, 255, 0.4);
    transition: all 0.3s ease;
}

QPushButton#PlayBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                               stop:0 #3a7bd5, stop:1 #00d2ff);
    transform: scale(1.1) rotate(5deg);
    box-shadow: 0 12px 30px rgba(0, 210, 255, 0.6);
}

QPushButton.CtrlBtn {
    background: rgba(255, 255, 255, 0.1);
    border: none;
    font-size: 20px;
    color: rgba(255, 255, 255, 0.8);
    border-radius: 50%;
    padding: 10px;
    min-width: 44px;
    min-height: 44px;
    transition: all 0.3s ease;
}

QPushButton.CtrlBtn:hover {
    color: #00d2ff;
    background: rgba(0, 210, 255, 0.2);
    transform: scale(1.1);
}

QPushButton.OffsetBtn {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 20px;
    color: rgba(255, 255, 255, 0.8);
    font-size: 12px;
    padding: 8px 16px;
    transition: all 0.3s ease;
}

QPushButton.OffsetBtn:hover {
    background: #00d2ff;
    border-color: #00d2ff;
    color: #0f0f23;
    transform: translateY(-1px);
}

/* 现代化进度条 */
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: rgba(255, 255, 255, 0.1);
    margin: 0px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    border: 3px solid #00d2ff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #00d2ff, stop:1 #3a7bd5);
    border-radius: 3px;
}

/* 音量滑块 */
QSlider#VolumeSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: rgba(255, 255, 255, 0.1);
    margin: 0px;
    border-radius: 2px;
}

QSlider#VolumeSlider::handle:horizontal {
    background: #ffffff;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 2px solid #00d2ff;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

QSlider#VolumeSlider::sub-page:horizontal {
    background: #00d2ff;
    border-radius: 2px;
}

/* 现代化输入控件 */
QLineEdit, QComboBox, QTextEdit {
    padding: 12px 16px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.08);
    color: #ffffff;
    font-size: 14px;
    selection-background-color: rgba(0, 210, 255, 0.3);
    backdrop-filter: blur(10px);
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border-color: #00d2ff;
    background: rgba(255, 255, 255, 0.12);
    outline: none;
}

QLineEdit::placeholder {
    color: rgba(255, 255, 255, 0.4);
}

QComboBox::drop-down {
    border: none;
    width: 35px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 6px solid rgba(255, 255, 255, 0.6);
    width: 0px;
    height: 0px;
}

QComboBox QAbstractItemView {
    background: rgba(40, 40, 60, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    color: white;
    selection-background-color: rgba(0, 210, 255, 0.3);
    backdrop-filter: blur(20px);
}

/* 现代化对话框 */
QDialog {
    background: rgba(40, 40, 60, 0.95);
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(30px);
}

QGroupBox {
    font-weight: 600;
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    margin-top: 10px;
    padding-top: 15px;
    background: rgba(255, 255, 255, 0.05);
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 10px;
    color: rgba(255, 255, 255, 0.8);
}

/* 现代化按钮 */
QPushButton {
    padding: 10px 20px;
    border-radius: 10px;
    font-size: 14px;
    border: none;
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
    transition: all 0.3s ease;
    font-weight: 500;
}

QPushButton:hover {
    background: rgba(255, 255, 255, 0.15);
    transform: translateY(-1px);
}

QPushButton:pressed {
    background: rgba(255, 255, 255, 0.2);
    transform: translateY(0);
}

QPushButton[style*="primary"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d2ff, stop:1 #3a7bd5);
    color: white;
}

QPushButton[style*="primary"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a7bd5, stop:1 #00d2ff);
}

/* 现代化标签页 */
QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
}

QTabWidget::tab-bar {
    alignment: center;
}

QTabBar::tab {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-bottom: none;
    padding: 10px 20px;
    margin-right: 3px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    color: rgba(255, 255, 255, 0.7);
    transition: all 0.3s ease;
}

QTabBar::tab:selected {
    background: rgba(0, 210, 255, 0.2);
    border-color: rgba(0, 210, 255, 0.3);
    border-bottom: 1px solid rgba(0, 210, 255, 0.2);
    color: #00d2ff;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background: rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.9);
}

/* 现代化复选框和单选框 */
QCheckBox, QRadioButton {
    spacing: 12px;
    color: rgba(255, 255, 255, 0.9);
    font-weight: 500;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 20px;
    height: 20px;
    border-radius: 5px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    background: rgba(255, 255, 255, 0.1);
}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: #00d2ff;
    border: 2px solid #00d2ff;
    image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'%3E%3Cpath d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z'/%3E%3C/svg%3E");
}

QRadioButton::indicator {
    border-radius: 10px;
}

QRadioButton::indicator:checked {
    background: #00d2ff;
    border: 2px solid #00d2ff;
    image: none;
}

/* 现代化滚动条 */
QScrollBar:vertical {
    border: none;
    background: rgba(255, 255, 255, 0.05);
    width: 12px;
    margin: 0px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    min-height: 25px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(0, 210, 255, 0.6);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}

/* 现代化进度条 */
QProgressBar {
    border: none;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    text-align: center;
    color: white;
    font-size: 12px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #00d2ff, stop:1 #3a7bd5);
    border-radius: 6px;
}

/* 现代化菜单 */
QMenu {
    background: rgba(40, 40, 60, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 8px;
    color: white;
    backdrop-filter: blur(20px);
}

QMenu::item {
    padding: 8px 16px;
    border-radius: 6px;
    margin: 2px;
}

QMenu::item:selected {
    background: rgba(0, 210, 255, 0.3);
    color: #00d2ff;
}

QMenu::separator {
    height: 1px;
    background: rgba(255, 255, 255, 0.1);
    margin: 5px 10px;
}

/* 现代化消息框 */
QMessageBox {
    background: rgba(40, 40, 60, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    backdrop-filter: blur(30px);
}

QMessageBox QLabel {
    color: white;
}

/* 现代化工具栏按钮 */
QToolButton {
    background: rgba(255, 255, 255, 0.1);
    border: none;
    border-radius: 8px;
    padding: 8px;
    color: rgba(255, 255, 255, 0.8);
}

QToolButton:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #00d2ff;
}

/* 现代化分割线 */
QSplitter::handle {
    background: rgba(255, 255, 255, 0.1);
}

QSplitter::handle:hover {
    background: rgba(0, 210, 255, 0.3);
}

/* 现代化工具提示 */
QToolTip {
    background: rgba(40, 40, 60, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: white;
    padding: 8px;
    font-size: 12px;
    backdrop-filter: blur(20px);
}
"""

# 在 ModernSodaPlayer 类的 init_ui 方法中，添加以下现代化特性：

class ModernSodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        # 设置现代化窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint)  # 无边框窗口
        self.setAttribute(Qt.WA_TranslucentBackground)  # 透明背景
        
        # 其他初始化代码保持不变...
        
    def init_ui(self):
        # 在原有基础上，添加一些现代化改进：
        
        # 1. 添加现代化标题栏
        self.setup_modern_titlebar()
        
        # 2. 添加现代化动画效果
        self.setup_animations()
        
        # 3. 其他UI初始化代码...
        
    def setup_modern_titlebar(self):
        """设置现代化标题栏"""
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                       stop:0 rgba(15, 15, 35, 0.9), 
                                       stop:1 rgba(26, 26, 46, 0.9));
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 15, 0)
        
        # 标题
        title_label = QLabel("🎵 汽水音乐 2025")
        title_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            font-weight: 600;
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 窗口控制按钮
        btn_minimize = self.create_title_button("−")
        btn_maximize = self.create_title_button("□")
        btn_close = self.create_title_button("×")
        
        btn_minimize.clicked.connect(self.showMinimized)
        btn_maximize.clicked.connect(self.toggle_maximize)
        btn_close.clicked.connect(self.close)
        
        title_layout.addWidget(btn_minimize)
        title_layout.addWidget(btn_maximize)
        title_layout.addWidget(btn_close)
        
        # 将标题栏添加到主布局
        self.centralWidget().layout().insertWidget(0, title_bar)
        
    def create_title_button(self, text):
        """创建标题栏按钮"""
        btn = QPushButton(text)
        btn.setFixedSize(25, 25)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: white;
            }
            QPushButton#close:hover {
                background: #ff4757;
                color: white;
            }
        """)
        if text == "×":
            btn.setObjectName("close")
        return btn
        
    def toggle_maximize(self):
        """切换最大化状态"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
            
    def setup_animations(self):
        """设置现代化动画效果"""
        # 这里可以添加各种现代化动画效果
        pass
        
    def mousePressEvent(self, event):
        """实现无边框窗口拖动"""
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """实现无边框窗口拖动"""
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

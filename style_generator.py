from ui_scale_manager import UIScaleManager

# --- 样式表生成器 ---
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
    background: {theme['hover']};
}}

/* 歌曲操作按钮 */
QPushButton.SongActionBtn {{
    background: transparent;
    border: none;
    color: {theme['text_secondary']};
    padding: {padding - 2}px;
    border-radius: 4px;
    font-size: {font_size}px;
    min-width: {icon_size}px;
    min-height: {icon_size}px;
}}

QPushButton.SongActionBtn:hover {{
    color: {theme['primary']};
    background: {theme['hover']};
}}

/* 对话框样式 */
QDialog {{
    background: {theme['surface']};
    color: {theme['text_primary']};
    border: 1px solid {theme['border']};
    border-radius: 16px;
    font-size: {font_size}px;
}}

QDialog QLabel {{
    color: {theme['text_primary']};
    font-size: {font_size}px;
    padding: {padding / 2}px;
}}

QDialog QLineEdit {{
    background: {theme['background']};
    border: 1px solid {theme['border']};
    border-radius: 8px;
    color: {theme['text_primary']};
    padding: {padding}px {padding * 1.5}px;
    font-size: {font_size}px;
    min-height: {input_height}px;
    selection-background-color: {theme['selected']};
}}

QDialog QLineEdit:focus {{
    border: 1px solid {theme['primary']};
    background: white;
}}

QDialog QCheckBox {{
    color: {theme['text_primary']};
    font-size: {font_size}px;
    spacing: {padding}px;
    min-height: {icon_size}px;
}}

QDialog QCheckBox::indicator {{
    width: {icon_size - 6}px;
    height: {icon_size - 6}px;
    border-radius: 4px;
    border: 1px solid {theme['border']};
}}

QDialog QCheckBox::indicator:checked {{
    background: {theme['primary']};
    border: 1px solid {theme['primary']};
}}

QDialog QPushButton {{
    padding: {padding}px {padding * 2}px;
    border-radius: 8px;
    font-size: {font_size}px;
    font-weight: 600;
    min-height: {button_height}px;
}}

QDialog QPushButton[class="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme['primary']}, stop:1 {theme['primary-light']});
    color: white;
    border: none;
}}

QDialog QPushButton[class="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme['primary-dark']}, stop:1 {theme['primary']});
}}

QDialog QPushButton[class="outline"] {{
    background: transparent;
    color: {theme['primary']};
    border: 1px solid {theme['primary']};
}}

QDialog QPushButton[class="outline"]:hover {{ 
    background: {theme['hover']}; 
}}

QDialog QTabWidget::pane {{ 
    border: 1px solid {theme['border']}; 
    border-radius: 8px; 
}}

QDialog QTabBar::tab {{ 
    background: transparent; 
    padding: {padding}px {padding * 2}px; 
    border: none; 
    color: {theme['text_secondary']}; 
    border-bottom: 2px solid transparent; 
    min-height: {button_height}px; 
}}

QDialog QTabBar::tab:selected {{ 
    color: {theme['primary']}; 
    border-bottom: 2px solid {theme['primary']}; 
}}

QDialog QComboBox {{ 
    background: {theme['background']}; 
    border: 1px solid {theme['border']}; 
    border-radius: 8px; 
    color: {theme['text_primary']}; 
    padding: {padding}px {padding * 1.5}px; 
    font-size: {font_size}px; 
    min-height: {input_height}px; 
}}

QDialog QComboBox:focus {{ 
    border: 1px solid {theme['primary']}; 
}}

QDialog QComboBox::drop-down {{ 
    border: none; 
    width: {icon_size}px; 
}}

QDialog QComboBox::down-arrow {{ 
    image: none;
    border-left: 1px solid {theme['border']};
    padding: 0 {padding}px;
}}

QDialog QSpinBox {{
    background: {theme['background']};
    border: 1px solid {theme['border']};
    border-radius: 8px;
    color: {theme['text_primary']};
    padding: {padding}px {padding * 1.5}px;
    font-size: {font_size}px;
    min-height: {input_height}px;
}}

QDialog QSpinBox:focus {{
    border: 1px solid {theme['primary']};
}}

/* 分割器样式 */
QSplitter::handle {{
    background: rgba(76, 175, 80, 0.1);
    width: {padding / 2}px;
    height: {padding / 2}px;
}}

/* 分组框样式 */
QGroupBox {{
    font-weight: bold;
    border: 1px solid {theme['border']};
    border-radius: 8px;
    margin-top: {padding * 1.5}px;
    padding-top: {padding * 1.5}px;
    font-size: {font_size}px;
    color: {theme['text_primary']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: {padding}px;
    padding: 0 {padding}px;
    color: {theme['text_primary']};
}}

/* 进度条样式 */
QProgressBar {{  
    border: 1px solid {theme['border']};  
    border-radius: 4px;  
    background: {theme['background']};  
    text-align: center;  
    color: {theme['text_primary']};  
    font-size: {font_size - 1}px;  
}}

QProgressBar::chunk {{  
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme['primary']}, stop:1 {theme['primary-light']});  
    border-radius: 3px;  
}}

/* 菜单样式 */  
QMenu {{  
    background: {theme['surface']};  
    color: {theme['text_primary']};  
    border: 1px solid {theme['border']};  
    border-radius: 8px;  
    padding: {padding / 2}px;  
    font-size: {font_size}px;  
}}

QMenu::item {{  
    padding: {padding}px {padding * 1.5}px;  
    border-radius: 4px;  
    min-height: {button_height - 5}px;  
}}

QMenu::item:selected {{  
    background: {theme['selected']};  
    color: {theme['primary']};  
}}

QMenu::separator {{  
    height: 1px;  
    background: {theme['border']};  
    margin: {padding / 2}px {padding}px;  
}}
"""

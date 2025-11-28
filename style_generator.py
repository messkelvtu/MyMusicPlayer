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
    box-shadow: 2px 0 5px {theme['shadow']};  /* 新增侧边栏阴影 */
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
    transition: all 0.2s ease;  /* 新增过渡动画 */
}}

QPushButton.NavBtn:hover {{
    background-color: {theme['hover']};
    color: {theme['primary']};
    border-left: 3px solid {theme['primary']};
    transform: translateX(2px);  /*  hover时轻微右移 */
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
    box-shadow: 0 2px 5px {theme['shadow']};  /* 新增按钮阴影 */
    transition: all 0.2s ease;
}}

QPushButton#DownloadBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme['primary-dark']}, stop:1 {theme['primary']});
    transform: translateY(-1px);  /* 轻微上浮 */
    box-shadow: 0 4px 8px {theme['shadow']};
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
    transition: all 0.2s ease;
}}

QLineEdit#SearchBox:focus {{
    background-color: {theme['surface']};  /* 适配深色主题 */
    border: 1px solid {theme['primary']};
    box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);  /* 聚焦高亮效果 */
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
    border: 1px solid {theme['border']};
    border-radius: 12px;
    font-size: {font_size}px; 
    padding: {padding}px;  /* 内部边距 */
}}

QTableWidget::item {{ 
    padding: {padding}px;
    border-bottom: 1px solid {theme['border']};
    color: {theme['text_primary']};
    min-height: {table_row_height}px; 
    border-radius: 6px;  /* 单元格圆角 */
}}

/* 歌词相关样式 */
QListWidget#BigLyric {{ 
    background: transparent; 
    border: none; 
    outline: none; 
    font-size: {font_size + 10}px; 
    color: {theme['text_secondary']}; 
    font-weight: 600;
}}

QListWidget#BigLyric::item:selected {{ 
    color: {theme['primary']}; 
    font-size: {font_size + 18}px; 
    font-weight: bold;
    text-shadow: 0 1px 3px {theme['shadow']};  /* 歌词高亮阴影 */
}}

/* 播放控制栏 */
QFrame#PlayerBar {{ 
    background-color: {theme['surface']}; 
    border-top: 1px solid {theme['border']};
    box-shadow: 0 -2px 10px {theme['shadow']};  /* 底部阴影 */
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
    box-shadow: 0 3px 8px {theme['shadow']};
    transition: all 0.2s ease;
}}

QPushButton#PlayBtn:hover {{ 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme['primary-dark']}, stop:1 {theme['primary']});
    transform: scale(1.05);  /* 轻微放大 */
}}

/* 进度条 */
QSlider::groove:horizontal {{
    height: {padding / 2}px;
    background: {theme['border']};
    border-radius: 3px;
    margin: {padding}px 0;  /* 增加上下边距 */
}}

QSlider::handle:horizontal {{
    background: {theme['primary']};
    width: {icon_size - 10}px;
    height: {icon_size - 10}px;
    margin: {padding / 2}px 0;
    border-radius: {icon_size / 2 - 5}px;
    box-shadow: 0 1px 3px {theme['shadow']};
    transition: all 0.1s ease;
}}

QSlider::handle:horizontal:hover {{
    transform: scale(1.1);  /* 鼠标悬停放大 */
}}

/* 滚动条优化 */
QScrollBar:vertical {{
    border: none;
    background: {theme['background']};
    width: {padding}px;
    margin: {padding}px 0;  /* 增加上下边距 */
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {theme['border']};
    min-height: {icon_size}px;
    border-radius: 4px;
    transition: background 0.2s ease;
}}

QScrollBar::handle:vertical:hover {{
    background: {theme['primary-light']};
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
    transition: all 0.2s ease;
}}

QPushButton.ActionBtn:hover {{
    border-color: {theme['primary']};
    color: {theme['primary']};
    background: {theme['hover']};
    box-shadow: 0 2px 5px {theme['shadow']};
}}
"""

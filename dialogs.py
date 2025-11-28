from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
                           QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                           QLabel, QMessageBox, QGroupBox, QRadioButton, QComboBox,
                           QTabWidget, QWidget, QSlider, QApplication, QColorDialog,
                           QFontDialog, QInputDialog, QFileDialog, QCheckBox, QSpinBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from ui_scale_manager import UIScaleManager
from theme_manager import ThemeManager
from style_generator import generate_stylesheet
from utils import ICONS, LyricListSearchWorker, LyricDownloader

# -- 对话框类 --  
class LyricSearchDialog(QDialog):  
    def __init__(self, song_name, duration_ms=0, parent=None):  
        super().__init__(parent)  
        self.setWindowTitle("搜索歌词")  

        # 获取屏幕尺寸和缩放管理器  
        screen = QApplication.primaryScreen()  
        screen_size = screen.size()  
        self.scale_manager = parent.scale_manager if hasattr(parent, 'scale_manager') else UIScaleManager()  
        self.theme_manager = parent.theme_manager if hasattr(parent, 'theme_manager') else ThemeManager()

        # 设置对话框尺寸
        dialog_width = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 700)
        dialog_height = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 500)
        self.resize(dialog_width, dialog_height)

        self.result_id = None
        self.duration_ms = duration_ms

        theme = self.theme_manager.get_theme()
        self.setStyleSheet(generate_stylesheet(theme, self.scale_manager, screen_size.width(), screen_size.height()))

        layout = QVBoxLayout(self)
        layout.setSpacing(self.scale_manager.get_scaled_margin(screen_size.width(), screen_size.height()))

        layout.setContentsMargins(
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2
        )

        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit(song_name)
        self.search_input.setPlaceholderText("输入歌曲名称")
        self.search_button = QPushButton("搜索")
        self.search_button.setProperty("class", "primary")
        self.search_button.clicked.connect(self.search_lyrics)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(['歌名', "歌手", "时长", "ID"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.itemDoubleClicked.connect(self.on_item_double_click)
        layout.addWidget(self.result_table)

        # 状态标签
        self.status_label = QLabel("输入关键词...")
        layout.addWidget(self.status_label)

        # 绑定按钮
        button_layout = QHBoxLayout()
        self.bind_button = QPushButton("下载并绑定")
        self.bind_button.setProperty("class", "primary")
        self.bind_button.clicked.connect(self.confirm_bind)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setProperty("class", "outline")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.bind_button)
        layout.addLayout(button_layout)

    def search_lyrics(self):
        keyword = self.search_input.text()
        self.result_table.setRowCount(0)
        self.status_label.setText("搜索中...")

        self.worker = LyricListSearchWorker(keyword)
        self.worker.search_finished.connect(self.on_search_finished)
        self.worker.start()

    def on_search_finished(self, results):
        self.status_label.setText(f"找到 {len(results)} 条")
        self.result_table.setRowCount(len(results))

        for i, result in enumerate(results):
            self.result_table.setItem(i, 0, QTableWidgetItem(result['name']))
            self.result_table.setItem(i, 1, QTableWidgetItem(result['artist']))

            duration_item = QTableWidgetItem(result['duration_str'])
            if abs(result['duration'] - self.duration_ms) < 3000 and self.duration_ms > 0:
                duration_item.setForeground(QColor("#1ECD97"))
            self.result_table.setItem(i, 2, duration_item)
            self.result_table.setItem(i, 3, QTableWidgetItem(str(result['id'])))

    def on_item_double_click(self, item):
        self.result_id = self.result_table.item(item.row(), 3).text()
        self.accept()

    def confirm_bind(self):
        row = self.result_table.currentRow()
        if row >= 0:
            self.result_id = self.result_table.item(row, 3).text()
            self.accept()
        else:
            QMessageBox.warning(self, "提示", "请选择一首歌曲")

class BatchInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑信息")

        # 获取屏幕尺寸和缩放管理器
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        self.scale_manager = parent.scale_manager if hasattr(parent, 'scale_manager') else UIScaleManager()
        self.theme_manager = parent.theme_manager if hasattr(parent, 'theme_manager') else ThemeManager()

        # 设置对话框尺寸
        dialog_width = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 500)
        dialog_height = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 400)
        self.resize(dialog_width, dialog_height)

        theme = self.theme_manager.get_theme()
        self.setStyleSheet(generate_stylesheet(theme, self.scale_manager, screen_size.width(), screen_size.height()))

        layout = QVBoxLayout(self)
        layout.setSpacing(self.scale_manager.get_scaled_margin(screen_size.width(), screen_size.height()))

        layout.setContentsMargins(
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2
        )

        # 歌曲标题
        title_group = QGroupBox("歌曲信息")
        title_layout = QVBoxLayout(title_group)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("歌曲标题")
        title_layout.addWidget(self.title_input)

        # 歌手
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("歌手")
        title_layout.addWidget(self.artist_input)

        # 专辑
        self.album_input = QLineEdit()
        self.album_input.setPlaceholderText("专辑")
        title_layout.addWidget(self.album_input)

        # 年份
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("年份")
        title_layout.addWidget(self.year_input)

        layout.addWidget(title_group)

        # 按钮
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setProperty("class", "outline")
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("保存更改")
        self.save_button.setProperty("class", "primary")
        self.save_button.clicked.connect(self.accept)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

    def get_data(self):
        return (
            self.title_input.text(),
            self.artist_input.text(),
            self.album_input.text(),
            self.year_input.text()
        )
        
    def set_data(self, title, artist, album, year):
        self.title_input.setText(title)
        self.artist_input.setText(artist)
        self.album_input.setText(album)
        self.year_input.setText(year)





class DownloadDialog(QDialog):
    def __init__(self, parent=None, current_p=1, collections=[]):
        super().__init__(parent)
        self.setWindowTitle("下载")

        # 获取屏幕尺寸和缩放管理器
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        self.scale_manager = parent.scale_manager if hasattr(parent, 'scale_manager') else UIScaleManager()
        self.theme_manager = parent.theme_manager if hasattr(parent, 'theme_manager') else ThemeManager()

        # 设置对话框尺寸
        dialog_width = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 600)
        dialog_height = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 500)
        self.resize(dialog_width, dialog_height)

        theme = self.theme_manager.get_theme()
        self.setStyleSheet(generate_stylesheet(theme, self.scale_manager, screen_size.width(), screen_size.height()))

        layout = QVBoxLayout(self)
        layout.setSpacing(self.scale_manager.get_scaled_margin(screen_size.width(), screen_size.height()))

        layout.setContentsMargins(
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2
        )

        # 视频链接
        url_group = QGroupBox("视频链接")
        url_layout = QVBoxLayout(url_group)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入 B 站视频链接")
        url_layout.addWidget(self.url_input)
        layout.addWidget(url_group)

        # 标签页
        self.tab_widget = QTabWidget()

        # 下载设置标签页
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setSpacing(self.scale_manager.get_scaled_margin(screen_size.width(), screen_size.height()))

        # 下载模式
        mode_group = QGroupBox("下载模式")
        mode_layout = QVBoxLayout(mode_group)
        self.single_radio = QRadioButton("单曲下载")
        self.playlist_radio = QRadioButton("合集下载")
        self.single_radio.setChecked(True)
        mode_layout.addWidget(self.single_radio)
        mode_layout.addWidget(self.playlist_radio)
        settings_layout.addWidget(mode_group)

        # 保存位置
        location_group = QGroupBox("保存位置")
        location_layout = QVBoxLayout(location_group)
        self.folder_combo = QComboBox()
        self.folder_combo.addItem("根目录", "")
        for collection in collections:
            self.folder_combo.addItem(f"{ICONS['folder_open']} {collection}", collection)
        self.folder_combo.addItem(f"{ICONS['folder_plus']} 新建...", "NEW")
        location_layout.addWidget(self.folder_combo)

        self.new_folder_input = QLineEdit()
        self.new_folder_input.setPlaceholderText("文件夹名称")
        self.new_folder_input.hide()
        location_layout.addWidget(self.new_folder_input)

        self.folder_combo.currentIndexChanged.connect(self.on_folder_combo_changed)
        settings_layout.addWidget(location_group)

        # 预设信息
        preset_group = QGroupBox("预设信息")
        preset_layout = QVBoxLayout(preset_group)
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("预设歌手")
        preset_layout.addWidget(self.artist_input)

        self.album_input = QLineEdit()
        self.album_input.setPlaceholderText("预设专辑")
        preset_layout.addWidget(self.album_input)
        settings_layout.addWidget(preset_group)

        self.tab_widget.addTab(settings_tab, "下载设置")

        # 高级选项标签页
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.addWidget(QLabel("高级选项内容..."))
        self.tab_widget.addTab(advanced_tab, "高级选项")

        layout.addWidget(self.tab_widget)

        # 按钮
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setProperty("class", "outline")
        self.cancel_button.clicked.connect(self.reject)
        self.download_button = QPushButton(f"{ICONS['download']} 开始下载")
        self.download_button.setProperty("class", "primary")
        self.download_button.clicked.connect(self.accept)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.download_button)
        layout.addLayout(button_layout)

    def on_folder_combo_changed(self):
        self.new_folder_input.setVisible(self.folder_combo.currentData() == "NEW")

    def get_data(self):
        mode = "playlist" if self.playlist_radio.isChecked() else "single"
        folder = self.folder_combo.currentData()

        if folder == "NEW":
            folder = self.new_folder_input.text().strip()

        return self.url_input.text(), mode, folder, self.artist_input.text(), self.album_input.text()

class SyncLyricsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("歌词同步")

        # 获取屏幕尺寸和缩放管理器
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        self.scale_manager = parent.scale_manager if hasattr(parent, 'scale_manager') else UIScaleManager()
        self.theme_manager = parent.theme_manager if hasattr(parent, 'theme_manager') else ThemeManager()

        # 设置对话框尺寸
        dialog_width = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 500)
        dialog_height = self.scale_manager.get_scaled_size(screen_size.width(), screen_size.height(), 400)
        self.resize(dialog_width, dialog_height)

        theme = self.theme_manager.get_theme()
        self.setStyleSheet(generate_stylesheet(theme, self.scale_manager, screen_size.width(), screen_size.height()))

        layout = QVBoxLayout(self)
        layout.setSpacing(self.scale_manager.get_scaled_margin(screen_size.width(), screen_size.height()))

        layout.setContentsMargins(
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2,
            self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height()) * 2
        )

        # 当前播放时间
        time_group = QGroupBox("当前播放时间")
        time_layout = QHBoxLayout(time_group)
        self.time_input = QLineEdit("00:29")
        self.play_button = QPushButton(f"{ICONS['play']} 播放")
        self.play_button.setProperty("class", "outline")
        time_layout.addWidget(self.time_input)
        time_layout.addWidget(self.play_button)
        layout.addWidget(time_group)

        # 选择歌词行
        lyric_group = QGroupBox("选择歌词行")
        lyric_layout = QVBoxLayout(lyric_group)
        self.lyric_combo = QComboBox()
        self.lyric_combo.addItems([
            "窗外的麻雀 在电线杆上多嘴",
            "你说这一句 很有夏天的感觉",
            "手中的铅笔 在纸上来来回回",
            "我用几行字形容你是我的谁",
            "秋刀鱼的滋味 猫跟你都想了解"
        ])
        lyric_layout.addWidget(self.lyric_combo)
        layout.addWidget(lyric_group)

        # 时间偏移
        offset_group = QGroupBox("时间偏移")
        offset_layout = QVBoxLayout(offset_group)
        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setRange(-10, 10)
        self.offset_slider.setValue(0)
        self.offset_label = QLabel("当前偏移: 0 秒")
        offset_layout.addWidget(self.offset_slider)
        offset_layout.addWidget(self.offset_label)
        layout.addWidget(offset_group)

        self.offset_slider.valueChanged.connect(self.on_offset_changed)

        # 按钮
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setProperty("class", "outline")
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button = QPushButton(f"{ICONS['check']} 应用同步")
        self.apply_button.setProperty("class", "primary")
        self.apply_button.clicked.connect(self.accept)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
        layout.addLayout(button_layout)

    def on_offset_changed(self, value):
        self.offset_label.setText(f"当前偏移: {value}秒")

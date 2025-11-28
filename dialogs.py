from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
                           QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                           QLabel, QMessageBox, QGroupBox, QRadioButton, QComboBox,
                           QTabWidget, QWidget, QSlider, QApplication, QColorDialog,
                           QFontDialog, QInputDialog, QFileDialog, QCheckBox, QSpinBox,
                           QProgressBar, QGridLayout)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QColor, QFont, QDesktopServices

from ui_scale_manager import UIScaleManager
from theme_manager import ThemeManager
from style_generator import generate_stylesheet
from utils import ICONS, LyricListSearchWorker, LyricDownloader
from bilibili_downloader import BilibiliDownloader

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


class BilibiliDownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("B站音频下载")
        
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

        # 主布局
        main_layout = QVBoxLayout(self)
        padding = self.scale_manager.get_scaled_padding(screen_size.width(), screen_size.height())
        main_layout.setContentsMargins(padding*2, padding*2, padding*2, padding*2)
        main_layout.setSpacing(padding)

        # URL输入
        url_layout = QHBoxLayout()
        url_label = QLabel("视频链接:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入B站视频或 playlist 链接")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        main_layout.addLayout(url_layout)

        # 下载设置
        settings_group = QGroupBox("下载设置")
        settings_layout = QGridLayout(settings_group)
        
        # 下载模式选择
        mode_label = QLabel("下载模式:")
        self.single_radio = QRadioButton("单个视频")
        self.playlist_radio = QRadioButton("播放列表")
        self.single_radio.setChecked(True)
        
        # 范围选择
        range_label = QLabel("范围:")
        self.start_spin = QSpinBox()
        self.start_spin.setMinimum(1)
        self.start_spin.setValue(1)
        self.end_spin = QSpinBox()
        self.end_spin.setMinimum(1)
        self.end_spin.setValue(1)
        range_label2 = QLabel("-")
        
        # 路径选择
        path_label = QLabel("保存路径:")
        self.path_input = QLineEdit()
        self.path_input.setText(os.path.expanduser("~/Music"))
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_path)
        
        # 格式选择
        format_label = QLabel("格式:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["仅音频 (MP3)", "视频 (MP4)"])
        self.format_combo.setCurrentIndex(0)

        # 添加到布局
        settings_layout.addWidget(mode_label, 0, 0)
        settings_layout.addWidget(self.single_radio, 0, 1)
        settings_layout.addWidget(self.playlist_radio, 0, 2)
        
        settings_layout.addWidget(range_label, 1, 0)
        settings_layout.addWidget(self.start_spin, 1, 1)
        settings_layout.addWidget(range_label2, 1, 2)
        settings_layout.addWidget(self.end_spin, 1, 3)
        
        settings_layout.addWidget(path_label, 2, 0)
        settings_layout.addWidget(self.path_input, 2, 1, 1, 3)
        settings_layout.addWidget(self.browse_btn, 2, 4)
        
        settings_layout.addWidget(format_label, 3, 0)
        settings_layout.addWidget(self.format_combo, 3, 1)
        
        main_layout.addWidget(settings_group)

        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("等待开始...")
        main_layout.addWidget(self.status_label)

        # 按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始下载")
        self.start_btn.setObjectName("DownloadBtn")
        self.start_btn.clicked.connect(self.start_download)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_download)
        
        self.open_folder_btn = QPushButton("打开文件夹")
        self.open_folder_btn.clicked.connect(self.open_download_folder)
        self.open_folder_btn.setEnabled(False)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addWidget(self.start_btn)
        main_layout.addLayout(btn_layout)

        # 下载线程
        self.downloader = None

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.path_input.text())
        if path:
            self.path_input.setText(path)

    def start_download(self):
        url = self.url_input.text().strip()
        path = self.path_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "错误", "请输入视频链接")
            return
            
        if not path:
            QMessageBox.warning(self, "错误", "请选择保存路径")
            return

        # 获取下载模式
        mode = 'single' if self.single_radio.isChecked() else 'playlist'
        start = self.start_spin.value()
        end = self.end_spin.value() if mode == 'playlist' else None
        
        # 禁用控件
        self.start_btn.setEnabled(False)
        self.url_input.setEnabled(False)
        self.path_input.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.single_radio.setEnabled(False)
        self.playlist_radio.setEnabled(False)
        self.start_spin.setEnabled(False)
        self.end_spin.setEnabled(False)

        # 开始下载
        self.downloader = BilibiliDownloader(
            url=url,
            path=path,
            mode=mode,
            start=start,
            end=end
        )
        
        self.downloader.progress_signal.connect(self.update_progress)
        self.downloader.finished_signal.connect(self.download_finished)
        self.downloader.error_signal.connect(self.download_error)
        self.downloader.start()

    def update_progress(self, text, percent):
        self.status_label.setText(text)
        self.progress_bar.setValue(percent)

    def download_finished(self, path, filename):
        self.status_label.setText("下载完成!")
        self.progress_bar.setValue(100)
        self.open_folder_btn.setEnabled(True)
        self._restore_ui()
        QMessageBox.information(self, "完成", f"文件已保存到:\n{path}")

    def download_error(self, error_msg):
        self.status_label.setText(f"错误: {error_msg}")
        self._restore_ui()
        QMessageBox.critical(self, "下载失败", error_msg)

    def cancel_download(self):
        if self.downloader and self.downloader.isRunning():
            self.downloader.cancel_download()
            self.status_label.setText("正在取消...")
            self.start_btn.setEnabled(False)
        else:
            self.close()

    def open_download_folder(self):
        path = self.path_input.text()
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _restore_ui(self):
        self.start_btn.setEnabled(True)
        self.url_input.setEnabled(True)
        self.path_input.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.single_radio.setEnabled(True)
        self.playlist_radio.setEnabled(True)
        self.start_spin.setEnabled(True)
        self.end_spin.setEnabled(True)

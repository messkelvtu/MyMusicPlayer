import sys
import os
import json
import shutil
import random
import threading
import re
import urllib.request
import urllib.parse
import time
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QFileDialog, QFrame, QAbstractItemView, QCheckBox,
                             QGraphicsDropShadowEffect, QInputDialog, QMessageBox, 
                             QFontDialog, QMenu, QAction, QSlider, QDialog, QRadioButton, 
                             QComboBox, QLineEdit, QTabWidget, QSpinBox, QColorDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize, QCoreApplication, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPalette, QLinearGradient, QPainter
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# --- 核心配置 ---
os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

CONFIG_FILE = "config.json"
METADATA_FILE = "metadata.json"
HISTORY_FILE = "history.json"
OFFSET_FILE = "offsets.json"

# --- 清新简洁的样式表 ---
STYLESHEET = """
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                               stop:0 #f8f9fa, stop:1 #e9ecef);
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}

/* 侧边栏 */
QFrame#Sidebar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #ffffff, stop:1 #f8f9fa);
    border-right: 1px solid #dee2e6;
}

QLabel#Logo {
    font-size: 20px;
    font-weight: bold;
    color: #20c997;
    padding: 20px 15px;
    background: transparent;
}

QLabel#SectionTitle {
    font-size: 11px;
    color: #6c757d;
    padding: 8px 15px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

QPushButton.NavBtn {
    background: transparent;
    border: none;
    text-align: left;
    padding: 12px 15px;
    font-size: 14px;
    color: #495057;
    border-radius: 8px;
    margin: 2px 8px;
    transition: all 0.2s;
}

QPushButton.NavBtn:hover {
    background: #e9ecef;
    color: #20c997;
    transform: translateX(2px);
}

QPushButton.NavBtn:checked {
    background: #20c997;
    color: white;
    font-weight: 600;
}

QPushButton#DownloadBtn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    font-weight: 600;
    border-radius: 8px;
    margin: 8px;
    padding: 12px;
}

QPushButton#DownloadBtn:hover {
    background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    transform: translateY(-1px);
}

/* 表格样式 */
QTableWidget {
    background: white;
    border: none;
    outline: none;
    border-radius: 8px;
    margin: 8px;
    selection-background-color: #e3f2fd;
    selection-color: #1976d2;
    gridline-color: #f1f3f4;
}

QHeaderView::section {
    background: #f8f9fa;
    border: none;
    border-bottom: 2px solid #e9ecef;
    padding: 12px 8px;
    font-weight: 600;
    color: #495057;
    font-size: 12px;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #f8f9fa;
}

QTableWidget::item:selected {
    background: #e3f2fd;
    color: #1976d2;
}

/* 歌词面板 */
QListWidget#LyricPanel {
    background: transparent;
    border: none;
    outline: none;
    font-size: 14px;
    color: #6c757d;
}

QListWidget#LyricPanel::item {
    padding: 8px 12px;
    border: none;
    background: transparent;
    text-align: center;
}

QListWidget#LyricPanel::item:selected {
    background: transparent;
    color: #20c997;
    font-weight: 600;
    font-size: 16px;
}

/* 播放条 */
QFrame#PlayerBar {
    background: rgba(255, 255, 255, 0.95);
    border-top: 1px solid #dee2e6;
    backdrop-filter: blur(10px);
}

QPushButton#PlayBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                               stop:0 #20c997, stop:1 #198754);
    color: white;
    border-radius: 25px;
    font-size: 16px;
    min-width: 50px;
    min-height: 50px;
    border: none;
}

QPushButton#PlayBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                               stop:0 #198754, stop:1 #20c997);
    transform: scale(1.05);
}

QPushButton.CtrlBtn {
    background: transparent;
    border: none;
    font-size: 16px;
    color: #6c757d;
    border-radius: 6px;
    padding: 6px;
}

QPushButton.CtrlBtn:hover {
    color: #20c997;
    background: #f8f9fa;
}

QPushButton.OffsetBtn {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    color: #6c757d;
    font-size: 10px;
    padding: 4px 8px;
}

QPushButton.OffsetBtn:hover {
    background: #20c997;
    border-color: #20c997;
    color: white;
}

QSlider::groove:horizontal {
    border: 1px solid #dee2e6;
    height: 6px;
    background: #e9ecef;
    margin: 2px 0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #20c997;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
    border: 2px solid white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #20c997, stop:1 #198754);
    border-radius: 3px;
}

/* 进度条 */
QProgressBar {
    border: none;
    background: #e9ecef;
    border-radius: 4px;
    text-align: center;
    color: white;
    font-size: 10px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                               stop:0 #20c997, stop:1 #198754);
    border-radius: 4px;
}
"""

def sanitize_filename(name):
    """清理文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def ms_to_str(ms):
    """毫秒转换为时间字符串"""
    s = ms // 1000
    return f"{s//60:02}:{s%60:02}"

# --- 1. 在线歌词搜索线程 ---
class LyricListSearchWorker(QThread):
    search_finished = pyqtSignal(list)

    def __init__(self, keyword):
        super().__init__()
        self.keyword = keyword

    def run(self):
        try:
            url = "http://music.163.com/api/search/get/web?csrf_token="
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            data = urllib.parse.urlencode({'s': self.keyword, 'type': 1, 'offset': 0, 'total': 'true', 'limit': 20}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as f:
                res = json.loads(f.read().decode('utf-8'))
            
            results = []
            if res.get('result') and res['result'].get('songs'):
                for s in res['result']['songs']:
                    artists = [art['name'] for art in s.get('artists', [])]
                    artist = ' / '.join(artists) if artists else "未知"
                    album = s.get('album', {}).get('name', '未知专辑')
                    duration = s.get('duration', 0)
                    results.append({
                        'name': s['name'],
                        'artist': artist,
                        'album': album,
                        'id': s['id'],
                        'duration': duration,
                        'duration_str': ms_to_str(duration)
                    })
            self.search_finished.emit(results)
        except Exception as e:
            print(f"搜索错误: {e}")
            self.search_finished.emit([])

# --- 2. 手动歌词搜索弹窗 ---
class LyricSearchDialog(QDialog):
    def __init__(self, song_name, artist="", duration_ms=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("在线歌词搜索")
        self.resize(800, 500)
        self.setStyleSheet("""
            QDialog { background: white; }
            QLineEdit { padding: 8px; border: 1px solid #dee2e6; border-radius: 4px; }
            QPushButton { padding: 8px 16px; border-radius: 4px; }
            QTableWidget { border: 1px solid #dee2e6; }
        """)
        
        self.result_id = None
        self.duration_ms = duration_ms 
        
        layout = QVBoxLayout(self)
        
        # 搜索框区域
        search_layout = QHBoxLayout()
        self.input_song = QLineEdit(song_name)
        self.input_song.setPlaceholderText("歌曲名")
        self.input_artist = QLineEdit(artist)
        self.input_artist.setPlaceholderText("歌手名（可选）")
        btn_search = QPushButton("🔍 搜索")
        btn_search.setStyleSheet("background: #20c997; color: white; font-weight: bold;")
        btn_search.clicked.connect(self.start_search)
        
        search_layout.addWidget(QLabel("歌曲:"))
        search_layout.addWidget(self.input_song)
        search_layout.addWidget(QLabel("歌手:"))
        search_layout.addWidget(self.input_artist)
        search_layout.addWidget(btn_search)
        layout.addLayout(search_layout)
        
        # 结果表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["歌名", "歌手", "专辑", "时长", "匹配度"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemDoubleClicked.connect(self.on_select)
        layout.addWidget(self.table)
        
        # 状态信息
        if duration_ms > 0:
            info_label = QLabel(f"当前歌曲时长: {ms_to_str(duration_ms)} - 选择时长相近的结果匹配更准确")
            info_label.setStyleSheet("color: #6c757d; font-size: 12px; padding: 5px;")
            layout.addWidget(info_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_bind = QPushButton("💾 绑定选中歌词")
        btn_bind.setStyleSheet("background: #20c997; color: white; font-weight: bold; padding: 10px;")
        btn_bind.clicked.connect(self.confirm_bind)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_bind)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def start_search(self):
        song = self.input_song.text().strip()
        artist = self.input_artist.text().strip()
        
        if not song:
            QMessageBox.warning(self, "提示", "请输入歌曲名")
            return
            
        keyword = f"{song} {artist}" if artist else song
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        # 显示搜索中状态
        loading_item = QTableWidgetItem("搜索中...")
        self.table.setRowCount(1)
        self.table.setItem(0, 0, loading_item)
        
        self.worker = LyricListSearchWorker(keyword)
        self.worker.search_finished.connect(self.on_search_done)
        self.worker.start()

    def on_search_done(self, results):
        self.table.setRowCount(len(results))
        
        for i, item in enumerate(results):
            self.table.setItem(i, 0, QTableWidgetItem(item['name']))
            self.table.setItem(i, 1, QTableWidgetItem(item['artist']))
            self.table.setItem(i, 2, QTableWidgetItem(item['album']))
            self.table.setItem(i, 3, QTableWidgetItem(item['duration_str']))
            
            # 计算匹配度
            match_score = self.calculate_match_score(item)
            match_item = QTableWidgetItem(f"{match_score}%")
            
            # 根据匹配度设置颜色
            if match_score >= 80:
                match_item.setForeground(QColor("#198754"))
            elif match_score >= 60:
                match_item.setForeground(QColor("#fd7e14"))
            else:
                match_item.setForeground(QColor("#6c757d"))
                
            self.table.setItem(i, 4, match_item)
            
            # 存储ID到隐藏列
            self.table.setItem(i, 0, QTableWidgetItem(item['name']))
            self.table.item(i, 0).setData(Qt.UserRole, item['id'])

    def calculate_match_score(self, item):
        """计算搜索结果的匹配度"""
        score = 0
        
        # 时长匹配 (40%)
        if self.duration_ms > 0:
            duration_diff = abs(item['duration'] - self.duration_ms)
            if duration_diff < 2000:  # 2秒内
                score += 40
            elif duration_diff < 5000:  # 5秒内
                score += 20
            elif duration_diff < 10000:  # 10秒内
                score += 10
        
        # 歌名匹配 (40%)
        target_song = self.input_song.text().lower()
        result_song = item['name'].lower()
        if target_song in result_song or result_song in target_song:
            score += 40
        elif any(word in result_song for word in target_song.split()):
            score += 25
        
        # 歌手匹配 (20%)
        target_artist = self.input_artist.text().lower()
        if target_artist:
            result_artist = item['artist'].lower()
            if target_artist in result_artist:
                score += 20
            elif any(word in result_artist for word in target_artist.split()):
                score += 10
        
        return min(score, 100)

    def on_select(self, item):
        self.confirm_bind()

    def confirm_bind(self):
        row = self.table.currentRow()
        if row >= 0:
            self.result_id = self.table.item(row, 0).data(Qt.UserRole)
            if self.result_id:
                self.accept()
            else:
                QMessageBox.warning(self, "错误", "未找到有效的歌曲ID")
        else:
            QMessageBox.warning(self, "提示", "请先选择一首歌曲")

# --- 歌词下载线程 ---
class LyricDownloader(QThread):
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, song_id, save_path):
        super().__init__()
        self.sid = song_id
        self.path = save_path
        
    def run(self):
        try:
            url = f"http://music.163.com/api/song/lyric?os=pc&id={self.sid}&lv=-1&kv=-1&tv=-1"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as f:
                res = json.loads(f.read().decode('utf-8'))
            
            lyric_text = ""
            if 'lrc' in res and 'lyric' in res['lrc']:
                lyric_text = res['lrc']['lyric']
            
            # 如果有逐字歌词，也一并获取
            if 'klyric' in res and 'lyric' in res['klyric']:
                klyric = res['klyric']['lyric']
                if klyric and klyric != lyric_text:
                    lyric_text += f"\n\n[klyric]\n{klyric}"
            
            if lyric_text:
                with open(self.path, 'w', encoding='utf-8') as f:
                    f.write(lyric_text)
                self.finished_signal.emit(lyric_text)
            else:
                self.error_signal.emit("未找到歌词")
                
        except Exception as e:
            self.error_signal.emit(f"下载失败: {str(e)}")

# --- 3. 批量移动对话框 ---
class BatchMoveDialog(QDialog):
    def __init__(self, collections, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量移动歌曲")
        self.resize(400, 200)
        self.setStyleSheet("""
            QDialog { background: white; }
            QPushButton { padding: 8px 16px; border-radius: 4px; }
        """)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("选择目标合集:"))
        
        self.collection_combo = QComboBox()
        self.collection_combo.addItem("💿 根目录", "")
        for collection in collections:
            self.collection_combo.addItem(f"📁 {collection}", collection)
        
        # 添加新建合集选项
        self.collection_combo.addItem("➕ 新建合集...", "NEW")
        self.collection_combo.currentIndexChanged.connect(self.on_combo_change)
        
        layout.addWidget(self.collection_combo)
        
        self.new_collection_input = QLineEdit()
        self.new_collection_input.setPlaceholderText("输入新合集名称")
        self.new_collection_input.hide()
        layout.addWidget(self.new_collection_input)
        
        # 操作选项
        self.move_files_check = QCheckBox("移动文件到目标文件夹")
        self.move_files_check.setChecked(True)
        layout.addWidget(self.move_files_check)
        
        self.update_metadata_check = QCheckBox("更新歌曲信息中的专辑字段")
        self.update_metadata_check.setChecked(True)
        layout.addWidget(self.update_metadata_check)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("🚚 开始移动")
        btn_ok.setStyleSheet("background: #20c997; color: white; font-weight: bold;")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def on_combo_change(self):
        if self.collection_combo.currentData() == "NEW":
            self.new_collection_input.show()
            self.new_collection_input.setFocus()
        else:
            self.new_collection_input.hide()

    def get_data(self):
        target = self.collection_combo.currentData()
        if target == "NEW":
            target = self.new_collection_input.text().strip()
        return {
            'target': target,
            'move_files': self.move_files_check.isChecked(),
            'update_metadata': self.update_metadata_check.isChecked()
        }

# --- 4. 桌面歌词窗口（保持原有样式）---
class DesktopLyricWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1200, 180)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        self.font_color = QColor(255, 255, 255)
        self.current_font = QFont("Microsoft YaHei", 36, QFont.Bold)
        
        self.labels = []
        for i in range(3):
            lbl = QLabel("")
            lbl.setAlignment(Qt.AlignCenter)
            self.labels.append(lbl)
            self.layout.addWidget(lbl)
        
        self.update_styles()
        self.locked = False

    def update_styles(self):
        base_size = self.current_font.pointSize()
        shadow_color = QColor(0, 0, 0, 200)
        for i, lbl in enumerate(self.labels):
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(8)
            effect.setColor(shadow_color)
            effect.setOffset(1, 1)
            lbl.setGraphicsEffect(effect)
            f = QFont(self.current_font)
            color_css = self.font_color.name()
            if i == 1:
                f.setPointSize(base_size)
                lbl.setStyleSheet(f"color: {color_css};")
            else:
                f.setPointSize(int(base_size * 0.6))
                r,g,b = self.font_color.red(), self.font_color.green(), self.font_color.blue()
                lbl.setStyleSheet(f"color: rgba({r}, {g}, {b}, 160);")
            lbl.setFont(f)

    def set_lyrics(self, p, c, n):
        self.labels[0].setText(p)
        self.labels[1].setText(c)
        self.labels[2].setText(n)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.locked:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self.show_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.locked:
            self.move(event.globalPos() - self.drag_pos)

    def wheelEvent(self, event):
        d = event.angleDelta().y()
        s = self.current_font.pointSize()
        self.current_font.setPointSize(min(120, s+2) if d>0 else max(15, s-2))
        self.update_styles()

    def show_menu(self, pos):
        menu = QMenu()
        act_color = menu.addAction("🎨 修改颜色")
        act_font = menu.addAction("🅰️ 修改字体")
        lock_text = "🔒 解锁位置" if self.locked else "🔒 锁定位置"
        act_lock = menu.addAction(lock_text)
        act_close = menu.addAction("❌ 隐藏歌词")
        action = menu.exec_(pos)
        if action == act_color:
            c = QColorDialog.getColor(self.font_color, self)
            if c.isValid():
                self.font_color = c
                self.update_styles()
        elif action == act_font:
            f, ok = QFontDialog.getFont(self.current_font, self)
            if ok:
                self.current_font = f
                self.update_styles()
        elif action == act_lock:
            self.locked = not self.locked
        elif action == act_close:
            self.hide()

# --- 5. 下载选项弹窗 ---
class DownloadDialog(QDialog):
    def __init__(self, parent=None, current_p=1, collections=[]):
        super().__init__(parent)
        self.setWindowTitle("B站音频下载")
        self.resize(450, 400)
        self.setStyleSheet("""
            QDialog { background: white; }
            QLineEdit, QComboBox { padding: 8px; border: 1px solid #dee2e6; border-radius: 4px; }
            QPushButton { padding: 8px 16px; border-radius: 4px; }
        """)
        
        layout = QVBoxLayout(self)
        
        # 下载模式
        mode_group = QWidget()
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.addWidget(QLabel("📺 下载模式:"))
        
        self.rb_single = QRadioButton(f"单视频 (P{current_p})")
        self.rb_playlist = QRadioButton(f"合集视频 (P{current_p} 及后续所有分P)")
        self.rb_single.setChecked(True)
        
        mode_layout.addWidget(self.rb_single)
        mode_layout.addWidget(self.rb_playlist)
        layout.addWidget(mode_group)
        
        # 存储位置
        layout.addWidget(QLabel("💾 存储位置:"))
        self.combo_coll = QComboBox()
        self.combo_coll.addItem("📂 根目录", "")
        for c in collections:
            self.combo_coll.addItem(f"📁 {c}", c)
        self.combo_coll.addItem("➕ 新建合集...", "NEW")
        layout.addWidget(self.combo_coll)
        
        self.input_new = QLineEdit()
        self.input_new.setPlaceholderText("输入新合集名称")
        self.input_new.hide()
        layout.addWidget(self.input_new)
        self.combo_coll.currentIndexChanged.connect(self.on_combo_change)

        # 元数据
        meta_group = QWidget()
        meta_layout = QVBoxLayout(meta_group)
        meta_layout.addWidget(QLabel("📝 歌曲信息 (可选):"))
        
        self.input_artist = QLineEdit()
        self.input_artist.setPlaceholderText("歌手/UP主")
        self.input_album = QLineEdit()
        self.input_album.setPlaceholderText("专辑/系列")
        
        meta_layout.addWidget(self.input_artist)
        meta_layout.addWidget(self.input_album)
        layout.addWidget(meta_group)
        
        # 下载选项
        self.auto_lyric = QCheckBox("自动搜索歌词")
        self.auto_lyric.setChecked(True)
        layout.addWidget(self.auto_lyric)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("🚀 开始下载")
        btn_ok.setStyleSheet("background: linear-gradient(135deg, #667eea, #764ba2); color: white; font-weight: bold; padding: 10px;")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def on_combo_change(self):
        if self.combo_coll.currentData() == "NEW":
            self.input_new.show()
            self.input_new.setFocus()
        else:
            self.input_new.hide()

    def get_data(self):
        mode = "playlist" if self.rb_playlist.isChecked() else "single"
        folder = self.combo_coll.currentData()
        if folder == "NEW":
            folder = self.input_new.text().strip()
        return {
            'mode': mode,
            'folder': folder,
            'artist': self.input_artist.text(),
            'album': self.input_album.text(),
            'auto_lyric': self.auto_lyric.isChecked()
        }

# --- B站下载线程 ---
class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str, list)  # 修改为传递文件列表
    error_signal = pyqtSignal(str)

    def __init__(self, url, save_path, mode="single", start_p=1, metadata=None):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.mode = mode
        self.start_p = start_p
        self.metadata = metadata or {}

    def run(self):
        if not yt_dlp:
            self.error_signal.emit("错误：缺少 yt-dlp 库")
            return
            
        if not os.path.exists(self.save_path):
            try:
                os.makedirs(self.save_path)
            except Exception as e:
                self.error_signal.emit(f"无法创建文件夹: {e}")
                return

        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%').strip()
                fn = os.path.basename(d.get('filename', '未知'))
                if len(fn) > 20:
                    fn = fn[:20] + "..."
                self.progress_signal.emit(f"⬇️ {p} : {fn}")
            elif d['status'] == 'finished':
                self.progress_signal.emit("✅ 下载完成，处理中...")

        items_range = str(self.start_p) if self.mode == 'single' else f"{self.start_p}:"
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best[height<=720]',
            'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
            'overwrites': True,
            'noplaylist': self.mode == 'single',
            'playlist_items': items_range,
            'ignoreerrors': True,
            'progress_hooks': [progress_hook],
            'quiet': False,
            'nocheckcertificate': True,
            'restrictfilenames': False,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }],
        }
        
        try:
            self.progress_signal.emit("🔍 开始解析视频信息...")
            downloaded_files = []
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息
                info = ydl.extract_info(self.url, download=False)
                
                if self.mode == 'playlist' and 'entries' in info:
                    total = len(info['entries'])
                    self.progress_signal.emit(f"📺 发现 {total} 个视频，开始下载...")
                
                # 开始下载
                ydl.download([self.url])
                
                # 获取下载的文件列表
                for f in os.listdir(self.save_path):
                    if f.endswith(('.m4a', '.mp3', '.mp4')):
                        downloaded_files.append(f)
                        
            self.progress_signal.emit("🎉 所有任务完成")
            self.finished_signal.emit(self.save_path, downloaded_files)
            
        except Exception as e:
            self.error_signal.emit(f"下载失败: {str(e)}")

# --- 主程序 ---
class SodaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽水音乐 - 简洁清新的音乐播放器")
        self.resize(1200, 800)
        self.setStyleSheet(STYLESHEET)

        # 初始化变量
        self.music_folder = ""
        self.current_collection = "" 
        self.collections = [] 
        self.playlist = [] 
        self.history = []
        self.lyrics = []
        self.current_index = -1
        self.offset = 0.0
        
        self.saved_offsets = {}
        self.metadata = {} 

        self.mode = 0  # 0:顺序 1:单曲循环 2:随机
        self.rate = 1.0 
        self.is_slider_pressed = False 

        # 初始化播放器
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.stateChanged.connect(self.on_state_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.error.connect(self.handle_player_error)

        # 初始化桌面歌词
        self.desktop_lyric = DesktopLyricWindow()
        
        self.init_ui()
        self.load_config()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === 侧边栏 ===
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # logo区域
        logo = QLabel("🎵 汽水音乐")
        logo.setObjectName("Logo")
        sidebar_layout.addWidget(logo)
        
        # 下载按钮
        self.btn_bili = QPushButton("📥 B站音频下载")
        self.btn_bili.setObjectName("DownloadBtn")
        self.btn_bili.clicked.connect(self.download_from_bilibili)
        sidebar_layout.addWidget(self.btn_bili)
        
        # 刷新按钮
        btn_refresh = QPushButton("🔄 刷新音乐库")
        btn_refresh.setProperty("NavBtn", True)
        btn_refresh.clicked.connect(self.full_scan)
        sidebar_layout.addWidget(btn_refresh)
        
        # 音乐库导航
        sidebar_layout.addWidget(QLabel("音乐库", objectName="SectionTitle"))
        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 15px;
                border: none;
                background: transparent;
            }
            QListWidget::item:selected {
                background: #20c997;
                color: white;
                border-radius: 6px;
                margin: 2px 8px;
            }
        """)
        self.nav_list.itemClicked.connect(self.switch_collection)
        sidebar_layout.addWidget(self.nav_list)
        
        # 底部按钮组
        sidebar_layout.addStretch()
        btn_group = QWidget()
        btn_group_layout = QVBoxLayout(btn_group)
        btn_group_layout.setContentsMargins(8, 8, 8, 8)
        btn_group_layout.setSpacing(8)
        
        btn_move = QPushButton("📦 批量管理")
        btn_move.setProperty("NavBtn", True)
        btn_move.clicked.connect(self.open_batch_move_dialog)
        btn_group_layout.addWidget(btn_move)
        
        btn_folder = QPushButton("📁 设置根目录")
        btn_folder.setProperty("NavBtn", True)
        btn_folder.clicked.connect(self.select_folder)
        btn_group_layout.addWidget(btn_folder)
        
        btn_lyric = QPushButton("💬 桌面歌词")
        btn_lyric.setProperty("NavBtn", True)
        btn_lyric.clicked.connect(self.toggle_lyric)
        btn_group_layout.addWidget(btn_lyric)
        
        sidebar_layout.addWidget(btn_group)
        layout.addWidget(sidebar)

        # === 右侧主区域 ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # 标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(60)
        title_bar.setStyleSheet("background: rgba(255,255,255,0.8); border-bottom: 1px solid #dee2e6;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 20, 0)
        
        self.lbl_collection_title = QLabel("全部音乐")
        self.lbl_collection_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057;")
        title_layout.addWidget(self.lbl_collection_title)
        title_layout.addStretch()
        
        # 搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 搜索歌曲...")
        self.search_box.setFixedWidth(200)
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #dee2e6;
                border-radius: 20px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #20c997;
            }
        """)
        self.search_box.textChanged.connect(self.search_songs)
        title_layout.addWidget(self.search_box)
        
        right_layout.addWidget(title_bar)

        # 内容区域
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 歌曲列表
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["歌曲标题", "歌手", "专辑", "时长"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.itemDoubleClicked.connect(self.play_selected)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        content_layout.addWidget(self.table, stretch=6)
        
        # 歌词面板
        lyric_container = QWidget()
        lyric_container.setFixedWidth(300)
        lyric_container.setStyleSheet("background: rgba(255,255,255,0.5);")
        lyric_layout = QVBoxLayout(lyric_container)
        lyric_layout.setContentsMargins(0, 0, 0, 0)
        
        lyric_title = QLabel("🎤 歌词")
        lyric_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #495057; padding: 15px;")
        lyric_layout.addWidget(lyric_title)
        
        self.panel_lyric = QListWidget()
        self.panel_lyric.setObjectName("LyricPanel")
        self.panel_lyric.setFocusPolicy(Qt.NoFocus)
        self.panel_lyric.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lyric_layout.addWidget(self.panel_lyric)
        
        content_layout.addWidget(lyric_container)
        right_layout.addWidget(content, stretch=1)

        # === 播放控制栏 ===
        player_bar = QFrame()
        player_bar.setObjectName("PlayerBar")
        player_bar.setFixedHeight(100)
        player_layout = QVBoxLayout(player_bar)
        player_layout.setContentsMargins(20, 10, 20, 10)
        
        # 进度条
        progress_layout = QHBoxLayout()
        self.lbl_curr_time = QLabel("00:00")
        self.lbl_curr_time.setStyleSheet("color: #6c757d; font-size: 12px;")
        self.lbl_total_time = QLabel("00:00")
        self.lbl_total_time.setStyleSheet("color: #6c757d; font-size: 12px;")
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderPressed.connect(self.slider_pressed)
        self.slider.sliderReleased.connect(self.slider_released)
        self.slider.valueChanged.connect(self.slider_moved)
        
        progress_layout.addWidget(self.lbl_curr_time)
        progress_layout.addWidget(self.slider, stretch=1)
        progress_layout.addWidget(self.lbl_total_time)
        player_layout.addLayout(progress_layout)
        
        # 控制按钮
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addStretch()
        
        self.btn_mode = QPushButton("🔁")
        self.btn_mode.setProperty("CtrlBtn", True)
        self.btn_mode.setToolTip("播放模式")
        self.btn_mode.clicked.connect(self.toggle_mode)
        
        btn_prev = QPushButton("⏮")
        btn_prev.setProperty("CtrlBtn", True)
        btn_prev.setToolTip("上一首")
        btn_prev.clicked.connect(self.play_prev)
        
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("PlayBtn")
        self.btn_play.setToolTip("播放/暂停")
        self.btn_play.clicked.connect(self.toggle_play)
        
        btn_next = QPushButton("⏭")
        btn_next.setProperty("CtrlBtn", True)
        btn_next.setToolTip("下一首")
        btn_next.clicked.connect(self.play_next)
        
        self.btn_rate = QPushButton("1.0x")
        self.btn_rate.setProperty("CtrlBtn", True)
        self.btn_rate.setToolTip("播放速度")
        self.btn_rate.clicked.connect(self.toggle_rate)
        
        ctrl_layout.addWidget(self.btn_mode)
        ctrl_layout.addSpacing(10)
        ctrl_layout.addWidget(btn_prev)
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(btn_next)
        ctrl_layout.addSpacing(10)
        ctrl_layout.addWidget(self.btn_rate)
        ctrl_layout.addStretch()
        
        player_layout.addLayout(ctrl_layout)
        
        # 偏移调整
        offset_layout = QHBoxLayout()
        offset_layout.addStretch()
        
        btn_slow = QPushButton("⏪ -0.5s")
        btn_slow.setProperty("OffsetBtn", True)
        btn_slow.clicked.connect(lambda: self.adjust_offset(-0.5))
        
        self.lbl_offset = QLabel("0.0s")
        self.lbl_offset.setStyleSheet("color: #6c757d; font-size: 11px; padding: 4px 8px;")
        
        btn_fast = QPushButton("+0.5s ⏩")
        btn_fast.setProperty("OffsetBtn", True)
        btn_fast.clicked.connect(lambda: self.adjust_offset(0.5))
        
        offset_layout.addWidget(btn_slow)
        offset_layout.addWidget(self.lbl_offset)
        offset_layout.addWidget(btn_fast)
        offset_layout.addStretch()
        
        player_layout.addLayout(offset_layout)
        right_layout.addWidget(player_bar)
        
        layout.addWidget(right_panel)

    def search_songs(self, text):
        """搜索歌曲"""
        if not text.strip():
            # 恢复显示所有歌曲
            if hasattr(self, '_original_playlist'):
                self.playlist = self._original_playlist.copy()
                self.refresh_table()
            return
            
        if not hasattr(self, '_original_playlist'):
            self._original_playlist = self.playlist.copy()
            
        search_text = text.lower()
        filtered_playlist = []
        
        for song in self._original_playlist:
            song_name = os.path.splitext(song["name"])[0].lower()
            artist = song.get("artist", "").lower()
            album = song.get("album", "").lower()
            
            if (search_text in song_name or 
                search_text in artist or 
                search_text in album):
                filtered_playlist.append(song)
                
        self.playlist = filtered_playlist
        self.refresh_table()

    def refresh_table(self):
        """刷新表格显示"""
        self.table.setRowCount(len(self.playlist))
        for row, song in enumerate(self.playlist):
            self.table.setItem(row, 0, QTableWidgetItem(os.path.splitext(song["name"])[0]))
            self.table.setItem(row, 1, QTableWidgetItem(song.get("artist", "未知")))
            self.table.setItem(row, 2, QTableWidgetItem(song.get("album", "未知")))
            self.table.setItem(row, 3, QTableWidgetItem(song.get("duration", "-")))

    # === 核心功能方法 ===
    def full_scan(self):
        """扫描音乐文件夹"""
        if not self.music_folder or not os.path.exists(self.music_folder):
            return
            
        self.collections = []
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4')
        
        # 扫描合集文件夹
        for item in os.listdir(self.music_folder):
            full_path = os.path.join(self.music_folder, item)
            if os.path.isdir(full_path):
                # 检查是否是合集文件夹（包含多个音乐文件）
                files = [x for x in os.listdir(full_path) if x.lower().endswith(exts)]
                if len(files) > 1:  # 包含多个音乐文件的文件夹才显示为合集
                    self.collections.append(item)
        
        # 更新导航列表
        self.nav_list.clear()
        self.nav_list.addItem("💿 全部音乐")
        self.nav_list.addItem("🕒 最近播放")
        for c in self.collections:
            self.nav_list.addItem(f"📁 {c}")
        
        # 加载当前视图
        if self.current_collection == "HISTORY":
            self.load_history_view()
        elif not self.current_collection or self.current_collection not in self.collections:
            self.current_collection = ""
            self.load_songs_for_collection()
        else:
            self.load_songs_for_collection()

    def switch_collection(self, item):
        """切换合集"""
        text = item.text()
        if "全部音乐" in text:
            self.current_collection = ""
            self.lbl_collection_title.setText("全部音乐")
            self.load_songs_for_collection()
        elif "最近播放" in text:
            self.current_collection = "HISTORY"
            self.lbl_collection_title.setText("最近播放")
            self.load_history_view()
        else:
            self.current_collection = text.replace("📁 ", "")
            self.lbl_collection_title.setText(f"合集：{self.current_collection}")
            self.load_songs_for_collection()

    def load_songs_for_collection(self):
        """加载指定合集的歌曲"""
        self.playlist = []
        self.table.setRowCount(0)
        exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4')
        
        target_dirs = []
        if self.current_collection:
            target_dirs = [os.path.join(self.music_folder, self.current_collection)]
        else:
            target_dirs = [self.music_folder]
            # 包含所有合集文件夹
            for item in os.listdir(self.music_folder):
                p = os.path.join(self.music_folder, item)
                if os.path.isdir(p) and item in self.collections:
                    target_dirs.append(p)

        row = 0
        for d in target_dirs:
            if not os.path.exists(d):
                continue
                
            for f in os.listdir(d):
                if f.lower().endswith(exts):
                    full_path = os.path.abspath(os.path.join(d, f))
                    meta = self.metadata.get(f, {
                        "artist": "未知歌手", 
                        "album": self.current_collection if self.current_collection else "默认专辑"
                    })
                    
                    song_data = {
                        "path": full_path,
                        "name": f,
                        "artist": meta.get("artist"),
                        "album": meta.get("album"),
                        "duration": "-"
                    }
                    self.playlist.append(song_data)
                    
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(os.path.splitext(f)[0]))
                    self.table.setItem(row, 1, QTableWidgetItem(meta.get("artist", "")))
                    self.table.setItem(row, 2, QTableWidgetItem(meta.get("album", "")))
                    self.table.setItem(row, 3, QTableWidgetItem("-"))
                    row += 1
        
        # 保存原始播放列表用于搜索
        self._original_playlist = self.playlist.copy()

    def load_history_view(self):
        """加载历史播放记录"""
        self.playlist = []
        self.table.setRowCount(0)
        
        for song in self.history:
            if os.path.exists(song["path"]):
                self.playlist.append(song)
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(os.path.splitext(song["name"])[0]))
                self.table.setItem(row, 1, QTableWidgetItem(song.get("artist", "")))
                self.table.setItem(row, 2, QTableWidgetItem(song.get("album", "")))
                self.table.setItem(row, 3, QTableWidgetItem(song.get("duration", "-")))

    def show_context_menu(self, pos):
        """显示右键菜单"""
        items = self.table.selectedItems()
        if not items:
            return
            
        selected_rows = sorted(list(set(i.row() for i in items)))
        menu = QMenu(self)
        
        # 播放操作
        if len(selected_rows) == 1:
            menu.addAction("▶ 播放", lambda: self.play_index(selected_rows[0]))
            menu.addSeparator()
        
        # 歌词操作
        if len(selected_rows) == 1:
            menu.addAction("🔍 搜索歌词", lambda: self.open_manual_search(selected_rows[0]))
            menu.addAction("❌ 删除歌词", lambda: self.remove_lyric(selected_rows[0]))
            menu.addSeparator()
        
        # 批量操作
        if len(selected_rows) > 0:
            move_menu = menu.addMenu("📂 移动到合集")
            
            # 根目录
            root_action = QAction("📂 根目录", self)
            root_action.triggered.connect(lambda: self.batch_move_files(selected_rows, ""))
            move_menu.addAction(root_action)
            move_menu.addSeparator()
            
            # 其他合集
            for collection in self.collections:
                if collection != self.current_collection:
                    action = QAction(f"📁 {collection}", self)
                    action.triggered.connect(lambda checked, c=collection: self.batch_move_files(selected_rows, c))
                    move_menu.addAction(action)
            
            menu.addAction(f"🗑️ 删除选中歌曲 ({len(selected_rows)}首)", 
                          lambda: self.delete_songs(selected_rows))
        
        menu.exec_(self.table.mapToGlobal(pos))

    def open_batch_move_dialog(self):
        """打开批量移动对话框"""
        selected_rows = sorted(list(set(i.row() for i in self.table.selectedItems())))
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要移动的歌曲")
            return
            
        dialog = BatchMoveDialog(self.collections, self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            self.batch_move_files(selected_rows, data['target'], data)

    def batch_move_files(self, rows, target_name, options=None):
        """批量移动文件"""
        options = options or {}
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认移动",
            f"确定要将 {len(rows)} 首歌曲移动到 {'根目录' if not target_name else target_name} 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        target_path = self.music_folder
        if target_name:
            target_path = os.path.join(self.music_folder, target_name)
            if not os.path.exists(target_path):
                os.makedirs(target_path)
        
        moved_count = 0
        for row in rows:
            if row >= len(self.playlist):
                continue
                
            song = self.playlist[row]
            try:
                src_path = song["path"]
                dst_path = os.path.join(target_path, song["name"])
                
                # 移动音频文件
                if options.get('move_files', True):
                    if src_path != dst_path:
                        shutil.move(src_path, dst_path)
                        song["path"] = dst_path
                
                # 移动歌词文件
                lrc_src = os.path.splitext(src_path)[0] + ".lrc"
                if os.path.exists(lrc_src):
                    lrc_dst = os.path.splitext(dst_path)[0] + ".lrc"
                    shutil.move(lrc_src, lrc_dst)
                
                # 更新元数据
                if options.get('update_metadata', True) and target_name:
                    self.metadata[song["name"]] = self.metadata.get(song["name"], {})
                    self.metadata[song["name"]]["album"] = target_name
                
                moved_count += 1
                
            except Exception as e:
                print(f"移动文件失败: {e}")
        
        # 保存更新后的元数据
        self.save_metadata()
        
        # 刷新界面
        self.full_scan()
        QMessageBox.information(self, "完成", f"成功移动 {moved_count} 首歌曲")

    def download_from_bilibili(self):
        """从B站下载音频"""
        if not self.music_folder:
            QMessageBox.warning(self, "提示", "请先设置音乐根目录")
            return
            
        url, ok = QInputDialog.getText(self, "B站下载", "请输入B站视频链接:")
        if not ok or not url:
            return
            
        # 解析分P信息
        p_num = 1
        match = re.search(r'[?&]p=(\d+)', url)
        if match:
            p_num = int(match.group(1))
            
        dialog = DownloadDialog(self, p_num, self.collections)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            save_path = self.music_folder
            if data['folder']:
                save_path = os.path.join(self.music_folder, data['folder'])
                if not os.path.exists(save_path):
                    os.makedirs(save_path)
            
            # 准备元数据
            metadata = {}
            if data['artist']:
                metadata['artist'] = data['artist']
            if data['album']:
                metadata['album'] = data['album']
            
            self.downloader = BilibiliDownloader(
                url, save_path, data['mode'], p_num, metadata
            )
            self.downloader.progress_signal.connect(
                lambda s: self.lbl_collection_title.setText(s)
            )
            self.downloader.finished_signal.connect(self.on_download_finished)
            self.downloader.error_signal.connect(
                lambda e: QMessageBox.warning(self, "下载错误", e)
            )
            self.downloader.start()
            
            self.lbl_collection_title.setText("⏳ 开始下载...")

    def on_download_finished(self, folder_path, file_list):
        """下载完成处理"""
        # 更新元数据
        for filename in file_list:
            if filename not in self.metadata:
                self.metadata[filename] = {}
        
        self.save_metadata()
        self.full_scan()
        
        # 自动搜索歌词
        if hasattr(self, 'temp_dl_artist'):
            QMessageBox.information(self, "完成", 
                                  f"下载完成！共下载 {len(file_list)} 个文件")
        else:
            QMessageBox.information(self, "完成", 
                                  f"下载完成！共下载 {len(file_list)} 个文件")

    def open_manual_search(self, idx):
        """打开手动歌词搜索"""
        if idx >= len(self.playlist):
            return
            
        song = self.playlist[idx]
        song_name = os.path.splitext(song["name"])[0]
        artist = song.get("artist", "")
        duration = self.player.duration() if self.current_index == idx else 0
        
        dialog = LyricSearchDialog(song_name, artist, duration, self)
        if dialog.exec_() == QDialog.Accepted and dialog.result_id:
            lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
            self.lyric_downloader = LyricDownloader(dialog.result_id, lrc_path)
            self.lyric_downloader.finished_signal.connect(
                lambda content: self.on_lyric_downloaded(content, idx)
            )
            self.lyric_downloader.error_signal.connect(
                lambda e: QMessageBox.warning(self, "歌词下载失败", e)
            )
            self.lyric_downloader.start()
            
            QMessageBox.information(self, "提示", "开始下载歌词...")

    def on_lyric_downloaded(self, content, idx):
        """歌词下载完成"""
        if self.current_index == idx:
            self.parse_lrc_content(content)
        QMessageBox.information(self, "成功", "歌词下载完成！")

    def remove_lyric(self, idx):
        """删除歌词文件"""
        if idx >= len(self.playlist):
            return
            
        song = self.playlist[idx]
        lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
        
        if os.path.exists(lrc_path):
            os.remove(lrc_path)
            if self.current_index == idx:
                self.parse_lrc_content("")
                self.panel_lyric.clear()
            QMessageBox.information(self, "完成", "歌词文件已删除")
        else:
            QMessageBox.information(self, "提示", "未找到歌词文件")

    def play_selected(self, item):
        """播放选中的歌曲"""
        self.play_index(item.row())

    def play_index(self, idx):
        """播放指定索引的歌曲"""
        if not self.playlist or idx >= len(self.playlist):
            return
            
        self.current_index = idx
        song = self.playlist[idx]
        
        # 添加到播放历史
        if song not in self.history:
            self.history.insert(0, song)
            if len(self.history) > 100:  # 限制历史记录数量
                self.history.pop()
            self.save_history()
        
        try:
            media_content = QMediaContent(QUrl.fromLocalFile(song["path"]))
            self.player.setMedia(media_content)
            self.player.setPlaybackRate(self.rate)
            self.player.play()
            
            # 更新播放按钮状态
            self.btn_play.setText("⏸")
            
            # 恢复偏移量
            self.offset = self.saved_offsets.get(song["name"], 0.0)
            self.update_offset_label()
            
            # 加载歌词
            lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
            if os.path.exists(lrc_path):
                self.parse_lrc_file(lrc_path)
            else:
                self.panel_lyric.clear()
                self.panel_lyric.addItem("🎵 正在播放...")
                # 自动搜索歌词
                self.auto_search_lyric(song)
                
        except Exception as e:
            print(f"播放失败: {e}")
            QMessageBox.warning(self, "播放错误", f"无法播放文件: {e}")

    def auto_search_lyric(self, song):
        """自动搜索歌词"""
        song_name = os.path.splitext(song["name"])[0]
        self.auto_searcher = LyricListSearchWorker(song_name)
        self.auto_searcher.search_finished.connect(
            lambda results: self.on_auto_search_result(results, song)
        )
        self.auto_searcher.start()

    def on_auto_search_result(self, results, song):
        """自动搜索歌词结果"""
        if results:
            # 选择最佳匹配
            best_match = results[0]
            lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
            
            self.auto_downloader = LyricDownloader(best_match['id'], lrc_path)
            self.auto_downloader.finished_signal.connect(
                lambda content: self.parse_lrc_content(content)
            )
            self.auto_downloader.start()

    def parse_lrc_file(self, path):
        """解析歌词文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.parse_lrc_content(content)
        except UnicodeDecodeError:
            try:
                with open(path, 'r', encoding='gbk') as f:
                    content = f.read()
                    self.parse_lrc_content(content)
            except Exception as e:
                print(f"解析歌词文件失败: {e}")
                self.panel_lyric.clear()
                self.panel_lyric.addItem("❌ 歌词文件解析失败")

    def parse_lrc_content(self, content):
        """解析歌词内容"""
        self.lyrics = []
        self.panel_lyric.clear()
        
        if not content:
            self.panel_lyric.addItem("🎵 纯音乐，请欣赏")
            return
            
        pattern = re.compile(r'\[(\d+):(\d+)\.(\d+)\](.*)')
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # 匹配时间标签
            match = pattern.match(line)
            if match:
                minutes, seconds, milliseconds, text = match.groups()
                if text.strip():  # 只添加非空歌词
                    time_sec = int(minutes) * 60 + int(seconds) + int(milliseconds) / 100
                    self.lyrics.append({"t": time_sec, "txt": text.strip()})
                    self.panel_lyric.addItem(text.strip())
        
        # 如果没有找到有效歌词
        if not self.lyrics:
            # 尝试其他格式
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('['):
                    self.panel_lyric.addItem(line)
        
        if self.panel_lyric.count() == 0:
            self.panel_lyric.addItem("🎵 暂无歌词")

    # === 播放控制方法 ===
    def adjust_offset(self, value):
        """调整歌词偏移"""
        self.offset += value
        self.update_offset_label()
        if self.current_index >= 0:
            song_name = self.playlist[self.current_index]["name"]
            self.saved_offsets[song_name] = self.offset
            self.save_offsets()

    def update_offset_label(self):
        """更新偏移量显示"""
        sign = "+" if self.offset >= 0 else ""
        self.lbl_offset.setText(f"偏移: {sign}{self.offset:.1f}s")

    def toggle_play(self):
        """切换播放/暂停"""
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶")
        else:
            self.player.play()
            self.btn_play.setText("⏸")

    def toggle_mode(self):
        """切换播放模式"""
        self.mode = (self.mode + 1) % 3
        modes = ["🔁 顺序", "🔂 单曲", "🔀 随机"]
        self.btn_mode.setText(modes[self.mode])

    def toggle_rate(self):
        """切换播放速度"""
        rates = [1.0, 1.25, 1.5, 2.0, 0.5]
        try:
            current_index = rates.index(self.rate)
        except ValueError:
            current_index = 0
            
        self.rate = rates[(current_index + 1) % len(rates)]
        self.player.setPlaybackRate(self.rate)
        self.btn_rate.setText(f"{self.rate}x")

    def play_next(self):
        """播放下一首"""
        if not self.playlist:
            return
            
        if self.mode == 2:  # 随机模式
            next_index = random.randint(0, len(self.playlist) - 1)
        else:  # 顺序模式
            next_index = (self.current_index + 1) % len(self.playlist)
            
        self.play_index(next_index)

    def play_prev(self):
        """播放上一首"""
        if not self.playlist:
            return
            
        if self.mode == 2:  # 随机模式
            prev_index = random.randint(0, len(self.playlist) - 1)
        else:  # 顺序模式
            prev_index = (self.current_index - 1) % len(self.playlist)
            
        self.play_index(prev_index)

    def on_position_changed(self, pos):
        """播放位置改变"""
        if not self.is_slider_pressed:
            self.slider.setValue(pos)
            
        self.lbl_curr_time.setText(ms_to_str(pos))
        
        # 计算带偏移的当前时间
        current_sec = pos / 1000 + self.offset
        
        # 更新歌词显示
        if self.lyrics:
            current_lyric_index = -1
            
            # 找到当前应该显示的歌词
            for i, lyric in enumerate(self.lyrics):
                if current_sec >= lyric["t"]:
                    current_lyric_index = i
                else:
                    break
            
            if current_lyric_index >= 0:
                # 确保索引在范围内
                if current_lyric_index < self.panel_lyric.count():
                    self.panel_lyric.setCurrentRow(current_lyric_index)
                    
                    # 平滑滚动到当前歌词
                    self.panel_lyric.scrollToItem(
                        self.panel_lyric.item(current_lyric_index),
                        QAbstractItemView.PositionAtCenter
                    )
                
                # 更新桌面歌词
                prev_text = self.lyrics[current_lyric_index - 1]["txt"] if current_lyric_index > 0 else ""
                current_text = self.lyrics[current_lyric_index]["txt"]
                next_text = self.lyrics[current_lyric_index + 1]["txt"] if current_lyric_index < len(self.lyrics) - 1 else ""
                
                self.desktop_lyric.set_lyrics(prev_text, current_text, next_text)

    def slider_pressed(self):
        """进度条按下"""
        self.is_slider_pressed = True

    def slider_released(self):
        """进度条释放"""
        self.is_slider_pressed = False
        self.player.setPosition(self.slider.value())

    def slider_moved(self, value):
        """进度条移动"""
        if self.is_slider_pressed:
            self.lbl_curr_time.setText(ms_to_str(value))

    def on_duration_changed(self, duration):
        """歌曲时长改变"""
        self.slider.setRange(0, duration)
        self.lbl_total_time.setText(ms_to_str(duration))
        
        # 更新表格中的时长显示
        if self.current_index >= 0:
            self.table.setItem(self.current_index, 3, QTableWidgetItem(ms_to_str(duration)))
            self.playlist[self.current_index]["duration"] = ms_to_str(duration)

    def on_state_changed(self, state):
        """播放状态改变"""
        self.btn_play.setText("⏸" if state == QMediaPlayer.PlayingState else "▶")

    def on_media_status_changed(self, status):
        """媒体状态改变"""
        if status == QMediaPlayer.EndOfMedia:
            if self.mode == 1:  # 单曲循环
                self.player.play()
            else:
                self.play_next()

    def select_folder(self):
        """选择音乐文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择音乐根目录")
        if folder:
            self.music_folder = folder
            self.full_scan()
            self.save_config()
            QMessageBox.information(self, "成功", f"已设置音乐根目录: {folder}")

    def toggle_lyric(self):
        """切换桌面歌词显示"""
        if self.desktop_lyric.isVisible():
            self.desktop_lyric.hide()
        else:
            self.desktop_lyric.show()

    def delete_songs(self, rows):
        """删除歌曲"""
        if not rows:
            return
            
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 {len(rows)} 首歌曲吗？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        # 停止播放
        if self.current_index in rows:
            self.player.stop()
            self.current_index = -1
            
        deleted_count = 0
        for row in sorted(rows, reverse=True):  # 从后往前删除
            if row < len(self.playlist):
                song = self.playlist[row]
                try:
                    # 删除音频文件
                    if os.path.exists(song["path"]):
                        os.remove(song["path"])
                    
                    # 删除歌词文件
                    lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
                    if os.path.exists(lrc_path):
                        os.remove(lrc_path)
                    
                    # 从播放列表中移除
                    self.playlist.pop(row)
                    deleted_count += 1
                    
                except Exception as e:
                    print(f"删除文件失败: {e}")
        
        # 刷新界面
        self.refresh_table()
        QMessageBox.information(self, "完成", f"已删除 {deleted_count} 首歌曲")

    # === 配置管理 ===
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.music_folder = config.get("music_folder", "")
                    
                    # 恢复桌面歌词设置
                    lyric_geo = config.get("lyric_geometry")
                    if lyric_geo:
                        self.desktop_lyric.setGeometry(*lyric_geo)
                    
                    lyric_color = config.get("lyric_color")
                    if lyric_color:
                        self.desktop_lyric.font_color = QColor(*lyric_color)
                        self.desktop_lyric.update_styles()
            
            # 加载其他数据
            for file_name, target_var in [
                (OFFSET_FILE, "saved_offsets"),
                (METADATA_FILE, "metadata"), 
                (HISTORY_FILE, "history")
            ]:
                if os.path.exists(file_name):
                    with open(file_name, 'r', encoding='utf-8') as f:
                        setattr(self, target_var, json.load(f))
            
            # 扫描音乐库
            if self.music_folder:
                self.full_scan()
                
        except Exception as e:
            print(f"加载配置失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            config = {
                "music_folder": self.music_folder,
                "lyric_geometry": self.desktop_lyric.geometry().getRect(),
                "lyric_color": self.desktop_lyric.font_color.getRgb()[:3]
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def save_offsets(self):
        """保存偏移量"""
        try:
            with open(OFFSET_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.saved_offsets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存偏移量失败: {e}")

    def save_metadata(self):
        """保存元数据"""
        try:
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存元数据失败: {e}")

    def save_history(self):
        """保存历史记录"""
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史记录失败: {e}")

    def handle_player_error(self):
        """处理播放器错误"""
        error_msg = self.player.errorString()
        if error_msg:
            print(f"播放器错误: {error_msg}")
            QMessageBox.warning(self, "播放错误", f"无法播放当前文件: {error_msg}")
            QTimer.singleShot(1000, self.play_next)

    def closeEvent(self, event):
        """关闭事件"""
        self.save_config()
        self.save_offsets()
        self.save_metadata()
        self.save_history()
        event.accept()

if __name__ == "__main__":
    # 设置高DPI支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("汽水音乐")
    app.setApplicationVersion("2.0")
    
    # 设置字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    # 创建并显示窗口
    player = SodaPlayer()
    player.show()
    
    sys.exit(app.exec_())

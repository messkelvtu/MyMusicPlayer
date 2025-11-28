import os
import re
from PyQt5.QtCore import QThread, pyqtSignal

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str, int)  # 进度文本和百分比
    finished_signal = pyqtSignal(str, str)  # 路径和文件名
    error_signal = pyqtSignal(str)          # 错误信息

    def __init__(self, url, path, mode, start, end=None):
        super().__init__()
        self.url = url
        self.path = path
        self.mode = mode  # 'single' 或 'playlist'
        self.start = start
        self.end = end
        self.is_canceled = False

    def run(self):
        if not yt_dlp:
            self.error_signal.emit("未安装 yt-dlp，无法下载\n请使用 pip install yt-dlp 安装")
            return

        # 验证并创建目录
        if not self._validate_and_create_directory():
            return

        # 配置下载选项
        opts = self._get_download_options()

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])
            if not self.is_canceled:
                self.finished_signal.emit(self.path, "下载完成")
        except Exception as e:
            if not self.is_canceled:
                self.error_signal.emit(f"下载失败: {str(e)}")

    def _validate_and_create_directory(self):
        try:
            if not os.path.exists(self.path):
                os.makedirs(self.path)
            if not os.access(self.path, os.W_OK):
                self.error_signal.emit("目标路径没有写入权限")
                return False
            return True
        except Exception as e:
            self.error_signal.emit(f"无法创建目录: {str(e)}")
            return False

    def _get_download_options(self):
        # 构建播放列表选项
        playlist_items = ""
        if self.mode == 'single':
            playlist_items = str(self.start)
        elif self.mode == 'playlist' and self.end:
            playlist_items = f"{self.start}-{self.end}"
        elif self.mode == 'playlist':
            playlist_items = f"{self.start}-"

        # 清理标题中的特殊字符
        def clean_title(title):
            return re.sub(r'[\\/*?:"<>|]', "_", title)

        return {
            'format': 'bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': os.path.join(self.path, f'{clean_title("%(title)s")}.%(ext)s'),
            'overwrites': False,
            'noplaylist': self.mode == 'single',
            'playlist_items': playlist_items,
            'progress_hooks': [self._progress_hook],
            'quiet': True,
            'nocheckcertificate': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }] if self.mode == 'audio' else [],
        }

    def _progress_hook(self, d):
        if self.is_canceled:
            raise Exception("下载已取消")
            
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').replace('%', '').strip()
            try:
                percent_int = int(float(percent))
            except:
                percent_int = 0
                
            filename = os.path.basename(d.get('filename', ''))[:20]
            self.progress_signal.emit(f"正在下载: {filename}...", percent_int)
        elif d['status'] == 'finished':
            self.progress_signal.emit("正在处理文件...", 100)

    def cancel_download(self):
        self.is_canceled = True

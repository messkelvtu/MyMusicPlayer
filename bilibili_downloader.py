import os
from PyQt5.QtCore import QThread, pyqtSignal

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

class BilibiliDownloader(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str, str)
    error_signal = pyqtSignal(str)

    def __init__(self, url, path, mode, sp):
        super().__init__()
        self.u = url
        self.p = path
        self.m = mode
        self.sp = sp

    def run(self):
        if not yt_dlp:
            self.error_signal.emit("未安装 yt-dlp，无法下载")
            return

        if not os.path.exists(self.p):
            try:
                os.makedirs(self.p)
            except Exception as e:
                self.error_signal.emit(f"无法创建目录: {e}")
                return

        def progress_hook(d):
            if d['status'] == 'downloading':
                self.progress_signal.emit(f"    {d.get('_percent_str', '')} {os.path.basename(d.get('filename', ''))[:20]}...")

        opts = {
            'format': 'bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': os.path.join(self.p, '%(title)s.%(ext)s'),
            'overwrites': True,
            'noplaylist': self.m == 'single',
            'playlist_items': str(self.sp) if self.m == 'single' else f"{self.sp}-",
            'progress_hooks': [progress_hook],
            'quiet': True,
            'nocheckcertificate': True,
            'restrictfilenames': False
        }

        try:
            with yt_dlp.YoutubeDL(opts) as y:
                y.download([self.u])
            self.finished_signal.emit(self.p, "")
        except Exception as e:
            self.error_signal.emit(str(e))

import re
import json
import urllib.request
import urllib.parse
from PyQt5.QtCore import QThread, pyqtSignal

# -- 辅助函数 --
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def ms_to_str(ms):
    if not ms:
        return "00:00"
    s = ms // 1000
    return f"{s//60:02}:{s%60:02}"

# --- 功能线程 ---
class LyricListSearchWorker(QThread):
    search_finished = pyqtSignal(list)

    def __init__(self, keyword):
        super().__init__()
        self.keyword = keyword

    def run(self):
        try:
            url = "http://music.163.com/api/search/get/web?csrf_token="
            headers = {"User-Agent": 'Mozilla/5.0'}
            data = urllib.parse.urlencode({
                's': self.keyword,
                'type': 1,
                'offset': 0,
                'total': 'true',
                'limit': 15
            }).encode('utf-8')

            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as f:
                res = json.loads(f.read().decode('utf-8'))

            results = [] 
            if res.get('result') and res['result'].get('songs'):
                for s in res['result']['songs']:
                    artist = s['artists'][0]['name'] if s['artists'] else "未知"
                    duration = s.get('duration', 0)
                    results.append({
                        'name': s['name'],
                        'artist': artist,
                        'id': s['id'],
                        'duration': duration,
                        'duration_str': ms_to_str(duration)
                    })
            self.search_finished.emit(results)
        except Exception as e:
            print(f"歌词搜索错误: {e}")
            self.search_finished.emit([])

class LyricDownloader(QThread):
    finished_signal = pyqtSignal(str)

    def __init__(self, sid, path):
        super().__init__()
        self.sid = sid
        self.path = path

    def run(self):
        try:
            url = f"http://music.163.com/api/song/lyric?os=pc&id={self.sid}&lv=-1&kv=-1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as f:
                res = json.loads(f.read().decode('utf-8'))

            if 'lrc' in res:
                lrc = res['lrc']['lyric']
                with open(self.path, 'w', encoding='utf-8') as f:
                    f.write(lrc)
                self.finished_signal.emit(lrc)
        except Exception as e:
            print(f"歌词下载错误: {e}")

# 图标映射
ICONS = {
    "music": "♫",
    "download": "↓",
    "disc": "●",
    "history": "🕒",
    "heart": "♥",
    "fire": "🔥",
    "star": "★",
    "sync": "🔄",
    "folder_plus": "📁+",
    "truck": "🚚",
    "folder_open": "📁",
    "microphone": "🎤",
    "search": "🔍",
    "edit": "✏️",
    "random": "🔀",
    "play": "▶",
    "pause": "⏸",
    "ellipsis": "⋯",
    "step_backward": "⏮",
    "step_forward": "⏭",
    "retweet": "🔁",
    "volume": "🔊",
    "sliders": "🎚",
    "youtube": "📺",
    "save": "💾",
    "check": "✓",
    "text_height": "A",
    "palette": "🎨",
    "font": "A",
    "align_center": "☰",
    "chevron_down": "▼",
    "close": "✕",
    "info": "ℹ",
    "warning": "⚠",
    "error": "✗"
}

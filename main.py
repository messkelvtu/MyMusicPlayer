import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import pygame
import threading
import time

# --- 配置 ---
# 默认配置，实际运行中会读取文件夹内的 _music_data.json
DEFAULT_DATA = {
    "favorites": [],
    "tags": {},  # "filename": ["热血", "欧美"]
    "last_play": {"file": None, "pos": 0},
    "offsets": {} # "filename": 0.5
}

class MusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("极客本地音乐 (EXE版)")
        self.root.geometry("1000x700")
        self.root.configure(bg="#2b2b2b")

        # 变量
        self.music_folder = ""
        self.playlist = [] # [{name, path, tags, is_fav}]
        self.current_song = None
        self.is_playing = False
        self.db = DEFAULT_DATA.copy()
        self.lyrics = []
        self.lyric_lines = [] # UI labels
        self.offset = 0

        # 初始化音频
        pygame.mixer.init()

        # --- 样式 ---
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background="#333", foreground="white", fieldbackground="#333", rowheight=30, borderwidth=0)
        style.configure("Treeview.Heading", background="#444", foreground="white", font=('Arial', 10, 'bold'))
        style.map("Treeview", background=[('selected', '#1db954')])

        # --- 布局 ---
        
        # 顶部工具栏
        top_frame = tk.Frame(root, bg="#222", padx=10, pady=10)
        top_frame.pack(fill=tk.X)
        
        tk.Button(top_frame, text="📂 选择歌单文件夹", bg="#1db954", fg="white", font=("Arial", 11, "bold"), relief="flat", command=self.select_folder).pack(side=tk.LEFT, padx=5)
        
        # 搜索框
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_list)
        tk.Label(top_frame, text="🔍", bg="#222", fg="#aaa").pack(side=tk.LEFT, padx=(20,5))
        search_entry = tk.Entry(top_frame, textvariable=self.search_var, bg="#444", fg="white", insertbackground="white", relief="flat", font=("Arial", 11))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 中间：左右分栏
        paned = tk.PanedWindow(root, bg="#2b2b2b", orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧：列表
        left_frame = tk.Frame(paned, bg="#2b2b2b")
        paned.add(left_frame, minsize=400)

        # 过滤器按钮
        filter_frame = tk.Frame(left_frame, bg="#2b2b2b")
        filter_frame.pack(fill=tk.X, pady=5)
        tk.Button(filter_frame, text="全部", command=lambda: self.apply_filter("all"), bg="#444", fg="white", bd=0, padx=10).pack(side=tk.LEFT, padx=2)
        tk.Button(filter_frame, text="❤️ 收藏", command=lambda: self.apply_filter("fav"), bg="#e91e63", fg="white", bd=0, padx=10).pack(side=tk.LEFT, padx=2)
        
        # 列表视图
        columns = ("name", "tags")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="歌曲名")
        self.tree.heading("tags", text="标签/分类")
        self.tree.column("name", width=300)
        self.tree.column("tags", width=100)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self.play_selected)
        self.tree.bind("<Button-3>", self.show_context_menu) # 右键菜单

        # 右键菜单
        self.context_menu = tk.Menu(root, tearoff=0)
        self.context_menu.add_command(label="❤️ 切换收藏", command=self.toggle_fav_context)
        self.context_menu.add_command(label="🏷️ 修改分类标签", command=self.edit_tags_context)

        # 右侧：歌词与控制
        right_frame = tk.Frame(paned, bg="#181818")
        paned.add(right_frame, minsize=300)

        # 信息显示
        self.lbl_title = tk.Label(right_frame, text="未播放", font=("Microsoft YaHei", 18, "bold"), bg="#181818", fg="white", pady=20)
        self.lbl_title.pack()

        # 歌词区
        lyric_canvas = tk.Frame(right_frame, bg="#181818")
        lyric_canvas.pack(fill=tk.BOTH, expand=True, padx=20)
        
        self.lyric_label = tk.Label(lyric_canvas, text="\n\n请选择文件夹开始\n\n", font=("Microsoft YaHei", 14), bg="#181818", fg="#888", justify=tk.CENTER)
        self.lyric_label.pack(expand=True)

        # 控制区
        ctrl_frame = tk.Frame(right_frame, bg="#282828", height=100)
        ctrl_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_scale = tk.Scale(ctrl_frame, variable=self.progress_var, from_=0, to=100, orient=tk.HORIZONTAL, showvalue=0, bg="#282828", fg="#1db954", highlightthickness=0, troughcolor="#444", command=self.seek_music)
        self.progress_scale.pack(fill=tk.X, padx=10, pady=5)
        
        btns_frame = tk.Frame(ctrl_frame, bg="#282828")
        btns_frame.pack(pady=10)

        tk.Button(btns_frame, text="⏮", command=self.play_prev, bg="#282828", fg="white", bd=0, font=("Arial", 16)).pack(side=tk.LEFT, padx=10)
        self.btn_play = tk.Button(btns_frame, text="▶", command=self.toggle_play, bg="white", fg="black", bd=0, font=("Arial", 16), width=3)
        self.btn_play.pack(side=tk.LEFT, padx=10)
        tk.Button(btns_frame, text="⏭", command=self.play_next, bg="#282828", fg="white", bd=0, font=("Arial", 16)).pack(side=tk.LEFT, padx=10)
        
        # 校准按钮
        offset_frame = tk.Frame(ctrl_frame, bg="#282828")
        offset_frame.pack(pady=5)
        tk.Label(offset_frame, text="歌词校准:", bg="#282828", fg="#888").pack(side=tk.LEFT)
        tk.Button(offset_frame, text="-0.5s", command=lambda: self.adjust_offset(-0.5), bg="#444", fg="white", bd=0, font=("Arial", 8)).pack(side=tk.LEFT, padx=5)
        self.lbl_offset = tk.Label(offset_frame, text="0.0s", bg="#282828", fg="#1db954")
        self.lbl_offset.pack(side=tk.LEFT)
        tk.Button(offset_frame, text="+0.5s", command=lambda: self.adjust_offset(0.5), bg="#444", fg="white", bd=0, font=("Arial", 8)).pack(side=tk.LEFT, padx=5)

        # 定时器线程
        self.check_event = threading.Event()
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()

        # 尝试自动加载上次的文件夹
        try:
            with open("app_config.json", "r") as f:
                cfg = json.load(f)
                if os.path.exists(cfg.get("last_folder", "")):
                    self.load_library(cfg["last_folder"])
        except:
            pass

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.load_library(path)
            # 保存配置，方便下次自动打开
            with open("app_config.json", "w") as f:
                json.dump({"last_folder": path}, f)

    def load_library(self, folder):
        self.music_folder = folder
        self.db_path = os.path.join(folder, "_music_data.json")
        
        # 读取或初始化数据库
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding='utf-8') as f:
                    self.db = json.load(f)
            except:
                self.db = DEFAULT_DATA.copy()
        else:
            self.db = DEFAULT_DATA.copy()
        
        self.refresh_list()
        
        # 恢复上次播放
        last = self.db.get("last_play", {})
        if last.get("file"):
            print(f"上次播放: {last['file']}")

    def refresh_list(self):
        self.playlist = []
        files = os.listdir(self.music_folder)
        exts = ('.mp3', '.wav', '.ogg')
        
        for f in files:
            if f.lower().endswith(exts):
                tags = self.db["tags"].get(f, [])
                is_fav = f in self.db["favorites"]
                self.playlist.append({
                    "name": f,
                    "path": os.path.join(self.music_folder, f),
                    "tags": tags,
                    "is_fav": is_fav
                })
        
        self.apply_filter("all")

    def apply_filter(self, mode):
        # 清空列表
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        search_key = self.search_var.get().lower()
        
        for song in self.playlist:
            # 搜索过滤
            if search_key and search_key not in song["name"].lower():
                continue

            # 模式过滤
            if mode == "fav" and not song["is_fav"]:
                continue
            
            # 显示
            disp_tags = ",".join(song["tags"])
            disp_name = ("❤️ " if song["is_fav"] else "") + song["name"]
            
            item_id = self.tree.insert("", tk.END, values=(disp_name, disp_tags))
            
            # 高亮当前播放
            if self.current_song and song["name"] == self.current_song["name"]:
                self.tree.selection_set(item_id)

    def filter_list(self, *args):
        self.apply_filter("all")

    def play_selected(self, event):
        selected = self.tree.selection()
        if not selected: return
        item = self.tree.item(selected[0])
        name_raw = item['values'][0].replace("❤️ ", "")
        
        # 找到对应歌曲对象
        for s in self.playlist:
            if s["name"] == name_raw:
                self.play_music(s)
                break

    def play_music(self, song_obj):
        self.current_song = song_obj
        try:
            pygame.mixer.music.load(song_obj["path"])
            pygame.mixer.music.play()
            self.is_playing = True
            self.btn_play.config(text="⏸")
            self.lbl_title.config(text=song_obj["name"])
            
            # 读取Offset
            self.offset = self.db["offsets"].get(song_obj["name"], 0)
            self.update_offset_lbl()
            
            # 加载歌词
            lrc_path = os.path.splitext(song_obj["path"])[0] + ".lrc"
            self.load_lyrics(lrc_path)
            
            # 保存状态
            self.save_db()
            
        except Exception as e:
            messagebox.showerror("错误", f"无法播放: {e}")

    def toggle_play(self):
        if not self.current_song: return
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.btn_play.config(text="▶")
        else:
            pygame.mixer.music.unpause()
            self.is_playing = True
            self.btn_play.config(text="⏸")

    def load_lyrics(self, path):
        self.lyrics = []
        if not os.path.exists(path):
            self.lyric_label.config(text="未找到歌词文件")
            return
        
        import re
        pattern = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\](.*)')
        try:
            with open(path, 'r', encoding='utf-8') as f: # 默认utf-8
                lines = f.readlines()
        except:
            try:
                with open(path, 'r', encoding='gbk') as f: # 尝试gbk
                    lines = f.readlines()
            except:
                self.lyric_label.config(text="歌词编码无法识别")
                return

        for line in lines:
            match = pattern.search(line)
            if match:
                m, s, ms_str, txt = match.groups()
                ms = int(ms_str) if len(ms_str) == 3 else int(ms_str)*10 if len(ms_str)==2 else 0
                t = int(m)*60 + int(s) + ms/1000.0
                if txt.strip():
                    self.lyrics.append({'time': t, 'text': txt.strip()})
        self.lyrics.sort(key=lambda x: x['time'])

    def update_loop(self):
        while True:
            if self.is_playing and pygame.mixer.music.get_busy():
                try:
                    # 更新进度条 (模拟，因为pygame get_pos 不准确且很难seek)
                    # 这里为了演示简单，不做精确的拖拽同步，只做歌词同步
                    
                    cur_ms = pygame.mixer.music.get_pos()
                    # Pygame get_pos 重置问题很麻烦，这里仅作为演示核心逻辑
                    # 真正完美的MP3播放器通常需要 mutagen 库获取总时长
                    
                    # 歌词同步
                    if self.lyrics:
                        cur_sec = (cur_ms / 1000.0) - self.offset
                        # 找当前句
                        txt = "..."
                        for i, line in enumerate(self.lyrics):
                            if cur_sec >= line['time']:
                                txt = line['text']
                            else:
                                break
                        
                        # 在主线程更新UI
                        self.root.after(0, lambda t=txt: self.lyric_label.config(text=t, fg="#1db954"))
                except:
                    pass
            time.sleep(0.1)

    # --- 进度条拖动 (Pygame缺陷：MP3 seek支持不好，wav可以) ---
    def seek_music(self, val):
        # 这是一个占位符，MP3 Seek在Pygame里很复杂
        pass 

    def play_next(self):
        if not self.current_song or not self.playlist: return
        # 找当前索引
        idx = -1
        for i, s in enumerate(self.playlist):
            if s["name"] == self.current_song["name"]:
                idx = i
                break
        if idx != -1 and idx < len(self.playlist)-1:
            self.play_music(self.playlist[idx+1])

    def play_prev(self):
        # 逻辑同上，略
        pass

    # --- 右键菜单功能 ---
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def toggle_fav_context(self):
        selected = self.tree.selection()
        if not selected: return
        item = self.tree.item(selected[0])
        name_raw = item['values'][0].replace("❤️ ", "")
        
        if name_raw in self.db["favorites"]:
            self.db["favorites"].remove(name_raw)
        else:
            self.db["favorites"].append(name_raw)
        
        self.save_db()
        self.refresh_list()

    def edit_tags_context(self):
        selected = self.tree.selection()
        if not selected: return
        item = self.tree.item(selected[0])
        name_raw = item['values'][0].replace("❤️ ", "")
        
        old_tags = ",".join(self.db["tags"].get(name_raw, []))
        new_tags = simpledialog.askstring("修改分类", "请输入分类(逗号分隔):", initialvalue=old_tags)
        
        if new_tags is not None:
            tag_list = [t.strip() for t in new_tags.split(",") if t.strip()]
            self.db["tags"][name_raw] = tag_list
            self.save_db()
            self.refresh_list()

    def adjust_offset(self, delta):
        if not self.current_song: return
        self.offset += delta
        self.offset = round(self.offset, 2)
        self.db["offsets"][self.current_song["name"]] = self.offset
        self.save_db()
        self.update_offset_lbl()
        
    def update_offset_lbl(self):
        sign = "+" if self.offset > 0 else ""
        self.lbl_offset.config(text=f"{sign}{self.offset}s")

    def save_db(self):
        if self.db_path:
            with open(self.db_path, "w", encoding='utf-8') as f:
                json.dump(self.db, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    root = tk.Tk()
    app = MusicPlayer(root)
    root.mainloop()
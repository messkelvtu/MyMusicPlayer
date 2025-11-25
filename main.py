import os
import json
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pygame

# --- QQ音乐风格配置 ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green") # QQ绿

DATA_FILE = "qq_music_data.json"

class QQMusicPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 窗口设置
        self.title("QQ音乐 (本地极速版)")
        self.geometry("1200x750")
        self.minsize(1000, 600)

        # 数据
        self.music_folder = ""
        self.all_songs = [] 
        self.playlists = {"❤️ 我喜欢的": [], "🎵 本地歌曲": []}
        self.custom_playlists = []
        self.current_playlist_key = "🎵 本地歌曲"
        self.current_song_list = [] # 当前视图显示的歌曲
        self.current_song = None
        self.is_playing = False
        self.lyrics = [] # [{time, text}]
        self.offset = 0
        self.lyric_lines_map = {} # 映射行号到时间

        pygame.mixer.init()
        self.load_data()

        # --- 布局 (Grid) ---
        self.grid_columnconfigure(1, weight=3) # 歌单区
        self.grid_columnconfigure(2, weight=2) # 歌词区
        self.grid_rowconfigure(0, weight=1)    # 主内容
        self.grid_rowconfigure(1, weight=0)    # 播放条

        # 1. 左侧侧边栏 (导航)
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#191919")
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="QQ音乐", font=("Microsoft YaHei", 24, "bold"), text_color="#1ECC94").pack(pady=30)
        
        self.btn_local = self.create_nav_btn("🎵 本地歌曲")
        self.btn_fav = self.create_nav_btn("❤️ 我喜欢的")
        
        ctk.CTkLabel(self.sidebar, text="创建的歌单", text_color="gray", anchor="w").pack(fill="x", padx=20, pady=(20, 10))
        self.playlist_container = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.playlist_container.pack(fill="both", expand=True)
        
        ctk.CTkButton(self.sidebar, text="+ 新建歌单", fg_color="transparent", border_width=1, border_color="gray", text_color="gray", command=self.add_playlist_dialog).pack(pady=20, padx=20)
        ctk.CTkButton(self.sidebar, text="📂 导入文件夹", fg_color="#1ECC94", text_color="white", hover_color="#158c67", command=self.select_folder).pack(pady=(0, 20), padx=20)

        # 2. 中间：歌单列表
        self.center_frame = ctk.CTkFrame(self, fg_color="#222222", corner_radius=0)
        self.center_frame.grid(row=0, column=1, sticky="nsew")
        
        # 搜索栏
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.do_search)
        search_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=20)
        ctk.CTkEntry(search_frame, textvariable=self.search_var, placeholder_text="🔍 搜索音乐...", width=300).pack(side="left")
        
        # 列表头
        self.list_title = ctk.CTkLabel(self.center_frame, text="本地歌曲", font=("Microsoft YaHei", 20, "bold"), anchor="w")
        self.list_title.pack(fill="x", padx=20, pady=(0, 10))
        
        # 歌曲列表 (Scrollable)
        self.song_list_frame = ctk.CTkScrollableFrame(self.center_frame, fg_color="transparent")
        self.song_list_frame.pack(fill="both", expand=True, padx=10)

        # 3. 右侧：歌词区 (QQ音乐风格)
        self.lyric_frame = ctk.CTkFrame(self, fg_color="#2B2B2B", corner_radius=0)
        self.lyric_frame.grid(row=0, column=2, sticky="nsew")
        
        # 歌曲信息大字
        self.info_frame = ctk.CTkFrame(self.lyric_frame, fg_color="transparent")
        self.info_frame.pack(pady=(40, 20))
        self.lbl_big_title = ctk.CTkLabel(self.info_frame, text="QQ音乐", font=("Microsoft YaHei", 22, "bold"))
        self.lbl_big_title.pack()
        self.lbl_big_artist = ctk.CTkLabel(self.info_frame, text="听我想听", font=("Microsoft YaHei", 14), text_color="gray")
        self.lbl_big_artist.pack()

        # 歌词显示控件 (Text Widget)
        # 使用原生 Text 实现精准滚动
        self.lyric_text = tk.Text(self.lyric_frame, bg="#2B2B2B", fg="#888", font=("Microsoft YaHei", 12), 
                                  bd=0, highlightthickness=0, state="disabled", cursor="arrow")
        self.lyric_text.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 配置 Tag (高亮样式)
        self.lyric_text.tag_config("center", justify="center")
        self.lyric_text.tag_config("current", foreground="#1ECC94", font=("Microsoft YaHei", 16, "bold"))
        self.lyric_text.tag_config("normal", foreground="#888", font=("Microsoft YaHei", 12))

        # 校准微调
        offset_box = ctk.CTkFrame(self.lyric_frame, fg_color="transparent")
        offset_box.pack(pady=10)
        ctk.CTkLabel(offset_box, text="歌词调整:", font=("Arial", 10), text_color="gray").pack(side="left")
        ctk.CTkButton(offset_box, text="-0.5", width=40, height=20, fg_color="#444", command=lambda: self.adjust_offset(-0.5)).pack(side="left", padx=5)
        self.lbl_offset = ctk.CTkLabel(offset_box, text="0.0s", font=("Arial", 10), text_color="#1ECC94")
        self.lbl_offset.pack(side="left")
        ctk.CTkButton(offset_box, text="+0.5", width=40, height=20, fg_color="#444", command=lambda: self.adjust_offset(0.5)).pack(side="left", padx=5)

        # 4. 底部播放控制条
        self.player_bar = ctk.CTkFrame(self, height=80, fg_color="#252525", corner_radius=0)
        self.player_bar.grid(row=1, column=0, columnspan=3, sticky="ew")
        
        # 进度条 (置顶)
        self.slider = ctk.CTkSlider(self.player_bar, from_=0, to=100, height=15, button_color="#1ECC94", progress_color="#1ECC94", command=self.seek_music)
        self.slider.pack(fill="x", pady=(0, 5))
        self.slider.set(0)
        
        # 控制区
        ctrl_box = ctk.CTkFrame(self.player_bar, fg_color="transparent")
        ctrl_box.pack(fill="both", expand=True)
        
        # 左侧歌曲小字
        self.bar_info = ctk.CTkLabel(ctrl_box, text="Ready", anchor="w", width=200)
        self.bar_info.pack(side="left", padx=20)
        
        # 中间按钮
        btns = ctk.CTkFrame(ctrl_box, fg_color="transparent")
        btns.pack(side="left", expand=True)
        
        ctk.CTkButton(btns, text="⏮", width=40, fg_color="transparent", command=self.play_prev).pack(side="left", padx=10)
        self.btn_play = ctk.CTkButton(btns, text="▶", width=50, height=50, corner_radius=25, fg_color="#1ECC94", hover_color="#158c67", command=self.toggle_play)
        self.btn_play.pack(side="left", padx=10)
        ctk.CTkButton(btns, text="⏭", width=40, fg_color="transparent", command=self.play_next).pack(side="left", padx=10)
        
        # 右侧操作
        ctk.CTkButton(ctrl_box, text="❤️", width=40, fg_color="transparent", text_color="gray", font=("Arial", 20), command=self.toggle_fav).pack(side="right", padx=20)
        ctk.CTkButton(ctrl_box, text="+", width=40, fg_color="transparent", font=("Arial", 20), command=self.add_to_playlist_menu).pack(side="right")

        # 初始化列表
        self.render_playlists_sidebar()
        self.switch_playlist("🎵 本地歌曲")
        
        # 启动线程
        threading.Thread(target=self.loop_monitor, daemon=True).start()

    def create_nav_btn(self, text):
        btn = ctk.CTkButton(self.sidebar, text=text, fg_color="transparent", text_color="#ccc", hover_color="#333", anchor="w", height=40, font=("Microsoft YaHei", 14), command=lambda t=text: self.switch_playlist(t))
        btn.pack(fill="x", padx=10, pady=2)
        return btn

    # --- 核心逻辑 ---
    
    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.music_folder = data.get("folder", "")
                    self.playlists["❤️ 我喜欢的"] = data.get("favorites", [])
                    custom = data.get("custom", {})
                    for k, v in custom.items():
                        self.custom_playlists.append(k)
                        self.playlists[k] = v
                    
                    if self.music_folder: self.scan_files(init=True)
            except: pass

    def save_data(self):
        data = {
            "folder": self.music_folder,
            "favorites": self.playlists["❤️ 我喜欢的"],
            "custom": {k: self.playlists[k] for k in self.custom_playlists}
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def select_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.music_folder = d
            self.scan_files()
            self.save_data()

    def scan_files(self, init=False):
        self.all_songs = []
        for root, _, files in os.walk(self.music_folder):
            for f in files:
                if f.lower().endswith(('.mp3', '.wav', '.ogg')):
                    self.all_songs.append({"name": f, "path": os.path.join(root, f), "artist": "未知歌手"})
        
        self.playlists["🎵 本地歌曲"] = [s["path"] for s in self.all_songs]
        if not init:
            self.switch_playlist("🎵 本地歌曲")
            messagebox.showinfo("扫描完成", f"共找到 {len(self.all_songs)} 首歌")

    def render_playlists_sidebar(self):
        for w in self.playlist_container.winfo_children(): w.destroy()
        for pl in self.custom_playlists:
            frame = ctk.CTkFrame(self.playlist_container, fg_color="transparent")
            frame.pack(fill="x")
            btn = ctk.CTkButton(frame, text=f"📄 {pl}", fg_color="transparent", anchor="w", text_color="#aaa", hover_color="#333", command=lambda n=pl: self.switch_playlist(n))
            btn.pack(side="left", fill="x", expand=True)
            # 删除按钮
            ctk.CTkButton(frame, text="×", width=20, fg_color="transparent", text_color="#666", hover_color="#333", command=lambda n=pl: self.delete_playlist(n)).pack(side="right")

    def switch_playlist(self, name):
        self.current_playlist_key = name
        self.list_title.configure(text=name)
        
        # 重置搜索
        self.search_var.set("")
        
        paths = self.playlists.get(name, [])
        # 将路径转为对象 (优化性能)
        path_map = {s["path"]: s for s in self.all_songs}
        
        self.current_song_list = []
        for p in paths:
            if p in path_map: self.current_song_list.append(path_map[p])
            else: self.current_song_list.append({"name": os.path.basename(p), "path": p, "artist": "?"})
            
        self.render_song_list()

    def render_song_list(self):
        for w in self.song_list_frame.winfo_children(): w.destroy()
        
        for idx, song in enumerate(self.current_song_list):
            row = ctk.CTkFrame(self.song_list_frame, fg_color="transparent", height=40)
            row.pack(fill="x", pady=1)
            
            # 颜色交替
            bg = "#2B2B2B" if idx % 2 == 0 else "transparent"
            btn = ctk.CTkButton(row, text=f"  {idx+1}    {song['name']}", anchor="w", fg_color=bg, hover_color="#333", text_color="#ddd", command=lambda s=song: self.play_music(s))
            btn.pack(fill="both", expand=True)

    def do_search(self, *args):
        key = self.search_var.get().lower()
        if not key:
            self.switch_playlist(self.current_playlist_key)
            return
        
        # 在全库搜索
        self.current_song_list = [s for s in self.all_songs if key in s["name"].lower()]
        self.render_song_list()

    # --- 播放与歌词逻辑 (核心) ---
    
    def play_music(self, song):
        try:
            pygame.mixer.music.load(song["path"])
            pygame.mixer.music.play()
            self.is_playing = True
            self.current_song = song
            self.btn_play.configure(text="⏸")
            
            self.bar_info.configure(text=song["name"])
            self.lbl_big_title.configure(text=song["name"])
            
            # 加载歌词
            lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
            self.load_lyrics(lrc_path)
        except Exception as e:
            print(e)

    def load_lyrics(self, path):
        self.lyrics = []
        self.lyric_text.configure(state="normal")
        self.lyric_text.delete("1.0", "end")
        
        content = "暂无歌词"
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: lines = f.readlines()
            except:
                try: 
                    with open(path, 'r', encoding='gbk') as f: lines = f.readlines()
                except: lines = []
            
            import re
            ptn = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\](.*)')
            
            valid_lines = []
            for line in lines:
                match = ptn.search(line)
                if match:
                    m, s, ms_str, txt = match.groups()
                    ms = int(ms_str) if len(ms_str)==3 else int(ms_str)*10
                    t = int(m)*60 + int(s) + ms/1000
                    if txt.strip():
                        valid_lines.append((t, txt.strip()))
            
            if valid_lines:
                content = ""
                self.lyrics = valid_lines
                for i, (t, txt) in enumerate(valid_lines):
                    # 插入文本，每行加两个 tag: center 和 line_i
                    self.lyric_text.insert("end", txt + "\n", ("center", "normal", f"line_{i}"))
        else:
            self.lyric_text.insert("end", "\n\n暂无歌词\n纯音乐，请欣赏", "center")
        
        self.lyric_text.configure(state="disabled")

    def loop_monitor(self):
        last_idx = -1
        while True:
            if self.is_playing and pygame.mixer.music.get_busy() and self.lyrics:
                pos = pygame.mixer.music.get_pos() / 1000 + self.offset
                
                # 找到当前句
                cur_idx = -1
                for i, (t, txt) in enumerate(self.lyrics):
                    if pos >= t: cur_idx = i
                    else: break
                
                if cur_idx != last_idx:
                    self.update_lyric_ui(cur_idx, last_idx)
                    last_idx = cur_idx
            time.sleep(0.1)

    def update_lyric_ui(self, cur_idx, last_idx):
        # 使用 Tkinter Text 的 tag 功能实现高亮和滚动
        try:
            self.lyric_text.configure(state="normal")
            
            # 1. 恢复上一句样式
            if last_idx != -1:
                self.lyric_text.tag_remove("current", f"line_{last_idx}.first", f"line_{last_idx}.last")
                self.lyric_text.tag_add("normal", f"line_{last_idx}.first", f"line_{last_idx}.last")

            # 2. 高亮当前句
            if cur_idx != -1:
                self.lyric_text.tag_remove("normal", f"line_{cur_idx}.first", f"line_{cur_idx}.last")
                self.lyric_text.tag_add("current", f"line_{cur_idx}.first", f"line_{cur_idx}.last")
                
                # 3. 滚动到中间 (QQ音乐核心体验)
                # "see" 方法会把该行滚动到可见区域，为了居中，我们不仅要 see 当前行
                # 还可以算出大概位置。这里用 see 很稳定。
                self.lyric_text.see(f"line_{cur_idx+5}.first") # 看后面几行，让当前行被顶上去一点
                self.lyric_text.see(f"line_{cur_idx}.first")   # 确保当前行肯定可见
                
            self.lyric_text.configure(state="disabled")
        except: pass

    # --- 其他功能 ---
    def toggle_play(self):
        if not self.current_song: return
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.btn_play.configure(text="▶")
        else:
            pygame.mixer.music.unpause()
            self.is_playing = True
            self.btn_play.configure(text="⏸")

    def play_next(self):
        if not self.current_song: return
        try:
            # 简单查找
            idx = -1
            for i, s in enumerate(self.current_song_list):
                if s["path"] == self.current_song["path"]: idx=i; break
            if idx != -1 and idx < len(self.current_song_list)-1:
                self.play_music(self.current_song_list[idx+1])
        except: pass

    def play_prev(self):
        # 略
        pass

    def seek_music(self, val):
        pass # pygame mp3 seek 支持有限，暂略

    def adjust_offset(self, delta):
        self.offset += delta
        self.lbl_offset.configure(text=f"{round(self.offset, 1)}s")

    def add_playlist_dialog(self):
        name = ctk.CTkInputDialog(text="歌单名称:", title="新建").get_input()
        if name:
            self.custom_playlists.append(name)
            self.playlists[name] = []
            self.render_playlists_sidebar()
            self.save_data()

    def delete_playlist(self, name):
        if messagebox.askyesno("删除", "确定删除?"):
            self.custom_playlists.remove(name)
            del self.playlists[name]
            self.render_playlists_sidebar()
            self.switch_playlist("🎵 本地歌曲")
            self.save_data()

    def toggle_fav(self):
        if not self.current_song: return
        p = self.current_song["path"]
        l = self.playlists["❤️ 我喜欢的"]
        if p in l: l.remove(p); messagebox.showinfo("","已取消收藏")
        else: l.append(p); messagebox.showinfo("","已收藏")
        self.save_data()

    def add_to_playlist_menu(self):
        if not self.current_song: return
        if not self.custom_playlists: return messagebox.showerror("","没有自建歌单")
        name = ctk.CTkInputDialog(text=f"输入歌单名 ({','.join(self.custom_playlists)}):", title="添加").get_input()
        if name in self.playlists:
            self.playlists[name].append(self.current_song["path"])
            self.save_data()
            messagebox.showinfo("","已添加")

if __name__ == "__main__":
    app = QQMusicPlayer()
    app.mainloop()

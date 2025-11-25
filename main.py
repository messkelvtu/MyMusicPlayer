import os
import json
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk  # 现代UI库
import pygame

# --- 配置 ---
ctk.set_appearance_mode("Dark")  # 深色模式
ctk.set_default_color_theme("green")  # 主题色（类似Spotify绿）

DATA_FILE = "music_data.json"

class ModernMusicPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 窗口设置
        self.title("极客云音乐 (GeekMusic)")
        self.geometry("1100x700")
        self.minsize(900, 600)

        # 数据初始化
        self.music_folder = ""
        self.all_songs = []  # [{path, name, artist}]
        self.playlists = {
            "❤️ 我喜欢的": [], 
            "🎵 全部歌曲": []
        }
        self.custom_playlists = [] # ["伤感", "运动"]
        self.current_playlist_name = "🎵 全部歌曲"
        self.current_playlist_data = [] # 当前列表显示的歌曲对象
        self.current_song = None
        self.is_playing = False
        self.lyrics = []
        self.offset = 0

        # 初始化 Pygame
        pygame.mixer.init()

        # 加载本地数据
        self.load_data()

        # --- 布局 ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. 左侧边栏 (Sidebar)
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1) # 让下面的按钮顶上去

        self.logo_label = ctk.CTkLabel(self.sidebar, text="🎵 极客云音乐", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # 侧边栏按钮
        self.sidebar_btn_all = self.create_sidebar_btn("🎵 全部歌曲", 1)
        self.sidebar_btn_fav = self.create_sidebar_btn("❤️ 我喜欢的", 2)
        
        # 分隔线
        ctk.CTkFrame(self.sidebar, height=2, fg_color="gray30").grid(row=3, column=0, sticky="ew", padx=20, pady=10)

        # 自定义歌单区 (Scrollable)
        self.playlist_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.playlist_frame.grid(row=4, column=0, sticky="nsew")
        
        # 底部功能按钮
        self.btn_import = ctk.CTkButton(self.sidebar, text="📂 导入文件夹", command=self.select_folder)
        self.btn_import.grid(row=5, column=0, padx=20, pady=10)
        
        self.btn_add_pl = ctk.CTkButton(self.sidebar, text="+ 新建歌单", fg_color="transparent", border_width=1, text_color="gray90", command=self.create_playlist_dialog)
        self.btn_add_pl.grid(row=6, column=0, padx=20, pady=(0, 20))

        # 2. 右侧主内容区
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_area.grid_columnconfigure(0, weight=3) # 歌曲列表宽
        self.main_area.grid_columnconfigure(1, weight=2) # 歌词宽
        self.main_area.grid_rowconfigure(1, weight=1)

        # 顶部搜索栏
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_music)
        self.entry_search = ctk.CTkEntry(self.main_area, placeholder_text="🔍 搜索歌曲...", textvariable=self.search_var)
        self.entry_search.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))

        # 歌曲列表 (使用 ScrollableFrame 模拟列表)
        self.scroll_songs = ctk.CTkScrollableFrame(self.main_area, label_text="歌曲列表")
        self.scroll_songs.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        
        # 歌词面板
        self.lyric_frame = ctk.CTkFrame(self.main_area, fg_color=("gray85", "gray20"))
        self.lyric_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")
        
        self.lbl_lyric_title = ctk.CTkLabel(self.lyric_frame, text="暂无播放", font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_lyric_title.pack(pady=20)
        
        self.txt_lyrics = ctk.CTkTextbox(self.lyric_frame, font=ctk.CTkFont(size=14), activate_scrollbars=False)
        self.txt_lyrics.pack(fill="both", expand=True, padx=10, pady=10)
        self.txt_lyrics.configure(state="disabled")

        # 校准按钮
        self.offset_frame = ctk.CTkFrame(self.lyric_frame, fg_color="transparent")
        self.offset_frame.pack(pady=10)
        ctk.CTkButton(self.offset_frame, text="<<", width=30, command=lambda: self.adjust_offset(-0.5)).pack(side="left", padx=5)
        self.lbl_offset = ctk.CTkLabel(self.offset_frame, text="0.0s")
        self.lbl_offset.pack(side="left", padx=5)
        ctk.CTkButton(self.offset_frame, text=">>", width=30, command=lambda: self.adjust_offset(0.5)).pack(side="left", padx=5)

        # 3. 底部播放控制条
        self.player_bar = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color=("white", "gray15"))
        self.player_bar.grid(row=1, column=1, sticky="ew")
        
        # 进度条
        self.slider = ctk.CTkSlider(self.player_bar, from_=0, to=100, command=self.seek_music)
        self.slider.pack(fill="x", padx=10, pady=5)
        self.slider.set(0)

        # 控制按钮容器
        self.ctrl_frame = ctk.CTkFrame(self.player_bar, fg_color="transparent")
        self.ctrl_frame.pack(pady=5)
        
        ctk.CTkButton(self.ctrl_frame, text="⏮", width=40, fg_color="transparent", command=self.play_prev).pack(side="left", padx=10)
        self.btn_play = ctk.CTkButton(self.ctrl_frame, text="▶", width=50, height=50, corner_radius=25, command=self.toggle_play)
        self.btn_play.pack(side="left", padx=10)
        ctk.CTkButton(self.ctrl_frame, text="⏭", width=40, fg_color="transparent", command=self.play_next).pack(side="left", padx=10)
        
        # 收藏与添加到歌单按钮
        self.btn_fav = ctk.CTkButton(self.ctrl_frame, text="♡", width=30, fg_color="transparent", font=ctk.CTkFont(size=20), text_color="gray", command=self.toggle_fav)
        self.btn_fav.pack(side="left", padx=20)
        
        ctk.CTkButton(self.ctrl_frame, text="+", width=30, fg_color="transparent", font=ctk.CTkFont(size=20), command=self.add_to_playlist_dialog).pack(side="left")

        # 渲染歌单
        self.refresh_custom_playlists()
        
        # 启动线程
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()

    def create_sidebar_btn(self, text, row):
        btn = ctk.CTkButton(self.sidebar, text=text, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=lambda t=text: self.switch_playlist(t))
        btn.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        return btn

    # --- 数据逻辑 ---
    def load_data(self):
        # 尝试读取上次的文件夹
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.music_folder = data.get("folder", "")
                    self.playlists["❤️ 我喜欢的"] = data.get("favorites", [])
                    # 加载自定义歌单
                    custom = data.get("custom_playlists", {})
                    for name, songs in custom.items():
                        self.custom_playlists.append(name)
                        self.playlists[name] = songs
                    
                    if self.music_folder and os.path.exists(self.music_folder):
                        self.scan_music(init=True)
            except:
                pass

    def save_data(self):
        # 保存喜爱列表、歌单配置、路径
        custom_export = {}
        for pl in self.custom_playlists:
            custom_export[pl] = self.playlists[pl]
            
        data = {
            "folder": self.music_folder,
            "favorites": self.playlists["❤️ 我喜欢的"],
            "custom_playlists": custom_export
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.music_folder = folder
            self.scan_music()
            self.save_data()

    def scan_music(self, init=False):
        self.all_songs = []
        # 递归扫描
        for root, dirs, files in os.walk(self.music_folder):
            for file in files:
                if file.lower().endswith(('.mp3', '.wav', '.ogg')):
                    full_path = os.path.join(root, file)
                    self.all_songs.append({
                        "name": file,
                        "path": full_path,
                        "artist": "未知歌手" # 这里简化，实际可以用 mutagen 读取
                    })
        self.playlists["🎵 全部歌曲"] = [s["path"] for s in self.all_songs]
        if not init:
            self.switch_playlist("🎵 全部歌曲")
            messagebox.showinfo("完成", f"共扫描到 {len(self.all_songs)} 首歌曲")

    # --- 界面交互 ---
    
    def refresh_custom_playlists(self):
        # 清除旧的按钮
        for widget in self.playlist_frame.winfo_children():
            widget.destroy()
        
        for pl_name in self.custom_playlists:
            btn = ctk.CTkButton(self.playlist_frame, text=f"📄 {pl_name}", fg_color="transparent", anchor="w", 
                                text_color=("gray10", "gray90"), 
                                command=lambda n=pl_name: self.switch_playlist(n))
            btn.pack(fill="x", pady=2)
            
            # 右键删除功能 (简单的绑定)
            btn.bind("<Button-3>", lambda event, n=pl_name: self.delete_playlist(n))

    def create_playlist_dialog(self):
        name = ctk.CTkInputDialog(text="输入新歌单名称:", title="新建歌单").get_input()
        if name and name not in self.playlists:
            self.custom_playlists.append(name)
            self.playlists[name] = []
            self.refresh_custom_playlists()
            self.save_data()

    def delete_playlist(self, name):
        if messagebox.askyesno("删除", f"确定删除歌单 {name} 吗?"):
            self.custom_playlists.remove(name)
            del self.playlists[name]
            self.refresh_custom_playlists()
            self.switch_playlist("🎵 全部歌曲")
            self.save_data()

    def switch_playlist(self, playlist_name):
        self.current_playlist_name = playlist_name
        self.scroll_songs.configure(label_text=playlist_name)
        
        # 获取路径列表
        paths = self.playlists.get(playlist_name, [])
        
        # 转换为歌曲对象列表
        # 注意：如果文件被删了，这里可能要容错，为了简单我们暂时通过路径匹配
        self.current_playlist_data = []
        
        # 为了效率，构建一个查找字典
        all_songs_map = {s["path"]: s for s in self.all_songs}
        
        if playlist_name == "🎵 全部歌曲":
             self.current_playlist_data = self.all_songs
        else:
            for path in paths:
                if path in all_songs_map:
                    self.current_playlist_data.append(all_songs_map[path])
                else:
                    # 如果找不到(可能没扫到)，临时造一个对象
                    self.current_playlist_data.append({"name": os.path.basename(path), "path": path, "artist": "?"})

        self.render_song_list()

    def filter_music(self, *args):
        if self.current_playlist_name != "🎵 全部歌曲":
            return # 简单处理，搜索只在全部歌曲里搜，或者过滤当前列表
        
        keyword = self.search_var.get().lower()
        if not keyword:
            self.current_playlist_data = self.all_songs
        else:
            self.current_playlist_data = [s for s in self.all_songs if keyword in s["name"].lower()]
        self.render_song_list()

    def render_song_list(self):
        # 清空列表
        for widget in self.scroll_songs.winfo_children():
            widget.destroy()

        for idx, song in enumerate(self.current_playlist_data):
            # 每一行是一个 Frame
            row = ctk.CTkFrame(self.scroll_songs, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            # 播放按钮
            btn = ctk.CTkButton(row, text=f"{idx+1}. {song['name']}", anchor="w", fg_color="transparent", 
                                command=lambda s=song: self.play_music(s))
            btn.pack(side="left", fill="x", expand=True)
            
            # 更多操作可以加在这里

    # --- 播放核心 ---
    def play_music(self, song):
        try:
            pygame.mixer.music.load(song["path"])
            pygame.mixer.music.play()
            self.current_song = song
            self.is_playing = True
            self.btn_play.configure(text="⏸")
            self.lbl_lyric_title.configure(text=song["name"])
            
            # 检查收藏状态
            if song["path"] in self.playlists["❤️ 我喜欢的"]:
                self.btn_fav.configure(text="❤️", text_color="#e91e63")
            else:
                self.btn_fav.configure(text="♡", text_color="gray")

            # 加载歌词
            lrc_path = os.path.splitext(song["path"])[0] + ".lrc"
            self.load_lyrics(lrc_path)

        except Exception as e:
            print(e)
            messagebox.showerror("错误", "无法播放该文件")

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
        # 找当前索引
        try:
            idx = self.current_playlist_data.index(self.current_song)
            if idx < len(self.current_playlist_data) - 1:
                self.play_music(self.current_playlist_data[idx+1])
        except: pass

    def play_prev(self):
        if not self.current_song: return
        try:
            idx = self.current_playlist_data.index(self.current_song)
            if idx > 0:
                self.play_music(self.current_playlist_data[idx-1])
        except: pass

    def seek_music(self, value):
        if self.current_song:
            # pygame mp3 seek 支持不完美，这里仅做尝试
            # 实际上你需要 mutagen 获取总时长来计算百分比
            pass 

    # --- 歌词与收藏 ---
    def load_lyrics(self, path):
        self.lyrics = []
        self.offset = 0
        self.lbl_offset.configure(text="0.0s")
        
        self.txt_lyrics.configure(state="normal")
        self.txt_lyrics.delete("1.0", "end")
        
        if os.path.exists(path):
            import re
            ptn = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\](.*)')
            try:
                with open(path, 'r', encoding='utf-8') as f: lines = f.readlines()
            except:
                try:
                    with open(path, 'r', encoding='gbk') as f: lines = f.readlines()
                except: lines = []
            
            full_text = ""
            for line in lines:
                match = ptn.search(line)
                if match:
                    m, s, ms_str, txt = match.groups()
                    ms = int(ms_str) if len(ms_str)==3 else int(ms_str)*10
                    t = int(m)*60 + int(s) + ms/1000
                    self.lyrics.append({'time': t, 'text': txt.strip()})
                    full_text += txt.strip() + "\n"
            
            self.txt_lyrics.insert("1.0", full_text)
        else:
            self.txt_lyrics.insert("1.0", "暂无歌词")
        
        self.txt_lyrics.configure(state="disabled")

    def toggle_fav(self):
        if not self.current_song: return
        path = self.current_song["path"]
        favs = self.playlists["❤️ 我喜欢的"]
        
        if path in favs:
            favs.remove(path)
            self.btn_fav.configure(text="♡", text_color="gray")
        else:
            favs.append(path)
            self.btn_fav.configure(text="❤️", text_color="#e91e63")
        self.save_data()

    def add_to_playlist_dialog(self):
        if not self.current_song: return
        if not self.custom_playlists:
            messagebox.showinfo("提示", "请先新建歌单")
            return
            
        # 简单的选择逻辑：弹窗让用户输入歌单名（为了简化代码）
        # 更好的做法是弹出一个 Listbox 窗口
        pl = ctk.CTkInputDialog(text=f"输入歌单名称 ({','.join(self.custom_playlists)}):", title="添加到...").get_input()
        if pl in self.playlists:
            if self.current_song["path"] not in self.playlists[pl]:
                self.playlists[pl].append(self.current_song["path"])
                self.save_data()
                messagebox.showinfo("成功", "已添加")
            else:
                messagebox.showinfo("提示", "已存在于该歌单")
        else:
            messagebox.showerror("错误", "歌单不存在")

    def adjust_offset(self, delta):
        self.offset += delta
        self.lbl_offset.configure(text=f"{round(self.offset, 1)}s")

    def update_loop(self):
        while True:
            if self.is_playing and pygame.mixer.music.get_busy():
                pos = pygame.mixer.music.get_pos()
                # 歌词高亮逻辑 (简化版)
                # 实际应用中需要计算 scroll 位置
                pass
            time.sleep(0.5)

if __name__ == "__main__":
    app = ModernMusicPlayer()
    app.mainloop()

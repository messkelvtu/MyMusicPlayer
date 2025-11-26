<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>音乐播放器 - 黑色毛衣</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Microsoft YaHei', Arial, sans-serif;
        }
        
        body {
            background-color: #0f0f0f;
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        /* 顶部信息区域 */
        .song-info {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
        }
        
        .song-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 8px;
            color: #ffffff;
        }
        
        .song-artist {
            font-size: 16px;
            color: #aaaaaa;
        }
        
        /* 歌词区域 */
        .lyrics-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 20px;
            position: relative;
        }
        
        .lyrics-content {
            width: 100%;
            max-width: 600px;
            text-align: center;
            line-height: 1.8;
        }
        
        .lyrics-line {
            font-size: 20px;
            margin: 15px 0;
            transition: all 0.3s ease;
            opacity: 0.5;
        }
        
        .lyrics-line.active {
            font-size: 24px;
            color: #ffffff;
            opacity: 1;
            font-weight: bold;
        }
        
        /* 底部控制区域 */
        .player-controls {
            background-color: #1a1a1a;
            padding: 20px;
            border-radius: 12px;
            margin-top: 20px;
        }
        
        .progress-container {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .progress-time {
            font-size: 12px;
            color: #888;
            min-width: 40px;
        }
        
        .progress-bar {
            flex: 1;
            height: 4px;
            background-color: #333;
            border-radius: 2px;
            margin: 0 10px;
            position: relative;
            cursor: pointer;
        }
        
        .progress {
            height: 100%;
            background-color: #1db954;
            border-radius: 2px;
            width: 30%;
        }
        
        .control-buttons {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 25px;
        }
        
        .control-btn {
            background: none;
            border: none;
            color: #e0e0e0;
            font-size: 20px;
            cursor: pointer;
            transition: color 0.2s;
        }
        
        .control-btn:hover {
            color: #ffffff;
        }
        
        .control-btn.play-pause {
            background-color: #1db954;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 24px;
        }
        
        /* 播放列表区域 */
        .playlist-section {
            margin-top: 30px;
        }
        
        .section-title {
            font-size: 18px;
            margin-bottom: 15px;
            color: #ffffff;
            padding-bottom: 8px;
            border-bottom: 1px solid #333;
        }
        
        .playlist {
            list-style: none;
        }
        
        .playlist-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 15px;
            border-bottom: 1px solid #222;
            transition: background-color 0.2s;
        }
        
        .playlist-item:hover {
            background-color: #1a1a1a;
        }
        
        .song-info-small {
            display: flex;
            flex-direction: column;
        }
        
        .song-title-small {
            font-size: 14px;
            color: #e0e0e0;
        }
        
        .song-artist-small {
            font-size: 12px;
            color: #888;
        }
        
        .song-actions {
            display: flex;
            gap: 10px;
        }
        
        .action-btn {
            background: none;
            border: none;
            color: #888;
            cursor: pointer;
            font-size: 14px;
            transition: color 0.2s;
        }
        
        .action-btn:hover {
            color: #e0e0e0;
        }
        
        /* 重命名输入框样式 */
        .rename-input {
            background-color: #222;
            border: 1px solid #444;
            border-radius: 4px;
            color: #e0e0e0;
            padding: 8px 12px;
            font-size: 14px;
            width: 200px;
            transition: border-color 0.3s;
        }
        
        .rename-input:focus {
            outline: none;
            border-color: #1db954;
        }
        
        /* 弹窗样式 */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal {
            background-color: #1a1a1a;
            border-radius: 12px;
            width: 90%;
            max-width: 400px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            overflow: hidden;
        }
        
        .modal-header {
            padding: 20px;
            border-bottom: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .modal-title {
            font-size: 18px;
            color: #ffffff;
            font-weight: bold;
        }
        
        .modal-close {
            background: none;
            border: none;
            color: #888;
            font-size: 20px;
            cursor: pointer;
            transition: color 0.2s;
        }
        
        .modal-close:hover {
            color: #e0e0e0;
        }
        
        .modal-body {
            padding: 20px;
        }
        
        .modal-footer {
            padding: 15px 20px;
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            border-top: 1px solid #333;
        }
        
        .modal-btn {
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.2s;
        }
        
        .modal-btn.primary {
            background-color: #1db954;
            color: white;
        }
        
        .modal-btn.secondary {
            background-color: #333;
            color: #e0e0e0;
        }
        
        .modal-btn:hover {
            opacity: 0.9;
        }
        
        /* 隐藏类 */
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 顶部歌曲信息 -->
        <div class="song-info">
            <h1 class="song-title">黑色毛衣</h1>
            <p class="song-artist">赵乃吉</p>
        </div>
        
        <!-- 歌词区域 -->
        <div class="lyrics-container">
            <div class="lyrics-content">
                <div class="lyrics-line active">一件黑色毛衣</div>
                <div class="lyrics-line">两个人的回忆</div>
                <div class="lyrics-line">雨过之后更难忘记</div>
                <div class="lyrics-line">忘记我还爱你</div>
                <div class="lyrics-line">你不用在意</div>
                <div class="lyrics-line">流泪也只是刚好而已</div>
                <div class="lyrics-line">我早已经待在谷底</div>
            </div>
        </div>
        
        <!-- 播放控制区域 -->
        <div class="player-controls">
            <div class="progress-container">
                <span class="progress-time">1:23</span>
                <div class="progress-bar">
                    <div class="progress"></div>
                </div>
                <span class="progress-time">4:56</span>
            </div>
            
            <div class="control-buttons">
                <button class="control-btn">🔀</button>
                <button class="control-btn">⏮️</button>
                <button class="control-btn play-pause">▶️</button>
                <button class="control-btn">⏭️</button>
                <button class="control-btn">🔁</button>
            </div>
        </div>
        
        <!-- 播放列表 -->
        <div class="playlist-section">
            <h2 class="section-title">播放列表</h2>
            <ul class="playlist">
                <li class="playlist-item">
                    <div class="song-info-small">
                        <span class="song-title-small">黑色毛衣</span>
                        <span class="song-artist-small">赵乃吉</span>
                    </div>
                    <div class="song-actions">
                        <button class="action-btn rename-btn">重命名</button>
                        <button class="action-btn delete-btn">删除</button>
                    </div>
                </li>
                <li class="playlist-item">
                    <div class="song-info-small">
                        <span class="song-title-small">七里香</span>
                        <span class="song-artist-small">周杰伦</span>
                    </div>
                    <div class="song-actions">
                        <button class="action-btn rename-btn">重命名</button>
                        <button class="action-btn delete-btn">删除</button>
                    </div>
                </li>
                <li class="playlist-item">
                    <div class="song-info-small">
                        <span class="song-title-small">晴天</span>
                        <span class="song-artist-small">周杰伦</span>
                    </div>
                    <div class="song-actions">
                        <button class="action-btn rename-btn">重命名</button>
                        <button class="action-btn delete-btn">删除</button>
                    </div>
                </li>
            </ul>
        </div>
    </div>
    
    <!-- 重命名弹窗 -->
    <div class="modal-overlay rename-modal hidden">
        <div class="modal">
            <div class="modal-header">
                <h3 class="modal-title">重命名歌曲</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <input type="text" class="rename-input" value="黑色毛衣" placeholder="输入新名称">
            </div>
            <div class="modal-footer">
                <button class="modal-btn secondary cancel-btn">取消</button>
                <button class="modal-btn primary confirm-btn">确定</button>
            </div>
        </div>
    </div>
    
    <!-- 删除确认弹窗 -->
    <div class="modal-overlay delete-modal hidden">
        <div class="modal">
            <div class="modal-header">
                <h3 class="modal-title">删除歌曲</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <p>确定要删除这首歌曲吗？此操作不可撤销。</p>
            </div>
            <div class="modal-footer">
                <button class="modal-btn secondary cancel-btn">取消</button>
                <button class="modal-btn primary confirm-btn">确定</button>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // 模拟歌词高亮滚动
            const lyricsLines = document.querySelectorAll('.lyrics-line');
            let currentLine = 0;
            
            setInterval(() => {
                lyricsLines.forEach(line => line.classList.remove('active'));
                lyricsLines[currentLine].classList.add('active');
                currentLine = (currentLine + 1) % lyricsLines.length;
            }, 3000);
            
            // 播放/暂停按钮
            const playPauseBtn = document.querySelector('.play-pause');
            playPauseBtn.addEventListener('click', function() {
                if (this.textContent === '▶️') {
                    this.textContent = '⏸️';
                } else {
                    this.textContent = '▶️';
                }
            });
            
            // 重命名功能
            const renameButtons = document.querySelectorAll('.rename-btn');
            const renameModal = document.querySelector('.rename-modal');
            const renameInput = document.querySelector('.rename-input');
            let currentRenameItem = null;
            
            renameButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const listItem = this.closest('.playlist-item');
                    const songTitle = listItem.querySelector('.song-title-small').textContent;
                    renameInput.value = songTitle;
                    currentRenameItem = listItem;
                    renameModal.classList.remove('hidden');
                });
            });
            
            // 删除功能
            const deleteButtons = document.querySelectorAll('.delete-btn');
            const deleteModal = document.querySelector('.delete-modal');
            let currentDeleteItem = null;
            
            deleteButtons.forEach(button => {
                button.addEventListener('click', function() {
                    currentDeleteItem = this.closest('.playlist-item');
                    deleteModal.classList.remove('hidden');
                });
            });
            
            // 弹窗关闭功能
            const closeButtons = document.querySelectorAll('.modal-close, .cancel-btn');
            closeButtons.forEach(button => {
                button.addEventListener('click', function() {
                    renameModal.classList.add('hidden');
                    deleteModal.classList.add('hidden');
                });
            });
            
            // 重命名确认
            const renameConfirm = document.querySelector('.rename-modal .confirm-btn');
            renameConfirm.addEventListener('click', function() {
                if (currentRenameItem && renameInput.value.trim() !== '') {
                    currentRenameItem.querySelector('.song-title-small').textContent = renameInput.value;
                    renameModal.classList.add('hidden');
                }
            });
            
            // 删除确认
            const deleteConfirm = document.querySelector('.delete-modal .confirm-btn');
            deleteConfirm.addEventListener('click', function() {
                if (currentDeleteItem) {
                    currentDeleteItem.remove();
                    deleteModal.classList.add('hidden');
                }
            });
            
            // 点击弹窗外部关闭
            document.querySelectorAll('.modal-overlay').forEach(overlay => {
                overlay.addEventListener('click', function(e) {
                    if (e.target === this) {
                        this.classList.add('hidden');
                    }
                });
            });
        });
    </script>
</body>
</html>

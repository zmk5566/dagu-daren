# 环境安装指南

## 快速安装

### 1. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或者
venv\Scripts\activate  # Windows
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 启动服务器
```bash
python server.py
```

### 4. 访问游戏
打开浏览器访问: http://127.0.0.1:5001

## 可选依赖说明

### BeatNet (高级节拍检测)
BeatNet提供深度学习的节拍检测功能，如果不需要可以跳过：
```bash
# 如果安装BeatNet遇到问题，可以注释掉requirements.txt中的相关行
# torch>=2.0.0
# torchaudio>=2.0.0
# BeatNet>=1.0.0
```

### FFmpeg
需要FFmpeg来处理各种音频格式：

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
下载FFmpeg并添加到PATH，或使用conda：
```bash
conda install ffmpeg
```

## 故障排除

### 1. 音频处理错误
如果遇到音频处理错误，确保已安装FFmpeg和soundfile。

### 2. BeatNet安装失败
BeatNet依赖PyTorch，如果安装困难可以暂时跳过该功能。

### 3. 端口占用
如果5001端口被占用，可以修改server.py中的端口设置。

## 目录结构
```
├── server.py              # 主服务器
├── game_interface.html     # 游戏界面
├── game_styles.css         # 游戏样式
├── static/                # 静态文件（SVG图片等）
├── data/                  # 歌曲数据
├── audio_processor/       # 音频处理模块
└── annotation_tools/      # 标注工具
```
# Bilibili 视频转 MP3 指南

本指南记录了如何从 Bilibili 下载视频并将其转换为 MP3 格式的音频文件。

## 1. 安装依赖工具

你需要安装两个命令行工具：`you-get` 用于下载视频，`ffmpeg` 用于转换格式。

### 使用 Homebrew 安装 (推荐 macOS 用户)

如果你的电脑上没有 [Homebrew](https://brew.sh/)，请先安装它。然后执行以下命令：

```bash
brew install you-get ffmpeg
```

### 使用 pip 安装 (适用于 Python 环境)
```bash
pip3 install you-get
```

## 2. 下载视频并转换为 MP3

这个过程分为两步：先用 `you-get` 下载视频，然后用 `ffmpeg` 转换为 MP3。这正是我们刚才手动操作的流程。

**步骤一：使用 `you-get` 下载 Bilibili 视频**

打开终端，执行以下命令将视频下载到 `songs` 文件夹。

```bash
# --output-dir / -o: 指定输出目录
you-get -o songs "https://www.bilibili.com/video/BV14r4y1A7UF/"
```
这会将视频（通常是 .mp4 文件）保存在 `songs` 文件夹里。

**步骤二：将视频 MP4 转换为 MP3**

接下来，使用 `ffmpeg` 将下载好的视频文件转换为 MP3。

```bash
# 确保 mp3s 文件夹存在
mkdir -p songs/mp3s

# 执行转换
# 将 "songs/视频文件名.mp4" 替换成你下载的实际文件名
ffmpeg -i "songs/视频文件名.mp4" "songs/mp3s/音频文件名.mp3"
```

例如，我们刚才的操作是：
```bash
ffmpeg -i "songs/象王行.mp4" "songs/mp3s/象王行.mp3"
```
这样，转换好的 MP3 文件就会保存在 `songs/mp3s/` 文件夹内。

# 音频处理脚本

本目录包含用于处理项目音频文件的实用脚本。

## `create_backing_tracks.sh`

这是一个 Bash 脚本，用于从分离的音轨（如 bass, drums, vocals, other）自动生成三个版本的伴奏 MP3 文件。

### 功能

脚本会生成以下三种伴奏：
1.  **无鼓声伴奏** (`backing_track_no_drums.mp3`)
2.  **30% 音量鼓声伴奏** (`backing_track_low_drums.mp3`)
3.  **10% 音量鼓声伴奏** (`backing_track_10_percent_drums.mp3`)

生成的文件会被放置在输入目录下的 `generated_audio` 子目录中。

### 先决条件

- **ffmpeg**: 你必须安装 `ffmpeg` 才能运行此脚本。
  - 在 macOS 上，推荐使用 Homebrew 安装: `brew install ffmpeg`

### 使用方法

要运行此脚本，你需要给它提供一个包含音轨文件的目录路径作为参数。

**重要提示**: 脚本要求音轨文件遵循特定的命名规范：
- `<目录名> - bass.wav`
- `<目录名> - drums.wav`
- `<目录名> - other.wav`
- `<目录名> - vocals.wav`

**命令格式**:
```bash
bash scripts/create_backing_tracks.sh <音轨目录路径>
```

**示例**:
```bash
bash scripts/create_backing_tracks.sh data/xwx-backtrack-n-drum
```

脚本会首先检查 `ffmpeg` 是否存在，然后验证必需的音轨文件是否存在，最后生成音频文件。

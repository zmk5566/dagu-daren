#!/bin/bash

# 检查 ffmpeg 是否已安装
if ! command -v ffmpeg &> /dev/null
then
    echo "错误：ffmpeg 未安装。请先安装 ffmpeg。"
    echo "在 macOS 上，你可以使用 Homebrew: brew install ffmpeg"
    exit 1
fi

# 检查是否提供了目录参数
if [ -z "$1" ]; then
    echo "用法: $0 <包含音轨的目录路径>"
    echo "例如: $0 data/xwx-backtrack-n-drum"
    exit 1
fi

INPUT_DIR=$1
BASENAME=$(basename "$INPUT_DIR")
OUTPUT_DIR="$INPUT_DIR/generated_audio"

# 定义输入文件路径
BASS_FILE="$INPUT_DIR/$BASENAME - bass.wav"
OTHER_FILE="$INPUT_DIR/$BASENAME - other.wav"
VOCALS_FILE="$INPUT_DIR/$BASENAME - vocals.wav"
DRUMS_FILE="$INPUT_DIR/$BASENAME - drums.wav"

# 检查所有必需的 .wav 文件是否存在
for file in "$BASS_FILE" "$OTHER_FILE" "$VOCALS_FILE" "$DRUMS_FILE"; do
    if [ ! -f "$file" ]; then
        echo "错误：必需文件不存在: $file"
        exit 1
    fi
done

# 创建输出目录
mkdir -p "$OUTPUT_DIR"
echo "输出目录已创建: $OUTPUT_DIR"

# --- 生成音频文件 ---

echo "1. 正在生成无鼓声伴奏..."
ffmpeg -y -i "$BASS_FILE" -i "$OTHER_FILE" -i "$VOCALS_FILE" \
-filter_complex "[0:a][1:a][2:a]amerge=inputs=3[a]" \
-map "[a]" "$OUTPUT_DIR/backing_track_no_drums.mp3" > /dev/null 2>&1

echo "2. 正在生成 30% 音量鼓声伴奏..."
ffmpeg -y -i "$BASS_FILE" -i "$OTHER_FILE" -i "$VOCALS_FILE" -i "$DRUMS_FILE" \
-filter_complex "[3:a]volume=0.3[drums];[0:a][1:a][2:a][drums]amerge=inputs=4[a]" \
-map "[a]" "$OUTPUT_DIR/backing_track_low_drums.mp3" > /dev/null 2>&1

echo "3. 正在生成 10% 音量鼓声伴奏..."
ffmpeg -y -i "$BASS_FILE" -i "$OTHER_FILE" -i "$VOCALS_FILE" -i "$DRUMS_FILE" \
-filter_complex "[3:a]volume=0.1[drums];[0:a][1:a][2:a][drums]amerge=inputs=4[a]" \
-map "[a]" "$OUTPUT_DIR/backing_track_10_percent_drums.mp3" > /dev/null 2>&1

echo "4. 正在转换鼓声音轨为 MP3..."
ffmpeg -y -i "$DRUMS_FILE" "$OUTPUT_DIR/drums.mp3" > /dev/null 2>&1

echo "---"
echo "成功！所有音轨已生成在 $OUTPUT_DIR 目录下。"

#!/bin/bash
# Convert video sang WebP animation
# Usage: ./convert_to_webp.sh input.mp4 [quality]

INPUT="$1"
QUALITY="${2:-75}"  # Chất lượng 0-100, mặc định 75

if [ -z "$INPUT" ]; then
    echo "Usage: $0 <input_video.mp4> [quality 0-100]"
    echo "Example: $0 HTMTECH.mp4 80"
    exit 1
fi

if [ ! -f "$INPUT" ]; then
    echo "File không tồn tại: $INPUT"
    exit 1
fi

# Tên output
BASENAME=$(basename "$INPUT" | sed 's/\.[^.]*$//')
OUTPUT="${BASENAME}.webp"

echo "Converting $INPUT → $OUTPUT (quality: $QUALITY)"

# Convert với ffmpeg
ffmpeg -i "$INPUT" \
    -vcodec libwebp \
    -lossless 0 \
    -q:v "$QUALITY" \
    -loop 0 \
    -an \
    -vsync 0 \
    -y \
    "$OUTPUT"

if [ $? -eq 0 ]; then
    echo "✅ Đã tạo: $OUTPUT"
    ls -lh "$OUTPUT"
else
    echo "❌ Lỗi convert"
    exit 1
fi

#!/bin/bash
# =============================================================================
#            SMART C AI - LOG ROTATION SCRIPT
# =============================================================================
# Script này xoay vòng và dọn dẹp log files
# Chạy: bash scripts/logrotate.sh
# Hoặc thêm vào crontab: 0 0 * * * /home/digits/.digits/scripts/logrotate.sh
# =============================================================================

LOG_DIR="${HOME}/.digits/logs"
MAX_LOG_SIZE_MB=10
MAX_LOG_FILES=5
MAX_LOG_AGE_DAYS=7

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

# Tạo thư mục nếu chưa có
mkdir -p "$LOG_DIR"

log "🔄 Bắt đầu log rotation..."
log "📁 Log directory: $LOG_DIR"

# 1. Rotate các file log lớn
for logfile in "$LOG_DIR"/*.log; do
    [ -f "$logfile" ] || continue
    
    # Lấy kích thước file (MB)
    size=$(du -m "$logfile" 2>/dev/null | cut -f1)
    
    if [ "$size" -gt "$MAX_LOG_SIZE_MB" ]; then
        log "📦 Rotating $logfile ($size MB)"
        
        # Tạo backup với timestamp
        timestamp=$(date +%Y%m%d_%H%M%S)
        backup_file="${logfile}.${timestamp}"
        
        # Move và nén
        mv "$logfile" "$backup_file"
        gzip "$backup_file" 2>/dev/null || true
        
        # Tạo file log mới rỗng
        touch "$logfile"
        
        log "✓ Đã xoay: $logfile"
    fi
done

# 2. Xóa các file log backup cũ
log "🧹 Xóa log backups cũ hơn $MAX_LOG_AGE_DAYS ngày..."
find "$LOG_DIR" -name "*.log.*" -mtime +$MAX_LOG_AGE_DAYS -delete 2>/dev/null || true
find "$LOG_DIR" -name "*.log.*.gz" -mtime +$MAX_LOG_AGE_DAYS -delete 2>/dev/null || true

# 3. Giữ lại chỉ N file backup mới nhất
for logname in smartc application gui_display audio; do
    backups=$(ls -t "$LOG_DIR"/${logname}*.gz 2>/dev/null | tail -n +$((MAX_LOG_FILES+1)))
    if [ -n "$backups" ]; then
        echo "$backups" | xargs rm -f 2>/dev/null || true
        log "✓ Giữ lại $MAX_LOG_FILES backups mới nhất cho $logname"
    fi
done

# 4. Hiển thị tổng kết
total_size=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)
file_count=$(ls -1 "$LOG_DIR" 2>/dev/null | wc -l)

log "📊 Tổng kết:"
log "   - Số files: $file_count"
log "   - Tổng dung lượng: $total_size"
log "✅ Log rotation hoàn tất!"

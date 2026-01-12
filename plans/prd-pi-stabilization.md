# PRD: Smart C AI Pi Stabilization

## Problem Statement
Smart C AI Pi Assistant đang gặp các vấn đề ổn định:
1. GUI không hiển thị đúng (màn đen)
2. Video nền không chạy
3. Settings button không hoạt động
4. Không tạo desktop icon
5. Không fullscreen

## Goals
- ✅ Sửa tất cả lỗi GUI/Video
- ✅ Settings button hoạt động
- ✅ Desktop icon được tạo khi cài đặt
- ✅ Fullscreen mặc định
- ✅ Emotion hiển thị khi không có video

## Non-Goals
- Không thêm feature mới
- Không thay đổi logic business

## Issues Found

| # | Severity | Issue | File | Fix |
|---|----------|-------|------|-----|
| 1 | ❌ Critical | `_on_settings_button_click` reference `_video_worker` đã xóa | gui_display.py | ✅ Fixed |
| 2 | ❌ Critical | VideoBackgroundWidget import lỗi | settings_window.py | Check |
| 3 | ⚠️ Major | Không tạo desktop icon | install_oslite.sh | Add |
| 4 | ⚠️ Major | WINDOW_SIZE_MODE không đọc đúng | gui_display.py | Check |
| 5 | 💡 Minor | App icon không hiển thị | main.py | Check |

## Implementation Plan

### Phase 1: Fix Critical Bugs
1. Fix settings button (DONE)
2. Test VideoBackgroundWidget import
3. Verify QML loads correctly

### Phase 2: Add Desktop Icon
1. Create desktop entry in install script
2. Copy icon to ~/.local/share/icons

### Phase 3: Fix Fullscreen
1. Debug WINDOW_SIZE_MODE loading
2. Ensure fullscreen on startup

### Phase 4: Test & Verify
1. Test on Pi
2. Verify all features work

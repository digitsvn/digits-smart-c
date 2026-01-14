# Code Review Report: Local Dashboard Slideshow & Background Manager

## Overview
- **Date**: 2026-01-14
- **Reviewer**: Code Reviewer Agent
- **Feature**: Local & Cloud Slideshow Control
- **Status**: ✅ Approved (After Fixes)

## Summary
Đã review toàn bộ mã nguồn liên quan đến tính năng Slideshow mới trên Local Dashboard, Cloud Dashboard và Core Logic. Đã phát hiện và sửa một lỗi crash nghiêm trọng (Critical) trong logic chuyển đổi chế độ và vấn đề đồng bộ cấu hình Cloud.

## Files Reviewed
| File | Lines | Status |
|------|-------|--------|
| `src/display/gui_display.py` | ~1024 | ⚠️ Fixed Critical Bug |
| `src/network/web_settings.py` | ~3254 | ✅ Approved |
| `src/application.py` | ~720 | ✅ Approved (Config logic improved) |
| `cloud-server/index.js` | ~660 | ✅ Approved |
| `src/cloud/device_agent.py` | ~760 | ✅ Approved |

## Issues Found & Resolved

### 🚫 Blockers / ❌ Critical Issues
1. **`src/display/gui_display.py`:982** - `AttributeError: 'GuiDisplay' object has no attribute 'set_video_file'`
   - **Problem**: Logic chuyển đổi từ Slideshow sang Video gọi method không tồn tại (`set_video_file`). Điều này sẽ làm App bị crash ngay khi User chọn Video Mode.
   - **Fix Applied**: Đã thay thế bằng `self.display_model.update_video_file_path(path)`.

2. **`src/application.py`**: Config Key Mismatch
   - **Problem**: `Application` chỉ đọc `CLOUD.SERVER_URL` trong khi `WebSettings` lưu vào `SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL`. Dẫn đến Pi không tự kết nối Cloud nếu cấu hình qua Local Dashboard.
   - **Fix Applied**: Đã cập nhật `_start_cloud_agent` để ưu tiên đọc key từ WebSettings.

## 👍 Good Practices Found
- **Resource Management**: Logic clear video path (`update_video_file_path("")`) khi kích hoạt Slideshow giúp giải phóng tài nguyên hệ thống (tránh chạy ngầm video player).
- **Fallback Safe**: `_start_video_from_config` xử lý tốt các trường hợp config thiếu hoặc sai lệch giữa các version cũ/mới.
- **Secure Upload**: Cloud Server sử dụng `multer` với bộ lọc file image và giới hạn kích thước an toàn.

## Security Review
- [x] Input Validation: Filename sanitization implemented.
- [x] Auth: Cloud APIs protected. Local Dashboard open (by design for LAN).
- [x] Secrets: No hardcoded secrets exposed in logic (using env/config).

## Decision
**Verdict**: ✅ **APPROVED**
Mã nguồn đã sẵn sàng để merge/deploy. Các lỗi tìm thấy đã được tự động sửa.

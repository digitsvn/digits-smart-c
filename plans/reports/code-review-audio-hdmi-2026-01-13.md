# Code Review Report: HDMI Audio & Dependency System

## Overview
- **Date**: 2026-01-13
- **Reviewer**: Code Reviewer Agent
- **Commits**: 15 commits (debc27b → de15be5)
- **Status**: 🔄 CHANGES REQUESTED

## Summary

Session này tập trung vào việc implement:
1. **Dependency Checker** - Tự động cài đặt system dependencies
2. **HDMI Audio Output** - Phát TTS qua HDMI với aplay
3. **Audio Buffering** - Giảm giật với buffer mechanism

## Files Reviewed

| File | Lines | Status |
|------|-------|--------|
| `src/audio_codecs/audio_setup.py` | 237 | ⚠️ Needs cleanup |
| `src/utils/dependency_checker.py` | 340 | ✅ Good |
| `src/plugins/audio.py` | 178 | ✅ Good |
| `src/audio_codecs/audio_codec.py` | 1715 | ⚠️ Needs fixes |

---

## Issues Found

### ⚠️ Major Issues

#### 1. **audio_setup.py:92-127** - Dead code PulseAudio functions
- **Problem**: `restart_pulseaudio()`, `find_hdmi_sink()`, `set_default_sink()` không còn được sử dụng vì đã chuyển sang dùng aplay trực tiếp
- **Impact**: Code confusing, tăng maintenance burden
- **Suggestion**: Xóa hoặc comment out các functions không sử dụng

#### 2. **audio_codec.py:99** - Magic number threshold
- **Problem**: `_hdmi_write_threshold = 640` là magic number
- **Suggestion**: Di chuyển vào AudioConfig class với comment giải thích

#### 3. **audio_codec.py:573-575** - Complex condition
- **Problem**: Logic `should_write` phức tạp, khó đọc
- **Suggestion**: Extract thành method riêng `_should_write_buffer()`

#### 4. **audio_codec.py** - Missing reset of write_count
- **Problem**: `_hdmi_write_count` không được reset khi TTS mới bắt đầu
- **Impact**: Debug log chỉ hiển 3 writes đầu tiên của session, không phải mỗi TTS
- **Suggestion**: Reset `_hdmi_write_count = 0` khi bắt đầu TTS mới

### 💡 Minor Issues

#### 5. **dependency_checker.py:36** - Hardcoded package commented
- **Problem**: `libjack-dev` có thể không cần thiết cho mọi setup
- **Suggestion**: Làm optional hoặc xóa nếu không cần

#### 6. **audio.py:68** - Magic number sleep
- **Problem**: `await asyncio.sleep(0.8)` không giải thích tại sao 0.8s
- **Suggestion**: Extract thành constant `AUDIO_BUFFER_DRAIN_DELAY = 0.8`

#### 7. **audio_setup.py:1-14** - Docstring outdated
- **Problem**: Docstring vẫn mention "paplay qua PulseAudio" nhưng code đã chuyển sang aplay
- **Suggestion**: Update docstring phản ánh implementation hiện tại

---

## 🚫 Blockers (Production)

### 1. **Audio not working after changes**
- **Problem**: User báo audio mất sau các thay đổi buffer
- **Root cause**: Buffer threshold có thể không bao giờ đạt với decoded audio size
- **Impact**: Production unusable
- **Required action**: Test và fix trước khi deploy

---

## 👍 What's Good

1. **Dependency Checker well-structured** - Clean separation, good error handling
2. **Health check for aplay** - `_check_aplay_health()` prevents crashes
3. **Multiple device formats** - `_start_hdmi_aplay()` thử nhiều format đảm bảo compatibility
4. **Proper error logging** - Emoji và Vietnamese logging dễ debug
5. **Buffer flush on TTS end** - `_flush_hdmi_buffer()` đảm bảo không mất audio cuối

---

## Security Review

- [x] No hardcoded credentials
- [x] No SQL injection (không sử dụng SQL)
- [x] Subprocess calls use list format (safe from injection)
- [x] Timeout for all subprocess calls
- ⚠️ `sudo apt-get install` runs without password prompt - cần user có passwordless sudo

---

## Test Review

- **Test coverage**: ❌ Không có unit tests
- **Tests quality**: N/A
- **Manual testing**: User testing on Pi

---

## Decision

**Verdict**: 🔄 CHANGES REQUESTED

### Conditions for Approval:

1. ✅ **CRITICAL**: Sửa audio không hoạt động - phải test trên Pi và confirm working
2. Update docstring trong audio_setup.py
3. Xóa hoặc comment dead code PulseAudio functions

### Nice-to-have (không block production):
- Extract magic numbers
- Add unit tests
- Extract complex conditions

---

## Recommended Next Steps

1. **Immediate**: Test audio trên Pi, xác nhận hoạt động
2. **Short-term**: Cleanup dead code, update docstrings
3. **Medium-term**: Add configuration options cho buffer threshold
4. **Long-term**: Add unit tests cho audio module

---

## Appendix: Commit History

```
de15be5 fix: Giảm threshold và write ngay chunk đầu tiên
540ef4b fix: Buffer audio chunks trước khi write - giảm syscalls
b40cb99 fix: Bỏ buffer options, dùng aplay đơn giản
c42f15e fix: Dùng -B buffer time để giảm giật audio
ddfbbae fix: Giảm warmup buffer để không bị thiếu đầu audio
7e85e57 fix: Đợi audio buffer drain trước khi kết thúc playback
072a549 fix: Tăng buffer size để tránh audio ngắt quãng
c1b3f80 fix: Cải thiện HDMI detection và xóa package không có
fc1a2cf fix: Thử nhiều HDMI device formats để đảm bảo hoạt động
1093050 fix: Đơn giản hóa audio - bỏ PulseAudio, dùng aplay trực tiếp
e116eb5 feat: Thêm đầy đủ MIC và Video dependencies
35d1ab3 feat: Dependency Checker với đầy đủ dependencies
6acbc63 feat: Dependency Checker - tự động kiểm tra và cài đặt
b0ba1cf feat: Auto-install PulseAudio khi chưa có
debc27b feat: PulseAudio setup tự động
```

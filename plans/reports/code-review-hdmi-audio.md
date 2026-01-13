# Code Review Report: HDMI Audio & MIC Test Features

## Overview
- **Date**: 2026-01-13
- **Reviewer**: Code Reviewer Agent
- **Commits**: ab57d39 → c7fcff0 (15 commits)
- **Status**: 🔄 CHANGES REQUESTED

## Summary

Session này tập trung fix HDMI audio output và cải thiện MIC testing. HDMI đã hoạt động thành công qua aplay subprocess. Tuy nhiên còn một số vấn đề cần xử lý.

## Files Reviewed

| File | Lines Changed | Status |
|------|---------------|--------|
| `src/audio_codecs/audio_codec.py` | +150 | ⚠️ Needs cleanup |
| `src/network/web_settings.py` | +100 | ⚠️ Minor issues |
| `install_oslite.sh` | +5 | ✅ OK |
| `requirements-pi.txt` | +3 | ✅ OK |

## Issues Found

### ⚠️ Major Issues

#### 1. **audio_codec.py:302** - Bare except clause
- **Problem**: `except:` không specify exception type
- **Suggestion**: Sử dụng `except Exception:` hoặc specific exception
```python
# Current
except:
    pass

# Should be
except Exception as e:
    logger.warning(f"Set volume failed: {e}")
```

#### 2. **audio_codec.py:336** - stderr DEVNULL hides errors
- **Problem**: Khi aplay fail, không có log nào
- **Suggestion**: Capture stderr và log khi có lỗi
```python
stderr=subprocess.PIPE  # Instead of DEVNULL
# Then check process.stderr
```

#### 3. **web_settings.py:1943** - Bare except for aplay subprocess
- **Problem**: `except: pass` mất thông tin lỗi
- **Suggestion**: Log warning

### 💡 Minor Issues

#### 1. **audio_codec.py** - Duplicate subprocess imports
- **Problem**: `import subprocess` được gọi nhiều lần trong các method
- **Suggestion**: Di chuyển lên đầu file

#### 2. **web_settings.py:1947** - base64 import inside function
- **Problem**: Import inside function làm chậm
- **Suggestion**: Di chuyển lên đầu file

#### 3. **audio_codec.py:326** - Comment sai
- **Problem**: Comment nói "# 24000" nhưng có thể là 16000
- **Suggestion**: Xóa hardcoded comment, dùng `# AudioConfig.OUTPUT_SAMPLE_RATE`

### 📝 Suggestions

1. **Add timeout for aplay process**: Nếu aplay hang, app sẽ freeze
2. **Health check for aplay**: Kiểm tra process.poll() định kỳ
3. **Graceful fallback**: Nếu HDMI fail, fallback sang sounddevice

## 👍 What's Good

1. **Giải pháp aplay cho HDMI**: Thông minh, bypass sounddevice limitations
2. **Auto-detect ALSA card**: Tìm card name từ `aplay -l` - robust
3. **Browser audio playback**: Cho phép test MIC trên browser - rất tiện
4. **Config debug info**: Hiển thị config trong UI giúp debug
5. **Comprehensive logging**: Log đầy đủ các bước

## Security Review
- [x] No hardcoded credentials
- [x] subprocess calls use list format (safe from injection)
- [x] Input validation for config values

## Test Coverage
- **Manual testing**: Done on Pi
- **Unit tests**: None for new code
- **Status**: Needs automated tests

## Decision

**Verdict**: 🔄 CHANGES REQUESTED

**Conditions for Approval**:
1. Fix bare `except:` clauses
2. Add error logging for subprocess failures
3. Move imports to file top

**Next Steps**:
1. Clean up code issues above
2. Add unit tests for HDMI audio
3. Debug MIC amplitude issue (separate task)
4. Consider adding health monitoring for aplay process

---

## Commits Reviewed

| Commit | Description | Status |
|--------|-------------|--------|
| ab57d39 | fix: Detect đúng ALSA HDMI card | ✅ |
| 8fa0079 | feat: Nghe lại MIC trên Browser | ✅ |
| adcc4d9 | fix: Skip OutputStream khi dùng aplay | ✅ |
| 9ee3bc0 | fix: Test MIC dùng arecord/aplay | ⚠️ |
| 1598113 | feat: HDMI dùng aplay | ⚠️ |
| 9ce46ec | feat: Config Info debug | ✅ |
| 6b3102e | feat: Dependencies cho Beamforming | ✅ |
| 3fcd121 | fix: Auto set I2S MIC device | ✅ |
| 57dbfc0 | fix: Auto update output_device_id | ✅ |
| 785ea89 | feat: Cập nhật & Restart button | ✅ |


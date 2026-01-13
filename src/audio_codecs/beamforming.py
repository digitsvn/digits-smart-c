"""
Beamforming Processor - Xử lý tín hiệu từ dual microphone (INMP441 stereo)

Delay-and-Sum Beamforming:
- Sử dụng 2 mic để xác định hướng giọng nói
- Tập trung vào hướng phía trước (người dùng)
- Khử nhiễu từ hướng khác (loa, tiếng ồn)
"""

import numpy as np
from typing import Optional, Tuple
from collections import deque
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BeamformingProcessor:
    """
    Delay-and-Sum Beamforming cho dual INMP441 microphone.
    
    Giả định:
    - 2 mic đặt cách nhau khoảng 6-10cm
    - User ở phía trước (angle = 0°)
    - Loa ở phía sau hoặc góc khác
    """
    
    def __init__(
        self,
        mic_distance: float = 0.08,  # Khoảng cách giữa 2 mic (8cm default)
        sample_rate: int = 16000,
        sound_speed: float = 343.0,  # Vận tốc âm thanh (m/s)
        target_angle: float = 0.0,   # Góc target (0° = phía trước)
    ):
        self.mic_distance = mic_distance
        self.sample_rate = sample_rate
        self.sound_speed = sound_speed
        self.target_angle = target_angle
        
        # Tính toán delay tối đa (samples)
        self.max_delay_time = mic_distance / sound_speed
        self.max_delay_samples = int(self.max_delay_time * sample_rate) + 1
        
        # Buffer cho delay compensation
        self._left_buffer = deque(maxlen=self.max_delay_samples * 2)
        self._right_buffer = deque(maxlen=self.max_delay_samples * 2)
        
        # Adaptive parameters
        self._noise_floor = 100  # Initial noise floor estimate
        self._signal_energy = 0
        self._noise_energy = 0
        self._adaptation_rate = 0.01
        
        # Voice Activity Detection (VAD) state
        self._vad_threshold = 500
        self._is_voice_active = False
        self._voice_buffer = deque(maxlen=10)
        
        # Configuration
        self._enabled = True
        self._null_steering_enabled = True  # Null steering để khử loa
        self._adaptive_enabled = True
        
        logger.info(
            f"BeamformingProcessor initialized: "
            f"mic_distance={mic_distance}m, "
            f"max_delay={self.max_delay_samples} samples"
        )
    
    def set_target_angle(self, angle_degrees: float):
        """Set góc target (0° = phía trước, 90° = bên phải, -90° = bên trái)."""
        self.target_angle = np.radians(angle_degrees)
        logger.info(f"Target angle set to: {angle_degrees}°")
    
    def set_mic_distance(self, distance_cm: float):
        """Set khoảng cách giữa 2 mic (cm)."""
        self.mic_distance = distance_cm / 100.0
        self.max_delay_time = self.mic_distance / self.sound_speed
        self.max_delay_samples = int(self.max_delay_time * self.sample_rate) + 1
        logger.info(f"Mic distance set to: {distance_cm}cm")
    
    def _calculate_delay_samples(self, angle_rad: float) -> int:
        """
        Tính delay (samples) cho góc nhất định.
        
        Công thức: delay = d * sin(θ) / c
        Với:
        - d: khoảng cách mic
        - θ: góc tới
        - c: vận tốc âm thanh
        """
        delay_time = self.mic_distance * np.sin(angle_rad) / self.sound_speed
        return int(delay_time * self.sample_rate)
    
    def _estimate_doa(self, left: np.ndarray, right: np.ndarray) -> float:
        """
        Direction of Arrival (DOA) estimation using GCC-PHAT.
        
        Returns:
            Góc (radians) của nguồn âm thanh chính.
        """
        if len(left) < 64:
            return 0.0
        
        try:
            # Generalized Cross-Correlation with Phase Transform (GCC-PHAT)
            n = len(left)
            
            # Zero-padding for better resolution
            n_fft = 2 ** int(np.ceil(np.log2(n * 2)))
            
            # FFT
            left_fft = np.fft.rfft(left, n_fft)
            right_fft = np.fft.rfft(right, n_fft)
            
            # Cross-correlation với phase transform
            cross_spectrum = left_fft * np.conj(right_fft)
            
            # Normalize (PHAT weighting)
            magnitude = np.abs(cross_spectrum)
            magnitude[magnitude < 1e-10] = 1e-10
            cross_spectrum_normalized = cross_spectrum / magnitude
            
            # Inverse FFT
            correlation = np.fft.irfft(cross_spectrum_normalized, n_fft)
            
            # Tìm peak trong range delay hợp lệ
            search_range = min(self.max_delay_samples, n_fft // 4)
            
            # Xem xét cả delay dương và âm
            positive_delays = correlation[:search_range]
            negative_delays = correlation[-search_range:]
            
            peak_pos = np.argmax(positive_delays)
            peak_neg = np.argmax(negative_delays)
            
            if positive_delays[peak_pos] > negative_delays[peak_neg]:
                delay_samples = peak_pos
            else:
                delay_samples = -(search_range - peak_neg)
            
            # Chuyển delay thành góc
            if abs(delay_samples) < 1:
                return 0.0
            
            delay_time = delay_samples / self.sample_rate
            sin_angle = np.clip(
                delay_time * self.sound_speed / self.mic_distance,
                -1.0, 1.0
            )
            angle = np.arcsin(sin_angle)
            
            return angle
            
        except Exception as e:
            logger.warning(f"DOA estimation failed: {e}")
            return 0.0
    
    def _apply_delay_and_sum(
        self,
        left: np.ndarray,
        right: np.ndarray,
        steer_angle: float
    ) -> np.ndarray:
        """
        Apply delay-and-sum beamforming.
        
        Args:
            left: Left channel
            right: Right channel
            steer_angle: Góc steering (radians)
        
        Returns:
            Beamformed output (mono)
        """
        delay_samples = self._calculate_delay_samples(steer_angle)
        
        if delay_samples == 0:
            # No delay needed, simple sum
            return ((left.astype(np.float32) + right.astype(np.float32)) / 2).astype(np.int16)
        
        n = len(left)
        
        if delay_samples > 0:
            # Delay left channel
            left_delayed = np.zeros(n, dtype=np.float32)
            if delay_samples < n:
                left_delayed[delay_samples:] = left[:-delay_samples].astype(np.float32)
            output = (left_delayed + right.astype(np.float32)) / 2
        else:
            # Delay right channel
            delay_samples = abs(delay_samples)
            right_delayed = np.zeros(n, dtype=np.float32)
            if delay_samples < n:
                right_delayed[delay_samples:] = right[:-delay_samples].astype(np.float32)
            output = (left.astype(np.float32) + right_delayed) / 2
        
        return output.astype(np.int16)
    
    def _apply_null_steering(
        self,
        left: np.ndarray,
        right: np.ndarray,
        null_angle: float,
        strength: float = 0.8
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Null steering - giảm tín hiệu từ hướng nhất định (ví dụ: loa).
        
        Args:
            left, right: Stereo channels
            null_angle: Góc cần khử (radians)
            strength: Độ mạnh của null (0-1)
        
        Returns:
            Modified left, right channels
        """
        delay_samples = self._calculate_delay_samples(null_angle)
        
        if abs(delay_samples) < 1:
            return left, right
        
        n = len(left)
        left_f = left.astype(np.float32)
        right_f = right.astype(np.float32)
        
        if delay_samples > 0 and delay_samples < n:
            # Trừ phiên bản shifted của left khỏi right
            subtraction = np.zeros(n, dtype=np.float32)
            subtraction[delay_samples:] = left_f[:-delay_samples]
            right_f = right_f - strength * subtraction
        elif delay_samples < 0:
            delay_samples = abs(delay_samples)
            if delay_samples < n:
                subtraction = np.zeros(n, dtype=np.float32)
                subtraction[delay_samples:] = right_f[:-delay_samples]
                left_f = left_f - strength * subtraction
        
        return left_f.astype(np.int16), right_f.astype(np.int16)
    
    def _voice_activity_detection(self, audio: np.ndarray) -> bool:
        """
        Simple Voice Activity Detection (VAD).
        """
        energy = np.mean(np.abs(audio.astype(np.float32)))
        self._voice_buffer.append(energy)
        
        avg_energy = np.mean(list(self._voice_buffer))
        
        # Adaptive threshold
        if self._adaptive_enabled:
            if not self._is_voice_active:
                # Update noise floor khi không có voice
                self._noise_floor = (
                    0.95 * self._noise_floor + 
                    0.05 * avg_energy
                )
            
            threshold = max(self._vad_threshold, self._noise_floor * 3)
        else:
            threshold = self._vad_threshold
        
        self._is_voice_active = avg_energy > threshold
        return self._is_voice_active
    
    def process(
        self,
        stereo_audio: np.ndarray,
        speaker_angle: float = 180.0  # Loa ở phía sau (180°)
    ) -> np.ndarray:
        """
        Process stereo audio với beamforming.
        
        Args:
            stereo_audio: Shape (n_samples, 2) hoặc interleaved (n_samples*2,)
            speaker_angle: Góc của loa (để null steering)
        
        Returns:
            Mono audio sau beamforming
        """
        if not self._enabled:
            # Simple average nếu disabled
            if len(stereo_audio.shape) == 2:
                return np.mean(stereo_audio, axis=1).astype(np.int16)
            else:
                left = stereo_audio[::2]
                right = stereo_audio[1::2]
                return ((left.astype(np.float32) + right.astype(np.float32)) / 2).astype(np.int16)
        
        # Parse stereo channels
        if len(stereo_audio.shape) == 2 and stereo_audio.shape[1] == 2:
            left = stereo_audio[:, 0].astype(np.int16)
            right = stereo_audio[:, 1].astype(np.int16)
        elif len(stereo_audio.shape) == 1 and len(stereo_audio) % 2 == 0:
            # Interleaved
            left = stereo_audio[::2].astype(np.int16)
            right = stereo_audio[1::2].astype(np.int16)
        else:
            logger.warning(f"Invalid stereo shape: {stereo_audio.shape}")
            return stereo_audio.flatten().astype(np.int16)
        
        # 1. Null steering: Giảm tín hiệu từ hướng loa
        if self._null_steering_enabled:
            speaker_rad = np.radians(speaker_angle)
            left, right = self._apply_null_steering(left, right, speaker_rad, strength=0.7)
        
        # 2. DOA estimation (chỉ khi có voice activity)
        if self._voice_activity_detection(left + right):
            estimated_angle = self._estimate_doa(left, right)
            
            # Sử dụng góc ước lượng nếu gần target, ngược lại dùng target
            if abs(estimated_angle - self.target_angle) < np.radians(45):
                steer_angle = estimated_angle
            else:
                steer_angle = self.target_angle
        else:
            steer_angle = self.target_angle
        
        # 3. Delay-and-sum beamforming hướng về target
        output = self._apply_delay_and_sum(left, right, steer_angle)
        
        return output
    
    def get_status(self) -> dict:
        """Lấy trạng thái processor."""
        return {
            "enabled": self._enabled,
            "mic_distance_cm": self.mic_distance * 100,
            "target_angle_deg": np.degrees(self.target_angle),
            "max_delay_samples": self.max_delay_samples,
            "null_steering": self._null_steering_enabled,
            "adaptive": self._adaptive_enabled,
            "is_voice_active": self._is_voice_active,
            "noise_floor": self._noise_floor,
        }
    
    def enable(self, enabled: bool = True):
        """Enable/disable beamforming."""
        self._enabled = enabled
        logger.info(f"Beamforming {'enabled' if enabled else 'disabled'}")
    
    def enable_null_steering(self, enabled: bool = True):
        """Enable/disable null steering (speaker cancellation)."""
        self._null_steering_enabled = enabled
        logger.info(f"Null steering {'enabled' if enabled else 'disabled'}")

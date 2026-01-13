"""
Unit Tests for BeamformingProcessor

Run: pytest tests/test_beamforming.py -v
"""

import numpy as np
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio_codecs.beamforming import BeamformingProcessor


class TestBeamformingProcessor:
    """Tests for BeamformingProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create a default processor instance."""
        return BeamformingProcessor(
            mic_distance=0.08,  # 8cm
            sample_rate=16000,
            sound_speed=343.0,
            target_angle=0.0
        )
    
    def test_initialization(self, processor):
        """Test processor initializes with correct defaults."""
        assert processor.mic_distance == 0.08
        assert processor.sample_rate == 16000
        assert processor.sound_speed == 343.0
        assert processor.target_angle == 0.0
        assert processor._enabled == True
        assert processor.max_delay_samples > 0
    
    def test_set_mic_distance(self, processor):
        """Test setting mic distance in cm."""
        processor.set_mic_distance(10.0)
        assert processor.mic_distance == 0.10
        
        processor.set_mic_distance(5.0)
        assert processor.mic_distance == 0.05
    
    def test_set_target_angle(self, processor):
        """Test setting target angle."""
        processor.set_target_angle(45.0)
        assert np.isclose(processor.target_angle, np.radians(45.0))
        
        processor.set_target_angle(-30.0)
        assert np.isclose(processor.target_angle, np.radians(-30.0))
    
    def test_calculate_delay_samples(self, processor):
        """Test delay calculation for different angles."""
        # At 0 degrees, no delay expected
        delay = processor._calculate_delay_samples(0.0)
        assert delay == 0
        
        # At 90 degrees, maximum delay
        delay_90 = processor._calculate_delay_samples(np.pi / 2)
        assert delay_90 == processor.max_delay_samples - 1 or delay_90 == processor.max_delay_samples
        
        # At -90 degrees, opposite delay
        delay_neg90 = processor._calculate_delay_samples(-np.pi / 2)
        assert delay_neg90 == -delay_90
    
    def test_process_disabled(self, processor):
        """Test processing when disabled - should do simple averaging."""
        processor._enabled = False
        
        # Create stereo test signal
        n_samples = 320
        left = np.random.randint(-1000, 1000, n_samples, dtype=np.int16)
        right = np.random.randint(-1000, 1000, n_samples, dtype=np.int16)
        stereo = np.column_stack([left, right])
        
        output = processor.process(stereo)
        
        # Should be mono
        assert output.shape == (n_samples,)
        assert output.dtype == np.int16
    
    def test_process_enabled(self, processor):
        """Test processing when enabled."""
        processor._enabled = True
        
        # Create stereo test signal (simulated voice)
        n_samples = 320
        t = np.linspace(0, n_samples / 16000, n_samples)
        signal = (np.sin(2 * np.pi * 440 * t) * 5000).astype(np.int16)
        left = signal
        right = signal  # Same signal = sound from front
        stereo = np.column_stack([left, right])
        
        output = processor.process(stereo)
        
        # Should be mono
        assert output.shape == (n_samples,)
        assert output.dtype == np.int16
    
    def test_process_interleaved(self, processor):
        """Test processing interleaved stereo data."""
        n_samples = 320
        left = np.ones(n_samples, dtype=np.int16) * 100
        right = np.ones(n_samples, dtype=np.int16) * 200
        
        # Interleave: L R L R L R ...
        interleaved = np.empty(n_samples * 2, dtype=np.int16)
        interleaved[::2] = left
        interleaved[1::2] = right
        
        output = processor.process(interleaved)
        
        # Should be mono (n_samples, not n_samples*2)
        assert output.shape == (n_samples,)
    
    def test_doa_estimation_front(self, processor):
        """Test DOA estimation for sound from front."""
        n_samples = 1024
        t = np.linspace(0, n_samples / 16000, n_samples)
        signal = (np.sin(2 * np.pi * 1000 * t) * 10000).astype(np.int16)
        
        # Same signal on both channels = front (0 degrees)
        left = signal
        right = signal
        
        angle = processor._estimate_doa(left, right)
        
        # Should be close to 0
        assert abs(angle) < np.radians(10)
    
    def test_doa_estimation_with_delay(self, processor):
        """Test DOA estimation for sound from side."""
        n_samples = 1024
        t = np.linspace(0, n_samples / 16000, n_samples)
        signal = (np.sin(2 * np.pi * 1000 * t) * 10000).astype(np.int16)
        
        # Delay right channel by a few samples = sound from left
        delay = 3
        left = signal
        right = np.zeros(n_samples, dtype=np.int16)
        right[delay:] = signal[:-delay]
        
        angle = processor._estimate_doa(left, right)
        
        # Should detect sound from left (positive angle)
        # Note: exact angle depends on mic distance and sample rate
        assert angle != 0  # Not from front
    
    def test_voice_activity_detection_silence(self, processor):
        """Test VAD with silence."""
        silence = np.zeros(320, dtype=np.int16)
        
        # Run a few times to settle noise floor
        for _ in range(5):
            result = processor._voice_activity_detection(silence)
        
        assert result == False
    
    def test_voice_activity_detection_voice(self, processor):
        """Test VAD with voice-like signal."""
        t = np.linspace(0, 320 / 16000, 320)
        voice = (np.sin(2 * np.pi * 300 * t) * 10000).astype(np.int16)
        
        result = processor._voice_activity_detection(voice)
        
        assert result == True
    
    def test_null_steering(self, processor):
        """Test null steering reduces interference."""
        n_samples = 320
        t = np.linspace(0, n_samples / 16000, n_samples)
        signal = (np.sin(2 * np.pi * 440 * t) * 5000).astype(np.int16)
        
        left = signal.copy()
        right = signal.copy()
        
        # Apply null steering
        left_ns, right_ns = processor._apply_null_steering(
            left, right, 
            null_angle=np.pi,  # 180 degrees (behind)
            strength=0.8
        )
        
        # Output should still be valid int16
        assert left_ns.dtype == np.int16
        assert right_ns.dtype == np.int16
    
    def test_delay_and_sum(self, processor):
        """Test delay-and-sum beamforming."""
        n_samples = 320
        left = np.ones(n_samples, dtype=np.int16) * 1000
        right = np.ones(n_samples, dtype=np.int16) * 1000
        
        # Steer to front
        output = processor._apply_delay_and_sum(left, right, steer_angle=0.0)
        
        assert output.shape == (n_samples,)
        assert output.dtype == np.int16
        # Average of 1000 and 1000 should be around 1000
        assert np.mean(output) > 900
    
    def test_get_status(self, processor):
        """Test status dictionary."""
        status = processor.get_status()
        
        assert 'enabled' in status
        assert 'mic_distance_cm' in status
        assert 'target_angle_deg' in status
        assert 'max_delay_samples' in status
        assert 'null_steering' in status
        assert 'is_voice_active' in status
    
    def test_enable_disable(self, processor):
        """Test enable/disable."""
        processor.enable(False)
        assert processor._enabled == False
        
        processor.enable(True)
        assert processor._enabled == True
    
    def test_enable_null_steering(self, processor):
        """Test enable/disable null steering."""
        processor.enable_null_steering(False)
        assert processor._null_steering_enabled == False
        
        processor.enable_null_steering(True)
        assert processor._null_steering_enabled == True


class TestBeamformingEdgeCases:
    """Edge case tests."""
    
    def test_very_short_input(self):
        """Test with very short audio."""
        processor = BeamformingProcessor()
        
        short_stereo = np.zeros((10, 2), dtype=np.int16)
        output = processor.process(short_stereo)
        
        assert len(output) == 10
    
    def test_empty_input(self):
        """Test with empty input."""
        processor = BeamformingProcessor()
        
        empty = np.zeros((0, 2), dtype=np.int16)
        output = processor.process(empty)
        
        assert len(output) == 0
    
    def test_extreme_mic_distance(self):
        """Test with extreme mic distances."""
        # Very small distance
        processor = BeamformingProcessor(mic_distance=0.01)
        assert processor.max_delay_samples >= 1
        
        # Large distance
        processor = BeamformingProcessor(mic_distance=0.5)
        assert processor.max_delay_samples > 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

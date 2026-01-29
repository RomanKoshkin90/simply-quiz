"""
Audio preprocessing module.
Handles loading, resampling, normalization, and vocal isolation.
"""
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import Tuple, Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class AudioPreprocessor:
    """
    Audio preprocessing pipeline for voice analysis.
    """
    
    def __init__(
        self,
        target_sr: int = None,
        max_duration: int = None,
    ):
        self.target_sr = target_sr or settings.target_sample_rate
        self.max_duration = max_duration or settings.max_audio_duration_seconds
    
    def load_audio(self, file_path: str | Path) -> Tuple[np.ndarray, int]:
        """
        Load audio file and convert to mono.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        logger.info(f"Loading audio file: {file_path}")
        
        # Load with librosa (handles various formats)
        audio, sr = librosa.load(
            str(file_path),
            sr=None,  # Keep original sample rate initially
            mono=True,  # Convert to mono
        )
        
        # Check duration
        duration = len(audio) / sr
        if duration > self.max_duration:
            logger.warning(
                f"Audio duration ({duration:.1f}s) exceeds max ({self.max_duration}s). Truncating."
            )
            audio = audio[: int(self.max_duration * sr)]
        
        logger.info(f"Loaded audio: {duration:.2f}s, {sr}Hz")
        return audio, sr
    
    def resample(
        self, 
        audio: np.ndarray, 
        orig_sr: int, 
        target_sr: int = None
    ) -> np.ndarray:
        """
        Resample audio to target sample rate.
        
        Args:
            audio: Audio array
            orig_sr: Original sample rate
            target_sr: Target sample rate (default: from settings)
            
        Returns:
            Resampled audio array
        """
        target_sr = target_sr or self.target_sr
        
        if orig_sr == target_sr:
            return audio
        
        logger.info(f"Resampling from {orig_sr}Hz to {target_sr}Hz")
        return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
    
    def normalize(self, audio: np.ndarray) -> np.ndarray:
        """
        Normalize audio to [-1, 1] range.
        
        Args:
            audio: Audio array
            
        Returns:
            Normalized audio array
        """
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            return audio / max_val
        return audio
    
    def remove_silence(
        self, 
        audio: np.ndarray, 
        sr: int,
        top_db: int = 30,
        frame_length: int = 2048,
        hop_length: int = 512,
    ) -> np.ndarray:
        """
        Remove leading and trailing silence from audio.
        
        Args:
            audio: Audio array
            sr: Sample rate
            top_db: Threshold below reference for silence detection
            
        Returns:
            Audio with silence removed
        """
        # Get non-silent intervals
        intervals = librosa.effects.split(
            audio, 
            top_db=top_db,
            frame_length=frame_length,
            hop_length=hop_length,
        )
        
        if len(intervals) == 0:
            logger.warning("No non-silent segments found")
            return audio
        
        # Concatenate non-silent parts
        non_silent = np.concatenate([audio[start:end] for start, end in intervals])
        
        logger.info(
            f"Removed silence: {len(audio)/sr:.2f}s -> {len(non_silent)/sr:.2f}s"
        )
        return non_silent
    
    def apply_high_pass_filter(
        self, 
        audio: np.ndarray, 
        sr: int, 
        cutoff_hz: int = 80
    ) -> np.ndarray:
        """
        Apply high-pass filter to remove low-frequency noise.
        
        Args:
            audio: Audio array
            sr: Sample rate
            cutoff_hz: Cutoff frequency in Hz
            
        Returns:
            Filtered audio
        """
        from scipy.signal import butter, sosfilt
        
        # Design butterworth high-pass filter
        sos = butter(5, cutoff_hz, btype='high', fs=sr, output='sos')
        filtered = sosfilt(sos, audio)
        
        return filtered.astype(np.float32)
    
    def preprocess(
        self, 
        file_path: str | Path,
        remove_silence_flag: bool = True,
        apply_filter: bool = True,
    ) -> Tuple[np.ndarray, int, float]:
        """
        Full preprocessing pipeline.
        
        Args:
            file_path: Path to audio file
            remove_silence_flag: Whether to remove silence
            apply_filter: Whether to apply high-pass filter
            
        Returns:
            Tuple of (processed_audio, sample_rate, original_duration)
        """
        # Load
        audio, orig_sr = self.load_audio(file_path)
        original_duration = len(audio) / orig_sr
        
        # Resample
        audio = self.resample(audio, orig_sr, self.target_sr)
        
        # Remove silence
        if remove_silence_flag:
            audio = self.remove_silence(audio, self.target_sr)
        
        # Apply high-pass filter
        if apply_filter:
            audio = self.apply_high_pass_filter(audio, self.target_sr)
        
        # Normalize
        audio = self.normalize(audio)
        
        logger.info(
            f"Preprocessing complete: {original_duration:.2f}s original, "
            f"{len(audio)/self.target_sr:.2f}s processed"
        )
        
        return audio, self.target_sr, original_duration
    
    def save_processed(
        self, 
        audio: np.ndarray, 
        sr: int, 
        output_path: str | Path
    ) -> Path:
        """
        Save processed audio to file.
        
        Args:
            audio: Processed audio array
            sr: Sample rate
            output_path: Output file path
            
        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        sf.write(str(output_path), audio, sr)
        logger.info(f"Saved processed audio to: {output_path}")
        
        return output_path


# Module-level instance for convenience
preprocessor = AudioPreprocessor()

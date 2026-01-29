"""
Pitch extraction module using CREPE.
Extracts fundamental frequency (F0) and vocal range analysis.
"""
import numpy as np
import crepe
from typing import Tuple, Optional, NamedTuple
import logging

from app.config import settings

logger = logging.getLogger(__name__)


# Voice type classification based on pitch range (in Hz)
VOICE_TYPES = {
    "bass": (80, 350),      # E2 - E4
    "baritone": (100, 400), # G2 - G4
    "tenor": (130, 520),    # C3 - C5
    "alto": (175, 700),     # F3 - F5
    "mezzo-soprano": (200, 880),  # G3 - A5
    "soprano": (260, 1050), # C4 - C6
}


class PitchResult(NamedTuple):
    """Result container for pitch extraction."""
    time: np.ndarray          # Time stamps
    frequency: np.ndarray     # F0 frequency in Hz
    confidence: np.ndarray    # Prediction confidence
    activation: np.ndarray    # Raw network activation


class PitchAnalysisResult(NamedTuple):
    """Analyzed pitch statistics."""
    min_pitch_hz: float
    max_pitch_hz: float
    median_pitch_hz: float
    mean_pitch_hz: float
    std_pitch_hz: float
    pitch_range_hz: float
    octave_range: float
    voiced_ratio: float
    detected_voice_type: Optional[str]
    min_pitch_note: str
    max_pitch_note: str


class PitchExtractor:
    """
    CREPE-based pitch extraction and analysis.
    """
    
    def __init__(
        self,
        model_capacity: str = None,
        step_size: int = None,
        confidence_threshold: float = 0.5,
    ):
        """
        Initialize pitch extractor.
        
        Args:
            model_capacity: CREPE model size (tiny, small, medium, large, full)
            step_size: Step size in milliseconds
            confidence_threshold: Minimum confidence for valid pitch
        """
        self.model_capacity = model_capacity or settings.crepe_model_capacity
        self.step_size = step_size or settings.crepe_step_size
        self.confidence_threshold = confidence_threshold
    
    def extract_pitch(
        self, 
        audio: np.ndarray, 
        sr: int,
        viterbi: bool = True,
    ) -> PitchResult:
        """
        Extract pitch using CREPE.
        
        Args:
            audio: Audio array (mono)
            sr: Sample rate
            viterbi: Use Viterbi decoding for smoother pitch
            
        Returns:
            PitchResult with time, frequency, confidence, activation
        """
        logger.info(
            f"Extracting pitch with CREPE ({self.model_capacity}, step={self.step_size}ms)"
        )
        
        # Run CREPE prediction
        time, frequency, confidence, activation = crepe.predict(
            audio,
            sr,
            model_capacity=self.model_capacity,
            step_size=self.step_size,
            viterbi=viterbi,
            verbose=0,  # Suppress progress bar
        )
        
        logger.info(f"Extracted {len(time)} pitch frames")
        
        return PitchResult(
            time=time,
            frequency=frequency,
            confidence=confidence,
            activation=activation,
        )
    
    def analyze_pitch(self, pitch_result: PitchResult) -> PitchAnalysisResult:
        """
        Analyze extracted pitch for vocal range statistics.
        
        Args:
            pitch_result: Raw pitch extraction result
            
        Returns:
            PitchAnalysisResult with statistics and classification
        """
        frequency = pitch_result.frequency
        confidence = pitch_result.confidence
        
        # Filter by confidence threshold
        voiced_mask = confidence >= self.confidence_threshold
        voiced_ratio = np.mean(voiced_mask)
        
        if voiced_ratio < 0.1:
            logger.warning(f"Low voiced ratio: {voiced_ratio:.2%}")
        
        # Get voiced frequencies only
        voiced_frequencies = frequency[voiced_mask]
        
        if len(voiced_frequencies) == 0:
            raise ValueError("No voiced segments detected above confidence threshold")
        
        # Filter out extreme values (likely errors)
        # Human voice typically 80-1100 Hz
        valid_mask = (voiced_frequencies >= 60) & (voiced_frequencies <= 1200)
        valid_frequencies = voiced_frequencies[valid_mask]
        
        if len(valid_frequencies) == 0:
            valid_frequencies = voiced_frequencies
        
        # Calculate statistics
        min_pitch = float(np.percentile(valid_frequencies, 5))   # 5th percentile
        max_pitch = float(np.percentile(valid_frequencies, 95))  # 95th percentile
        median_pitch = float(np.median(valid_frequencies))
        mean_pitch = float(np.mean(valid_frequencies))
        std_pitch = float(np.std(valid_frequencies))
        pitch_range = max_pitch - min_pitch
        
        # Calculate octave range: log2(max/min)
        octave_range = np.log2(max_pitch / min_pitch) if min_pitch > 0 else 0
        
        # Classify voice type
        voice_type = self._classify_voice_type(min_pitch, max_pitch, median_pitch)
        
        # Convert to musical notes
        min_note = self._hz_to_note(min_pitch)
        max_note = self._hz_to_note(max_pitch)
        
        logger.info(
            f"Pitch analysis: {min_note} ({min_pitch:.1f}Hz) - "
            f"{max_note} ({max_pitch:.1f}Hz), {octave_range:.2f} octaves, "
            f"type: {voice_type}"
        )
        
        return PitchAnalysisResult(
            min_pitch_hz=min_pitch,
            max_pitch_hz=max_pitch,
            median_pitch_hz=median_pitch,
            mean_pitch_hz=mean_pitch,
            std_pitch_hz=std_pitch,
            pitch_range_hz=pitch_range,
            octave_range=octave_range,
            voiced_ratio=voiced_ratio,
            detected_voice_type=voice_type,
            min_pitch_note=min_note,
            max_pitch_note=max_note,
        )
    
    def _classify_voice_type(
        self, 
        min_pitch: float, 
        max_pitch: float, 
        median_pitch: float
    ) -> Optional[str]:
        """
        Classify voice type based on pitch range.
        
        Uses median pitch as primary indicator, with range as secondary.
        """
        best_match = None
        best_score = 0
        
        for voice_type, (type_min, type_max) in VOICE_TYPES.items():
            type_median = (type_min + type_max) / 2
            
            # Score based on how well median fits the type
            if type_min <= median_pitch <= type_max:
                # Distance from center of range (normalized)
                distance = abs(median_pitch - type_median) / (type_max - type_min)
                score = 1 - distance
                
                # Bonus if range overlaps well
                overlap = min(max_pitch, type_max) - max(min_pitch, type_min)
                if overlap > 0:
                    score += 0.2
                
                if score > best_score:
                    best_score = score
                    best_match = voice_type
        
        return best_match
    
    @staticmethod
    def _hz_to_note(frequency: float) -> str:
        """
        Convert frequency in Hz to musical note name.
        
        Args:
            frequency: Frequency in Hz
            
        Returns:
            Note name (e.g., "C4", "A#3")
        """
        if frequency <= 0:
            return "N/A"
        
        # A4 = 440 Hz
        A4 = 440.0
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        # Calculate semitones from A4
        semitones_from_a4 = 12 * np.log2(frequency / A4)
        
        # A4 is the 9th note in octave 4 (0-indexed from C)
        total_semitones = int(round(semitones_from_a4)) + 9 + (4 * 12)
        
        octave = total_semitones // 12
        note_index = total_semitones % 12
        
        return f"{notes[note_index]}{octave}"
    
    @staticmethod
    def hz_to_midi(frequency: float) -> int:
        """Convert Hz to MIDI note number."""
        if frequency <= 0:
            return 0
        return int(round(69 + 12 * np.log2(frequency / 440.0)))
    
    @staticmethod
    def midi_to_hz(midi_note: int) -> float:
        """Convert MIDI note number to Hz."""
        return 440.0 * (2 ** ((midi_note - 69) / 12))


# Module-level instance
pitch_extractor = PitchExtractor()

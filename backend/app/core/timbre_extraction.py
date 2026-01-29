"""
Timbre/acoustic feature extraction using OpenSMILE.
Extracts eGeMAPS features for voice characterization.
"""
import numpy as np
import opensmile
from typing import Dict, Optional, Any
from pathlib import Path
import tempfile
import soundfile as sf
import logging

from app.config import settings

logger = logging.getLogger(__name__)


# Key eGeMAPS features for voice analysis
KEY_FEATURES = [
    # Frequency features
    'F0semitoneFrom27.5Hz_sma3nz_amean',
    'F0semitoneFrom27.5Hz_sma3nz_stddevNorm',
    'jitterLocal_sma3nz_amean',
    'shimmerLocaldB_sma3nz_amean',
    
    # Formants
    'F1frequency_sma3nz_amean',
    'F2frequency_sma3nz_amean',
    'F3frequency_sma3nz_amean',
    
    # Energy/loudness
    'loudness_sma3_amean',
    'loudness_sma3_stddevNorm',
    
    # Spectral
    'spectralFlux_sma3_amean',
    'HNRdBACF_sma3nz_amean',
    
    # Voice quality
    'logRelF0-H1-H2_sma3nz_amean',
    'logRelF0-H1-A3_sma3nz_amean',
]


class TimbreExtractor:
    """
    OpenSMILE-based timbre feature extraction.
    Uses eGeMAPS feature set optimized for voice analysis.
    """
    
    def __init__(
        self,
        feature_set: str = None,
        feature_level: str = None,
    ):
        """
        Initialize timbre extractor.
        
        Args:
            feature_set: OpenSMILE feature set name
            feature_level: Feature level (lld, lld_de, functionals)
        """
        self.feature_set_name = feature_set or settings.opensmile_feature_set
        self.feature_level = feature_level or settings.opensmile_feature_level
        
        # Map string to OpenSMILE feature set enum
        feature_set_map = {
            'eGeMAPSv02': opensmile.FeatureSet.eGeMAPSv02,
            'ComParE_2016': opensmile.FeatureSet.ComParE_2016,
            'GeMAPSv01b': opensmile.FeatureSet.GeMAPSv01b,
        }
        
        feature_level_map = {
            'lld': opensmile.FeatureLevel.LowLevelDescriptors,
            'lld_de': opensmile.FeatureLevel.LowLevelDescriptors_Deltas,
            'functionals': opensmile.FeatureLevel.Functionals,
        }
        
        self.feature_set = feature_set_map.get(
            self.feature_set_name, 
            opensmile.FeatureSet.eGeMAPSv02
        )
        self.level = feature_level_map.get(
            self.feature_level,
            opensmile.FeatureLevel.Functionals
        )
        
        # Initialize SMILE extractor
        self._smile = None
    
    @property
    def smile(self) -> opensmile.Smile:
        """Lazy-load OpenSMILE extractor."""
        if self._smile is None:
            logger.info(
                f"Initializing OpenSMILE ({self.feature_set_name}, {self.feature_level})"
            )
            self._smile = opensmile.Smile(
                feature_set=self.feature_set,
                feature_level=self.level,
            )
        return self._smile
    
    def extract_features(
        self, 
        audio: np.ndarray, 
        sr: int
    ) -> Dict[str, float]:
        """
        Extract timbre features from audio.
        
        Args:
            audio: Audio array
            sr: Sample rate
            
        Returns:
            Dictionary of feature name -> value
        """
        logger.info("Extracting timbre features with OpenSMILE")
        
        # OpenSMILE needs a file, so we create a temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as tmp:
            sf.write(tmp.name, audio, sr)
            
            # Extract features
            features_df = self.smile.process_file(tmp.name)
        
        # Convert DataFrame to dict
        if len(features_df) == 0:
            raise ValueError("No features extracted from audio")
        
        # Get first row (functionals are aggregated)
        features = features_df.iloc[0].to_dict()
        
        logger.info(f"Extracted {len(features)} timbre features")
        
        return features
    
    def extract_key_features(
        self, 
        audio: np.ndarray, 
        sr: int
    ) -> Dict[str, Optional[float]]:
        """
        Extract key subset of features for display.
        
        Args:
            audio: Audio array
            sr: Sample rate
            
        Returns:
            Dictionary of key features
        """
        full_features = self.extract_features(audio, sr)
        
        key_features = {}
        for feature_name in KEY_FEATURES:
            key_features[feature_name] = full_features.get(feature_name)
        
        return key_features
    
    def get_summary_features(
        self, 
        features: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Get human-readable summary of timbre features.
        
        Args:
            features: Full feature dictionary
            
        Returns:
            Summary with interpretable feature names
        """
        def safe_get(key: str, default: float = 0.0) -> float:
            val = features.get(key)
            return float(val) if val is not None else default
        
        summary = {
            # Pitch-related
            'mean_f0_semitone': safe_get('F0semitoneFrom27.5Hz_sma3nz_amean'),
            'f0_variability': safe_get('F0semitoneFrom27.5Hz_sma3nz_stddevNorm'),
            
            # Voice quality
            'jitter': safe_get('jitterLocal_sma3nz_amean'),
            'shimmer': safe_get('shimmerLocaldB_sma3nz_amean'),
            'hnr': safe_get('HNRdBACF_sma3nz_amean'),
            
            # Formants
            'f1_mean': safe_get('F1frequency_sma3nz_amean'),
            'f2_mean': safe_get('F2frequency_sma3nz_amean'),
            'f3_mean': safe_get('F3frequency_sma3nz_amean'),
            
            # Energy
            'loudness_mean': safe_get('loudness_sma3_amean'),
            'loudness_variability': safe_get('loudness_sma3_stddevNorm'),
            
            # Spectral
            'spectral_flux': safe_get('spectralFlux_sma3_amean'),
            
            # Harmonic structure
            'h1_h2_ratio': safe_get('logRelF0-H1-H2_sma3nz_amean'),
            'h1_a3_ratio': safe_get('logRelF0-H1-A3_sma3nz_amean'),
        }
        
        return summary
    
    def features_to_vector(
        self, 
        features: Dict[str, float],
        feature_names: list = None,
    ) -> np.ndarray:
        """
        Convert feature dict to numpy vector for similarity computation.
        
        Args:
            features: Feature dictionary
            feature_names: List of feature names to include (for consistent ordering)
            
        Returns:
            Feature vector as numpy array
        """
        if feature_names is None:
            # Use sorted keys for consistent ordering
            feature_names = sorted(features.keys())
        
        vector = np.array([
            features.get(name, 0.0) for name in feature_names
        ], dtype=np.float32)
        
        # Handle NaN values
        vector = np.nan_to_num(vector, nan=0.0)
        
        return vector
    
    def get_feature_names(self) -> list:
        """Get list of all feature names from the extractor."""
        return list(self.smile.feature_names)


# Module-level instance
timbre_extractor = TimbreExtractor()

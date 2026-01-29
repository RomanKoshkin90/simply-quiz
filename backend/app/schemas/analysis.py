"""
Pydantic schemas for voice analysis API.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PitchAnalysis(BaseModel):
    """Pitch analysis results."""
    min_pitch_hz: float = Field(..., description="Minimum detected pitch in Hz")
    max_pitch_hz: float = Field(..., description="Maximum detected pitch in Hz")
    median_pitch_hz: float = Field(..., description="Median pitch in Hz")
    pitch_std_hz: float = Field(..., description="Standard deviation of pitch")
    
    min_pitch_note: str = Field(..., description="Min pitch as musical note (e.g. 'C3')")
    max_pitch_note: str = Field(..., description="Max pitch as musical note (e.g. 'C5')")
    
    detected_voice_type: Optional[str] = Field(
        None, description="Detected voice type (bass, baritone, tenor, alto, soprano)"
    )
    octave_range: float = Field(..., description="Vocal range in octaves")


class SimilarArtist(BaseModel):
    """Similar artist match."""
    artist_id: int
    name: str
    similarity_score: float = Field(..., ge=0, le=100, description="Similarity percentage")
    voice_type: Optional[str] = None
    genre: Optional[str] = None


class RecommendedSong(BaseModel):
    """Recommended song based on vocal range."""
    song_id: int
    title: str
    artist_name: str
    pitch_match_score: float = Field(..., description="How well song matches user's range")
    difficulty: Optional[int] = Field(None, ge=1, le=5)


class TimbreFeatures(BaseModel):
    """Extracted timbre/acoustic features from OpenSMILE."""
    # Key eGeMAPS features (subset for display)
    mean_f0: Optional[float] = Field(None, description="Mean fundamental frequency")
    jitter: Optional[float] = Field(None, description="Pitch variation (jitter)")
    shimmer: Optional[float] = Field(None, description="Amplitude variation (shimmer)")
    hnr: Optional[float] = Field(None, description="Harmonics-to-noise ratio")
    
    # Formants
    f1_mean: Optional[float] = Field(None, description="First formant mean")
    f2_mean: Optional[float] = Field(None, description="Second formant mean")
    f3_mean: Optional[float] = Field(None, description="Third formant mean")
    
    # Spectral features
    spectral_flux: Optional[float] = Field(None, description="Spectral flux")
    mfcc_summary: Optional[dict] = Field(None, description="MFCC feature summary")
    
    # Full feature dict for storage
    full_features: Optional[dict] = Field(None, description="All extracted features")


class VoiceAnalysisRequest(BaseModel):
    """Request for voice analysis."""
    session_id: Optional[str] = Field(None, description="Optional session ID for tracking")


class VoiceAnalysisResponse(BaseModel):
    """Complete voice analysis response."""
    session_id: str
    
    # Pitch analysis
    pitch_analysis: PitchAnalysis
    
    # Timbre features
    timbre_features: TimbreFeatures
    
    # Similar artists
    top_similar_artists: list[SimilarArtist]
    
    # Recommended songs
    recommended_songs: list[RecommendedSong]
    
    # Metadata
    audio_duration_seconds: float
    analysis_timestamp: datetime
    
    class Config:
        from_attributes = True


class AudioUploadResponse(BaseModel):
    """Response after audio file upload."""
    session_id: str
    filename: str
    duration_seconds: float
    sample_rate: int
    message: str


class AnalysisStatusResponse(BaseModel):
    """Status of analysis job."""
    session_id: str
    status: str  # pending, processing, completed, failed
    progress_percent: Optional[float] = None
    error_message: Optional[str] = None

"""
SQLAlchemy ORM models for voice analysis system.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, Text, Integer, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY

from app.db.database import Base


class ArtistProfile(Base):
    """
    Artist voice profile for similarity comparison.
    Contains pre-computed voice embeddings and features.
    """
    __tablename__ = "artist_profiles"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    genre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Vocal range
    min_pitch_hz: Mapped[float] = mapped_column(Float, nullable=False)
    max_pitch_hz: Mapped[float] = mapped_column(Float, nullable=False)
    median_pitch_hz: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Voice classification
    voice_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # bass, baritone, tenor, alto, soprano
    
    # Timbre features (OpenSMILE eGeMAPS - 88 features)
    timbre_features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Voice embedding vector (for similarity search)
    # Stored as JSON array for simplicity, consider pgvector for production
    voice_embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    songs: Mapped[list["Song"]] = relationship("Song", back_populates="artist")


class Song(Base):
    """
    Song with pitch range information for recommendations.
    """
    __tablename__ = "songs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artist_profiles.id"), nullable=False)
    
    # Song pitch range (for matching user's vocal range)
    min_pitch_hz: Mapped[float] = mapped_column(Float, nullable=False)
    max_pitch_hz: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Difficulty level (1-5)
    difficulty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Metadata
    genre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Yandex Music integration
    yandex_music_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    yandex_music_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Relationships
    artist: Mapped["ArtistProfile"] = relationship("ArtistProfile", back_populates="songs")


class VoiceAnalysisResult(Base):
    """
    Stored results of voice analysis for a user session.
    """
    __tablename__ = "voice_analysis_results"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # Audio file info
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    audio_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Pitch analysis results
    min_pitch_hz: Mapped[float] = mapped_column(Float, nullable=False)
    max_pitch_hz: Mapped[float] = mapped_column(Float, nullable=False)
    median_pitch_hz: Mapped[float] = mapped_column(Float, nullable=False)
    pitch_std_hz: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Voice classification
    detected_voice_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timbre features
    timbre_features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Voice embedding
    voice_embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # Similar artists results (JSON array of {artist_id, name, similarity_score})
    similar_artists: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # Recommended songs (JSON array of {song_id, title, artist_name})
    recommended_songs: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

"""
Voice analysis pipeline orchestration.
Coordinates all processing steps from audio upload to final analysis.
"""
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import uuid
import logging
from datetime import datetime

from app.core.audio_preprocessing import AudioPreprocessor
from app.core.pitch_extraction import PitchExtractor, PitchAnalysisResult
from app.core.timbre_extraction import TimbreExtractor
from app.core.voice_embedding import VoiceEmbeddingGenerator
from app.core.similarity_engine import SimilarityEngine, ArtistMatch, SongMatch
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Complete result of voice analysis pipeline."""
    session_id: str
    
    # Audio info
    original_duration: float
    processed_duration: float
    sample_rate: int
    
    # Pitch analysis
    min_pitch_hz: float
    max_pitch_hz: float
    median_pitch_hz: float
    mean_pitch_hz: float
    pitch_std_hz: float
    octave_range: float
    voiced_ratio: float
    detected_voice_type: Optional[str]
    min_pitch_note: str
    max_pitch_note: str
    
    # Timbre features
    timbre_summary: Dict[str, Any]
    timbre_full: Dict[str, float]
    
    # Embedding
    voice_embedding: np.ndarray
    
    # Similar artists
    similar_artists: list[ArtistMatch]
    
    # Recommended songs
    recommended_songs: list[SongMatch]
    
    # Metadata
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result['voice_embedding'] = self.voice_embedding.tolist()
        result['similar_artists'] = [asdict(a) for a in self.similar_artists]
        result['recommended_songs'] = [asdict(s) for s in self.recommended_songs]
        result['timestamp'] = self.timestamp.isoformat()
        return result


class VoiceAnalysisPipeline:
    """
    Main pipeline for voice analysis.
    Orchestrates all processing steps.
    """
    
    def __init__(
        self,
        preprocessor: AudioPreprocessor = None,
        pitch_extractor: PitchExtractor = None,
        timbre_extractor: TimbreExtractor = None,
        embedding_generator: VoiceEmbeddingGenerator = None,
        similarity_engine: SimilarityEngine = None,
    ):
        """
        Initialize pipeline with optional custom components.
        
        Args:
            preprocessor: Audio preprocessor
            pitch_extractor: Pitch extraction component
            timbre_extractor: Timbre extraction component
            embedding_generator: Voice embedding generator
            similarity_engine: Similarity computation engine
        """
        self.preprocessor = preprocessor or AudioPreprocessor()
        self.pitch_extractor = pitch_extractor or PitchExtractor()
        self.timbre_extractor = timbre_extractor or TimbreExtractor()
        self.embedding_generator = embedding_generator or VoiceEmbeddingGenerator()
        self.similarity_engine = similarity_engine or SimilarityEngine()
    
    async def analyze(
        self,
        audio_path: str | Path,
        session_id: str = None,
        artists_data: list[Dict[str, Any]] = None,
        songs_data: list[Dict[str, Any]] = None,
    ) -> PipelineResult:
        """
        Run full voice analysis pipeline.
        
        Args:
            audio_path: Path to audio file
            session_id: Optional session ID (generated if not provided)
            artists_data: Artist profiles for similarity comparison
            songs_data: Songs for recommendations
            
        Returns:
            PipelineResult with all analysis data
        """
        import time
        pipeline_start = time.time()
        
        session_id = session_id or str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        print(f"[PIPELINE] 🚀 Запуск анализа для {session_id}")
        
        # Step 1: Preprocess audio
        print(f"[PIPELINE] 1️⃣ Предобработка аудио...")
        step_start = time.time()
        audio, sr, original_duration = self.preprocessor.preprocess(audio_path)
        processed_duration = len(audio) / sr
        print(f"[PIPELINE] ✅ Предобработка: {time.time() - step_start:.1f}s (длина: {processed_duration:.1f}s)")
        
        # Clip audio for analysis — 30s is more than enough for voice type detection
        max_analysis_samples = settings.max_analysis_duration_seconds * sr
        analysis_audio = audio[:max_analysis_samples] if len(audio) > max_analysis_samples else audio
        print(f"[PIPELINE] 🎯 Анализ: {len(analysis_audio)/sr:.1f}s из {processed_duration:.1f}s")

        # Step 2: Extract pitch
        print(f"[PIPELINE] 2️⃣ Извлечение pitch (CREPE)...")
        step_start = time.time()
        pitch_result = self.pitch_extractor.extract_pitch(analysis_audio, sr)
        pitch_analysis = self.pitch_extractor.analyze_pitch(pitch_result)
        print(f"[PIPELINE] ✅ Pitch: {time.time() - step_start:.1f}s")

        # Step 3: Extract timbre features
        print(f"[PIPELINE] 3️⃣ Извлечение тембра (OpenSMILE)...")
        step_start = time.time()
        timbre_full = self.timbre_extractor.extract_features(analysis_audio, sr)
        timbre_summary = self.timbre_extractor.get_summary_features(timbre_full)
        print(f"[PIPELINE] ✅ Тембр: {time.time() - step_start:.1f}s")
        
        # Step 4: Generate voice embedding
        print(f"[PIPELINE] 4️⃣ Генерация embedding...")
        step_start = time.time()
        voice_embedding = self.embedding_generator.generate(
            analysis_audio, sr, pitch_analysis
        )
        print(f"[PIPELINE] ✅ Embedding: {time.time() - step_start:.1f}s")
        
        # Step 5: Find similar artists and recommend songs
        print(f"[PIPELINE] 5️⃣ Поиск похожих артистов...")
        
        similar_artists = []
        if artists_data:
            similar_artists = self.similarity_engine.find_similar_artists(
                user_embedding=voice_embedding,
                user_min_pitch=pitch_analysis.min_pitch_hz,
                user_max_pitch=pitch_analysis.max_pitch_hz,
                user_timbre=timbre_summary,
                artists=artists_data,
            )
        
        recommended_songs = []
        if songs_data:
            recommended_songs = self.similarity_engine.recommend_songs(
                user_min_pitch=pitch_analysis.min_pitch_hz,
                user_max_pitch=pitch_analysis.max_pitch_hz,
                songs=songs_data,
            )
        
        print(f"[PIPELINE] ✅ Артисты: {len(similar_artists)}, Песни: {len(recommended_songs)}")
        print(f"[PIPELINE] 🎉 Анализ завершен за {time.time() - pipeline_start:.1f}s")
        
        return PipelineResult(
            session_id=session_id,
            original_duration=original_duration,
            processed_duration=processed_duration,
            sample_rate=sr,
            min_pitch_hz=pitch_analysis.min_pitch_hz,
            max_pitch_hz=pitch_analysis.max_pitch_hz,
            median_pitch_hz=pitch_analysis.median_pitch_hz,
            mean_pitch_hz=pitch_analysis.mean_pitch_hz,
            pitch_std_hz=pitch_analysis.std_pitch_hz,
            octave_range=pitch_analysis.octave_range,
            voiced_ratio=pitch_analysis.voiced_ratio,
            detected_voice_type=pitch_analysis.detected_voice_type,
            min_pitch_note=pitch_analysis.min_pitch_note,
            max_pitch_note=pitch_analysis.max_pitch_note,
            timbre_summary=timbre_summary,
            timbre_full=timbre_full,
            voice_embedding=voice_embedding,
            similar_artists=similar_artists,
            recommended_songs=recommended_songs,
            timestamp=timestamp,
        )
    
    def analyze_sync(
        self,
        audio_path: str | Path,
        session_id: str = None,
        artists_data: list[Dict[str, Any]] = None,
        songs_data: list[Dict[str, Any]] = None,
    ) -> PipelineResult:
        """
        Synchronous version of analyze for non-async contexts.
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.analyze(audio_path, session_id, artists_data, songs_data)
        )


# Module-level instance
pipeline = VoiceAnalysisPipeline()

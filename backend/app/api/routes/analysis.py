"""
Voice analysis endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
from typing import Optional
import logging
from datetime import datetime

from app.config import settings
from app.db.database import get_db
from app.db.models import ArtistProfile, Song, VoiceAnalysisResult
from app.schemas.analysis import (
    VoiceAnalysisResponse,
    VoiceAnalysisRequest,
    PitchAnalysis,
    TimbreFeatures,
    SimilarArtist,
    RecommendedSong,
)
from app.core.pipeline import VoiceAnalysisPipeline

logger = logging.getLogger(__name__)

router = APIRouter()

# Supported audio formats (должно совпадать с audio.py)
SUPPORTED_FORMATS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.webm'}


def find_audio_file(session_id: str) -> Optional[Path]:
    """Find uploaded audio file by session ID."""
    upload_dir = Path(settings.audio_upload_dir)
    logger.info(f"Looking for audio file with session_id: {session_id} in {upload_dir}")
    
    for ext in SUPPORTED_FORMATS:
        file_path = upload_dir / f"{session_id}{ext}"
        if file_path.exists():
            logger.info(f"Found audio file: {file_path}")
            return file_path
        else:
            logger.debug(f"Checked: {file_path} (not found)")
    
    # Логируем все файлы в директории для отладки
    if upload_dir.exists():
        existing_files = list(upload_dir.glob(f"{session_id}*"))
        if existing_files:
            logger.warning(f"Found files with similar session_id: {existing_files}")
        else:
            all_files = list(upload_dir.glob("*"))
            logger.warning(f"No files found. Upload dir contains {len(all_files)} files total")
    else:
        logger.error(f"Upload directory does not exist: {upload_dir}")
    
    return None


@router.post("/analyze-voice", response_model=VoiceAnalysisResponse)
async def analyze_voice(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze uploaded voice recording.
    
    Performs full voice analysis pipeline:
    1. Audio preprocessing
    2. Pitch extraction (CREPE)
    3. Timbre feature extraction (OpenSMILE)
    4. Voice embedding generation
    5. Artist similarity matching
    6. Song recommendations
    
    Returns comprehensive voice analysis including:
    - Pitch range (min, max, median)
    - Detected voice type
    - Timbre characteristics
    - Top similar artists
    - Recommended songs
    """
    # Find audio file
    audio_path = find_audio_file(session_id)
    if not audio_path:
        raise HTTPException(
            status_code=404,
            detail=f"Audio file not found for session {session_id}. "
                   "Please upload audio first using /upload-audio"
        )
    
    try:
        import time
        start_time = time.time()
        
        print(f"[ANALYSIS] 🎬 Начинаю анализ для сессии {session_id}")
        
        # Load artist profiles from database
        print(f"[ANALYSIS] 📊 Загружаю профили артистов из БД...")
        artists_result = await db.execute(select(ArtistProfile))
        artist_profiles = artists_result.scalars().all()
        print(f"[ANALYSIS] ✅ Загружено {len(artist_profiles)} артистов ({time.time() - start_time:.1f}s)")
        
        artists_data = [
            {
                'id': artist.id,
                'name': artist.name,
                'genre': artist.genre,
                'voice_type': artist.voice_type,
                'min_pitch_hz': artist.min_pitch_hz,
                'max_pitch_hz': artist.max_pitch_hz,
                'median_pitch_hz': artist.median_pitch_hz,
                'timbre_features': artist.timbre_features,
                'voice_embedding': artist.voice_embedding,
            }
            for artist in artist_profiles
        ]
        
        # Load songs from database
        songs_result = await db.execute(
            select(Song, ArtistProfile.name)
            .join(ArtistProfile, Song.artist_id == ArtistProfile.id)
        )
        songs_with_artists = songs_result.all()
        
        songs_data = [
            {
                'id': song.id,
                'title': song.title,
                'artist_name': artist_name,
                'min_pitch_hz': song.min_pitch_hz,
                'max_pitch_hz': song.max_pitch_hz,
                'difficulty': song.difficulty,
                'genre': song.genre,
                'yandex_music_id': getattr(song, 'yandex_music_id', None),
                'yandex_music_url': getattr(song, 'yandex_music_url', None),
            }
            for song, artist_name in songs_with_artists
        ]
        
        # Run analysis pipeline
        print(f"[ANALYSIS] 🎤 Запускаю анализ голоса... ({time.time() - start_time:.1f}s)")
        pipeline = VoiceAnalysisPipeline()
        result = await pipeline.analyze(
            audio_path=audio_path,
            session_id=session_id,
            artists_data=artists_data,
            songs_data=songs_data,
        )
        
        # Save result to database
        analysis_record = VoiceAnalysisResult(
            session_id=session_id,
            original_filename=audio_path.name,
            audio_duration_seconds=result.original_duration,
            min_pitch_hz=result.min_pitch_hz,
            max_pitch_hz=result.max_pitch_hz,
            median_pitch_hz=result.median_pitch_hz,
            pitch_std_hz=result.pitch_std_hz,
            detected_voice_type=result.detected_voice_type,
            timbre_features=result.timbre_summary,
            voice_embedding=result.voice_embedding.tolist(),
            similar_artists=[
                {
                    'artist_id': a.artist_id,
                    'name': a.name,
                    'similarity_score': a.similarity_score,
                    'voice_type': a.voice_type,
                    'genre': a.genre,
                }
                for a in result.similar_artists
            ],
            recommended_songs=[
                {
                    'song_id': s.song_id,
                    'title': s.title,
                    'artist_name': s.artist_name,
                    'pitch_match_score': s.pitch_match_score,
                    'difficulty': s.difficulty,
                    'yandex_music_id': s.yandex_music_id,
                    'yandex_music_url': s.yandex_music_url,
                }
                for s in result.recommended_songs
            ],
        )
        db.add(analysis_record)
        await db.commit()
        
        # Build response
        return VoiceAnalysisResponse(
            session_id=session_id,
            pitch_analysis=PitchAnalysis(
                min_pitch_hz=result.min_pitch_hz,
                max_pitch_hz=result.max_pitch_hz,
                median_pitch_hz=result.median_pitch_hz,
                pitch_std_hz=result.pitch_std_hz,
                min_pitch_note=result.min_pitch_note,
                max_pitch_note=result.max_pitch_note,
                detected_voice_type=result.detected_voice_type,
                octave_range=result.octave_range,
            ),
            timbre_features=TimbreFeatures(
                mean_f0=result.timbre_summary.get('mean_f0_semitone'),
                jitter=result.timbre_summary.get('jitter'),
                shimmer=result.timbre_summary.get('shimmer'),
                hnr=result.timbre_summary.get('hnr'),
                f1_mean=result.timbre_summary.get('f1_mean'),
                f2_mean=result.timbre_summary.get('f2_mean'),
                f3_mean=result.timbre_summary.get('f3_mean'),
                spectral_flux=result.timbre_summary.get('spectral_flux'),
                full_features=result.timbre_full,
            ),
            top_similar_artists=[
                SimilarArtist(
                    artist_id=a.artist_id,
                    name=a.name,
                    similarity_score=round(a.similarity_score, 1),
                    voice_type=a.voice_type,
                    genre=a.genre,
                )
                for a in result.similar_artists
            ],
            recommended_songs=[
                RecommendedSong(
                    song_id=s.song_id,
                    title=s.title,
                    artist_name=s.artist_name,
                    pitch_match_score=round(s.pitch_match_score, 1),
                    difficulty=s.difficulty,
                    yandex_music_id=s.yandex_music_id,
                    yandex_music_url=s.yandex_music_url,
                )
                for s in result.recommended_songs
            ],
            audio_duration_seconds=result.original_duration,
            analysis_timestamp=result.timestamp,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error analyzing voice: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error during voice analysis: {str(e)}"
        )


@router.get("/analysis/{session_id}", response_model=VoiceAnalysisResponse)
async def get_analysis_result(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get previously computed analysis result by session ID.
    """
    result = await db.execute(
        select(VoiceAnalysisResult)
        .where(VoiceAnalysisResult.session_id == session_id)
    )
    analysis = result.scalar_one_or_none()
    
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis result not found for session {session_id}"
        )
    
    # Reconstruct response from stored data
    return VoiceAnalysisResponse(
        session_id=analysis.session_id,
        pitch_analysis=PitchAnalysis(
            min_pitch_hz=analysis.min_pitch_hz,
            max_pitch_hz=analysis.max_pitch_hz,
            median_pitch_hz=analysis.median_pitch_hz,
            pitch_std_hz=analysis.pitch_std_hz or 0,
            min_pitch_note="N/A",  # Not stored
            max_pitch_note="N/A",  # Not stored
            detected_voice_type=analysis.detected_voice_type,
            octave_range=0,  # Recalculate if needed
        ),
        timbre_features=TimbreFeatures(
            mean_f0=analysis.timbre_features.get('mean_f0_semitone') if analysis.timbre_features else None,
            jitter=analysis.timbre_features.get('jitter') if analysis.timbre_features else None,
            shimmer=analysis.timbre_features.get('shimmer') if analysis.timbre_features else None,
            hnr=analysis.timbre_features.get('hnr') if analysis.timbre_features else None,
            f1_mean=analysis.timbre_features.get('f1_mean') if analysis.timbre_features else None,
            f2_mean=analysis.timbre_features.get('f2_mean') if analysis.timbre_features else None,
            f3_mean=analysis.timbre_features.get('f3_mean') if analysis.timbre_features else None,
            spectral_flux=analysis.timbre_features.get('spectral_flux') if analysis.timbre_features else None,
            full_features=analysis.timbre_features,
        ),
        top_similar_artists=[
            SimilarArtist(
                artist_id=a['artist_id'],
                name=a['name'],
                similarity_score=a['similarity_score'],
                voice_type=a.get('voice_type'),
                genre=a.get('genre'),
            )
            for a in (analysis.similar_artists or [])
        ],
        recommended_songs=[
            RecommendedSong(
                song_id=s['song_id'],
                title=s['title'],
                artist_name=s['artist_name'],
                pitch_match_score=s.get('pitch_match_score', 0),
                difficulty=s.get('difficulty'),
                yandex_music_id=s.get('yandex_music_id'),
                yandex_music_url=s.get('yandex_music_url'),
            )
            for s in (analysis.recommended_songs or [])
        ],
        audio_duration_seconds=analysis.audio_duration_seconds,
        analysis_timestamp=analysis.created_at,
    )

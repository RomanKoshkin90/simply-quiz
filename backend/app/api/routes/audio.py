"""
Audio upload and processing endpoints.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import uuid
import aiofiles
import librosa
import logging

from app.config import settings
from app.schemas.analysis import AudioUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Supported audio formats (librosa поддерживает webm через audioread)
SUPPORTED_FORMATS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.webm'}


def validate_audio_file(filename: str) -> bool:
    """Validate audio file extension."""
    ext = Path(filename).suffix.lower()
    return ext in SUPPORTED_FORMATS


@router.post("/upload-audio", response_model=AudioUploadResponse)
async def upload_audio(
    file: UploadFile = File(..., description="Audio file to upload"),
):
    """
    Upload audio file for voice analysis.
    
    Accepts WAV, MP3, FLAC, OGG, M4A, AAC, WMA formats.
    Maximum duration: 5 minutes.
    
    Returns session_id for subsequent analysis request.
    """
    # Validate file extension
    if not validate_audio_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Create upload path
    ext = Path(file.filename).suffix.lower()
    upload_path = Path(settings.audio_upload_dir) / f"{session_id}{ext}"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Save uploaded file
        async with aiofiles.open(upload_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        # Проверяем что файл действительно сохранился
        if not upload_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Failed to save uploaded file"
            )
        
        file_size = upload_path.stat().st_size
        logger.info(f"Saved uploaded file: {upload_path} (size: {file_size} bytes, ext: {ext})")
        
        # Get audio info
        duration = librosa.get_duration(path=str(upload_path))
        
        # Check duration limit
        if duration > settings.max_audio_duration_seconds:
            # Remove file
            upload_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail=f"Audio duration ({duration:.1f}s) exceeds maximum "
                       f"({settings.max_audio_duration_seconds}s)"
            )
        
        # Get sample rate
        sr = librosa.get_samplerate(str(upload_path))
        
        return AudioUploadResponse(
            session_id=session_id,
            filename=file.filename,
            duration_seconds=round(duration, 2),
            sample_rate=sr,
            message="Audio uploaded successfully. Use session_id for analysis."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        # Cleanup on error
        upload_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing audio file: {str(e)}"
        )


@router.delete("/audio/{session_id}")
async def delete_audio(session_id: str):
    """
    Delete uploaded audio file by session ID.
    """
    upload_dir = Path(settings.audio_upload_dir)
    
    # Find file with session_id
    for ext in SUPPORTED_FORMATS:
        file_path = upload_dir / f"{session_id}{ext}"
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted audio file: {file_path}")
            return {"message": "Audio file deleted", "session_id": session_id}
    
    raise HTTPException(
        status_code=404,
        detail=f"Audio file not found for session {session_id}"
    )

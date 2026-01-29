"""
Artist profile service for database operations.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List
import numpy as np
import logging

from app.db.models import ArtistProfile, Song

logger = logging.getLogger(__name__)


class ArtistService:
    """Service for artist profile CRUD operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_artist(
        self,
        name: str,
        min_pitch_hz: float,
        max_pitch_hz: float,
        median_pitch_hz: float,
        genre: str = None,
        voice_type: str = None,
        timbre_features: dict = None,
        voice_embedding: list = None,
    ) -> ArtistProfile:
        """Create new artist profile."""
        artist = ArtistProfile(
            name=name,
            genre=genre,
            min_pitch_hz=min_pitch_hz,
            max_pitch_hz=max_pitch_hz,
            median_pitch_hz=median_pitch_hz,
            voice_type=voice_type,
            timbre_features=timbre_features,
            voice_embedding=voice_embedding,
        )
        self.db.add(artist)
        await self.db.commit()
        await self.db.refresh(artist)
        
        logger.info(f"Created artist profile: {name} (id={artist.id})")
        return artist
    
    async def get_artist(self, artist_id: int) -> Optional[ArtistProfile]:
        """Get artist by ID."""
        result = await self.db.execute(
            select(ArtistProfile).where(ArtistProfile.id == artist_id)
        )
        return result.scalar_one_or_none()
    
    async def get_artist_by_name(self, name: str) -> Optional[ArtistProfile]:
        """Get artist by name."""
        result = await self.db.execute(
            select(ArtistProfile).where(ArtistProfile.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_all_artists(self) -> List[ArtistProfile]:
        """Get all artist profiles."""
        result = await self.db.execute(select(ArtistProfile))
        return list(result.scalars().all())
    
    async def update_artist_embedding(
        self,
        artist_id: int,
        voice_embedding: list,
    ) -> Optional[ArtistProfile]:
        """Update artist's voice embedding."""
        artist = await self.get_artist(artist_id)
        if artist:
            artist.voice_embedding = voice_embedding
            await self.db.commit()
            await self.db.refresh(artist)
        return artist
    
    async def delete_artist(self, artist_id: int) -> bool:
        """Delete artist profile."""
        result = await self.db.execute(
            delete(ArtistProfile).where(ArtistProfile.id == artist_id)
        )
        await self.db.commit()
        return result.rowcount > 0


class SongService:
    """Service for song CRUD operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_song(
        self,
        title: str,
        artist_id: int,
        min_pitch_hz: float,
        max_pitch_hz: float,
        difficulty: int = None,
        genre: str = None,
        duration_seconds: int = None,
    ) -> Song:
        """Create new song."""
        song = Song(
            title=title,
            artist_id=artist_id,
            min_pitch_hz=min_pitch_hz,
            max_pitch_hz=max_pitch_hz,
            difficulty=difficulty,
            genre=genre,
            duration_seconds=duration_seconds,
        )
        self.db.add(song)
        await self.db.commit()
        await self.db.refresh(song)
        
        logger.info(f"Created song: {title} (id={song.id})")
        return song
    
    async def get_songs_by_artist(self, artist_id: int) -> List[Song]:
        """Get all songs by artist."""
        result = await self.db.execute(
            select(Song).where(Song.artist_id == artist_id)
        )
        return list(result.scalars().all())
    
    async def get_all_songs(self) -> List[Song]:
        """Get all songs."""
        result = await self.db.execute(select(Song))
        return list(result.scalars().all())
    
    async def get_songs_in_range(
        self,
        min_pitch_hz: float,
        max_pitch_hz: float,
    ) -> List[Song]:
        """Get songs matching pitch range."""
        result = await self.db.execute(
            select(Song).where(
                Song.min_pitch_hz >= min_pitch_hz * 0.8,  # Some tolerance
                Song.max_pitch_hz <= max_pitch_hz * 1.2,
            )
        )
        return list(result.scalars().all())

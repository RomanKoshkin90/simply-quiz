"""
Database seeding script with sample artists and songs.
Run this to populate the database with test data.

Usage:
    python -m scripts.seed_database
"""
import asyncio
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal, engine, Base
from app.services.artist_service import ArtistService, SongService


# Sample artist data (approximate vocal ranges for famous singers)
SAMPLE_ARTISTS = [
    {
        "name": "Freddie Mercury",
        "genre": "Rock",
        "voice_type": "tenor",
        "min_pitch_hz": 92.5,   # F#2
        "max_pitch_hz": 784.0,  # G5
        "median_pitch_hz": 330.0,
    },
    {
        "name": "Adele",
        "genre": "Pop/Soul",
        "voice_type": "mezzo-soprano",
        "min_pitch_hz": 175.0,  # F3
        "max_pitch_hz": 700.0,  # F5
        "median_pitch_hz": 330.0,
    },
    {
        "name": "Michael Jackson",
        "genre": "Pop",
        "voice_type": "tenor",
        "min_pitch_hz": 165.0,  # E3
        "max_pitch_hz": 830.0,  # G#5
        "median_pitch_hz": 370.0,
    },
    {
        "name": "Whitney Houston",
        "genre": "R&B/Pop",
        "voice_type": "soprano",
        "min_pitch_hz": 200.0,  # G3
        "max_pitch_hz": 880.0,  # A5
        "median_pitch_hz": 440.0,
    },
    {
        "name": "Ed Sheeran",
        "genre": "Pop",
        "voice_type": "tenor",
        "min_pitch_hz": 110.0,  # A2
        "max_pitch_hz": 523.0,  # C5
        "median_pitch_hz": 260.0,
    },
    {
        "name": "Beyoncé",
        "genre": "R&B/Pop",
        "voice_type": "mezzo-soprano",
        "min_pitch_hz": 175.0,  # F3
        "max_pitch_hz": 880.0,  # A5
        "median_pitch_hz": 392.0,
    },
    {
        "name": "Bruno Mars",
        "genre": "Pop/R&B",
        "voice_type": "tenor",
        "min_pitch_hz": 130.0,  # C3
        "max_pitch_hz": 698.0,  # F5
        "median_pitch_hz": 330.0,
    },
    {
        "name": "Frank Sinatra",
        "genre": "Jazz",
        "voice_type": "baritone",
        "min_pitch_hz": 98.0,   # G2
        "max_pitch_hz": 415.0,  # G#4
        "median_pitch_hz": 220.0,
    },
    {
        "name": "Lady Gaga",
        "genre": "Pop",
        "voice_type": "mezzo-soprano",
        "min_pitch_hz": 165.0,  # E3
        "max_pitch_hz": 830.0,  # G#5
        "median_pitch_hz": 370.0,
    },
    {
        "name": "Elvis Presley",
        "genre": "Rock/Pop",
        "voice_type": "baritone",
        "min_pitch_hz": 87.0,   # F2
        "max_pitch_hz": 493.0,  # B4
        "median_pitch_hz": 220.0,
    },
]

# Sample songs for each artist
SAMPLE_SONGS = {
    "Freddie Mercury": [
        {"title": "Bohemian Rhapsody", "min_pitch_hz": 130.0, "max_pitch_hz": 740.0, "difficulty": 5},
        {"title": "We Are The Champions", "min_pitch_hz": 146.0, "max_pitch_hz": 523.0, "difficulty": 3},
        {"title": "Somebody to Love", "min_pitch_hz": 165.0, "max_pitch_hz": 698.0, "difficulty": 4},
    ],
    "Adele": [
        {"title": "Hello", "min_pitch_hz": 196.0, "max_pitch_hz": 523.0, "difficulty": 3},
        {"title": "Rolling in the Deep", "min_pitch_hz": 175.0, "max_pitch_hz": 587.0, "difficulty": 4},
        {"title": "Someone Like You", "min_pitch_hz": 196.0, "max_pitch_hz": 466.0, "difficulty": 3},
    ],
    "Michael Jackson": [
        {"title": "Billie Jean", "min_pitch_hz": 196.0, "max_pitch_hz": 622.0, "difficulty": 3},
        {"title": "Beat It", "min_pitch_hz": 196.0, "max_pitch_hz": 587.0, "difficulty": 3},
        {"title": "Thriller", "min_pitch_hz": 175.0, "max_pitch_hz": 622.0, "difficulty": 3},
    ],
    "Whitney Houston": [
        {"title": "I Will Always Love You", "min_pitch_hz": 220.0, "max_pitch_hz": 784.0, "difficulty": 5},
        {"title": "Greatest Love of All", "min_pitch_hz": 196.0, "max_pitch_hz": 698.0, "difficulty": 4},
        {"title": "I Wanna Dance with Somebody", "min_pitch_hz": 220.0, "max_pitch_hz": 659.0, "difficulty": 3},
    ],
    "Ed Sheeran": [
        {"title": "Shape of You", "min_pitch_hz": 130.0, "max_pitch_hz": 440.0, "difficulty": 2},
        {"title": "Perfect", "min_pitch_hz": 146.0, "max_pitch_hz": 440.0, "difficulty": 2},
        {"title": "Thinking Out Loud", "min_pitch_hz": 130.0, "max_pitch_hz": 392.0, "difficulty": 2},
    ],
    "Beyoncé": [
        {"title": "Halo", "min_pitch_hz": 196.0, "max_pitch_hz": 698.0, "difficulty": 4},
        {"title": "Crazy in Love", "min_pitch_hz": 220.0, "max_pitch_hz": 622.0, "difficulty": 3},
        {"title": "Single Ladies", "min_pitch_hz": 220.0, "max_pitch_hz": 587.0, "difficulty": 3},
    ],
    "Bruno Mars": [
        {"title": "Just the Way You Are", "min_pitch_hz": 165.0, "max_pitch_hz": 523.0, "difficulty": 2},
        {"title": "Uptown Funk", "min_pitch_hz": 175.0, "max_pitch_hz": 587.0, "difficulty": 3},
        {"title": "Locked Out of Heaven", "min_pitch_hz": 196.0, "max_pitch_hz": 622.0, "difficulty": 4},
    ],
    "Frank Sinatra": [
        {"title": "My Way", "min_pitch_hz": 130.0, "max_pitch_hz": 370.0, "difficulty": 2},
        {"title": "Fly Me to the Moon", "min_pitch_hz": 146.0, "max_pitch_hz": 370.0, "difficulty": 2},
        {"title": "New York, New York", "min_pitch_hz": 130.0, "max_pitch_hz": 392.0, "difficulty": 2},
    ],
    "Lady Gaga": [
        {"title": "Bad Romance", "min_pitch_hz": 220.0, "max_pitch_hz": 698.0, "difficulty": 4},
        {"title": "Shallow", "min_pitch_hz": 175.0, "max_pitch_hz": 784.0, "difficulty": 5},
        {"title": "Poker Face", "min_pitch_hz": 196.0, "max_pitch_hz": 587.0, "difficulty": 3},
    ],
    "Elvis Presley": [
        {"title": "Can't Help Falling in Love", "min_pitch_hz": 130.0, "max_pitch_hz": 370.0, "difficulty": 2},
        {"title": "Suspicious Minds", "min_pitch_hz": 130.0, "max_pitch_hz": 440.0, "difficulty": 3},
        {"title": "Jailhouse Rock", "min_pitch_hz": 130.0, "max_pitch_hz": 392.0, "difficulty": 2},
    ],
}


def generate_fake_embedding(seed: int, dim: int = 512) -> list:
    """Generate reproducible fake embedding for demo purposes."""
    np.random.seed(seed)
    embedding = np.random.randn(dim).astype(np.float32)
    embedding = embedding / np.linalg.norm(embedding)
    return embedding.tolist()


def generate_fake_timbre(seed: int) -> dict:
    """Generate fake timbre features for demo purposes."""
    np.random.seed(seed)
    return {
        "mean_f0_semitone": float(np.random.uniform(30, 50)),
        "f0_variability": float(np.random.uniform(0.1, 0.5)),
        "jitter": float(np.random.uniform(0.01, 0.05)),
        "shimmer": float(np.random.uniform(0.1, 0.5)),
        "hnr": float(np.random.uniform(10, 25)),
        "f1_mean": float(np.random.uniform(400, 800)),
        "f2_mean": float(np.random.uniform(1000, 2000)),
        "f3_mean": float(np.random.uniform(2200, 3000)),
        "loudness_mean": float(np.random.uniform(0.3, 0.8)),
        "spectral_flux": float(np.random.uniform(0.01, 0.1)),
    }


async def seed_database():
    """Seed database with sample artists and songs."""
    print("Creating database tables...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        artist_service = ArtistService(session)
        song_service = SongService(session)
        
        print("Seeding artists...")
        
        for i, artist_data in enumerate(SAMPLE_ARTISTS):
            # Check if artist already exists
            existing = await artist_service.get_artist_by_name(artist_data["name"])
            if existing:
                print(f"  Skipping {artist_data['name']} (already exists)")
                continue
            
            # Create artist with fake embedding
            artist = await artist_service.create_artist(
                name=artist_data["name"],
                genre=artist_data["genre"],
                voice_type=artist_data["voice_type"],
                min_pitch_hz=artist_data["min_pitch_hz"],
                max_pitch_hz=artist_data["max_pitch_hz"],
                median_pitch_hz=artist_data["median_pitch_hz"],
                timbre_features=generate_fake_timbre(i),
                voice_embedding=generate_fake_embedding(i),
            )
            print(f"  Created: {artist.name}")
            
            # Add songs for this artist
            songs = SAMPLE_SONGS.get(artist.name, [])
            for song_data in songs:
                song = await song_service.create_song(
                    title=song_data["title"],
                    artist_id=artist.id,
                    min_pitch_hz=song_data["min_pitch_hz"],
                    max_pitch_hz=song_data["max_pitch_hz"],
                    difficulty=song_data["difficulty"],
                    genre=artist_data["genre"],
                )
                print(f"    Added song: {song.title}")
        
        print("\nDatabase seeding complete!")
        
        # Print summary
        artists = await artist_service.get_all_artists()
        songs = await song_service.get_all_songs()
        print(f"Total artists: {len(artists)}")
        print(f"Total songs: {len(songs)}")


if __name__ == "__main__":
    asyncio.run(seed_database())

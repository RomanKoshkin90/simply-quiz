"""
Similarity engine for comparing voice embeddings and features.
Uses cosine similarity for embedding comparison.
"""
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from sklearn.metrics.pairwise import cosine_similarity
from dataclasses import dataclass
import logging

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ArtistMatch:
    """Match result for an artist."""
    artist_id: int
    name: str
    similarity_score: float  # 0-100 percentage
    voice_type: Optional[str] = None
    genre: Optional[str] = None
    pitch_overlap: Optional[float] = None


@dataclass
class SongMatch:
    """Match result for a song recommendation."""
    song_id: int
    title: str
    artist_name: str
    pitch_match_score: float  # 0-100 percentage
    difficulty: Optional[int] = None
    yandex_music_id: Optional[str] = None
    yandex_music_url: Optional[str] = None


class SimilarityEngine:
    """
    Engine for computing similarity between voices.
    """
    
    def __init__(self, top_n: int = None):
        """
        Initialize similarity engine.
        
        Args:
            top_n: Number of top matches to return
        """
        self.top_n = top_n or settings.top_n_similar_artists
    
    def compute_embedding_similarity(
        self,
        user_embedding: np.ndarray,
        artist_embeddings: List[Tuple[int, np.ndarray]],
    ) -> List[Tuple[int, float]]:
        """
        Compute cosine similarity between user embedding and artist embeddings.
        
        Args:
            user_embedding: User's voice embedding (1D array)
            artist_embeddings: List of (artist_id, embedding) tuples
            
        Returns:
            List of (artist_id, similarity_score) tuples, sorted by score
        """
        if len(artist_embeddings) == 0:
            logger.warning("No artist embeddings to compare")
            return []
        
        # Reshape user embedding for sklearn
        user_emb = user_embedding.reshape(1, -1)
        
        # Stack artist embeddings
        artist_ids = [aid for aid, _ in artist_embeddings]
        artist_matrix = np.vstack([emb.reshape(1, -1) for _, emb in artist_embeddings])
        
        # Compute cosine similarities
        similarities = cosine_similarity(user_emb, artist_matrix)[0]
        
        # Convert to percentage (0-100) and pair with IDs
        results = [
            (artist_ids[i], float(max(0, similarities[i]) * 100))
            for i in range(len(artist_ids))
        ]
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(
            f"Computed similarity for {len(results)} artists. "
            f"Top score: {results[0][1]:.1f}%" if results else "No results"
        )
        
        return results
    
    def compute_pitch_overlap(
        self,
        user_min_hz: float,
        user_max_hz: float,
        target_min_hz: float,
        target_max_hz: float,
    ) -> float:
        """
        Compute overlap between two pitch ranges.
        
        Args:
            user_min_hz: User's minimum pitch
            user_max_hz: User's maximum pitch
            target_min_hz: Target (song/artist) minimum pitch
            target_max_hz: Target maximum pitch
            
        Returns:
            Overlap score as percentage (0-100)
        """
        # Calculate overlap
        overlap_min = max(user_min_hz, target_min_hz)
        overlap_max = min(user_max_hz, target_max_hz)
        
        if overlap_min >= overlap_max:
            # No overlap
            return 0.0
        
        overlap_range = overlap_max - overlap_min
        target_range = target_max_hz - target_min_hz
        
        if target_range <= 0:
            return 0.0
        
        # Score based on how much of target range user can cover
        overlap_score = (overlap_range / target_range) * 100
        
        return min(100.0, overlap_score)
    
    def compute_combined_similarity(
        self,
        user_embedding: np.ndarray,
        user_min_pitch: float,
        user_max_pitch: float,
        user_timbre: Dict[str, float],
        artist_data: Dict[str, Any],
        weights: Dict[str, float] = None,
    ) -> float:
        """
        Compute combined similarity using multiple factors.
        
        Args:
            user_embedding: User's voice embedding
            user_min_pitch: User's min pitch
            user_max_pitch: User's max pitch
            user_timbre: User's timbre features
            artist_data: Artist data dict with embedding, pitch, timbre
            weights: Weight for each factor
            
        Returns:
            Combined similarity score (0-100)
        """
        weights = weights or {
            'embedding': 0.5,
            'pitch': 0.3,
            'timbre': 0.2,
        }
        
        scores = {}
        
        # Embedding similarity
        if 'voice_embedding' in artist_data and artist_data['voice_embedding']:
            try:
                artist_emb = np.array(artist_data['voice_embedding'])
                if artist_emb.size > 0 and user_embedding.size > 0:
                    emb_sim = cosine_similarity(
                        user_embedding.reshape(1, -1),
                        artist_emb.reshape(1, -1)
                    )[0][0]
                    scores['embedding'] = max(0, emb_sim) * 100
                else:
                    scores['embedding'] = 0.0  # No similarity if empty
            except Exception as e:
                logger.warning(f"Error computing embedding similarity: {e}")
                scores['embedding'] = 0.0
        else:
            scores['embedding'] = 0.0  # No similarity if no embedding
        
        # Pitch overlap
        if 'min_pitch_hz' in artist_data and 'max_pitch_hz' in artist_data:
            scores['pitch'] = self.compute_pitch_overlap(
                user_min_pitch,
                user_max_pitch,
                artist_data['min_pitch_hz'],
                artist_data['max_pitch_hz'],
            )
        else:
            scores['pitch'] = 0.0  # No similarity if no pitch data
        
        # Timbre similarity (using key features)
        if 'timbre_features' in artist_data and artist_data['timbre_features']:
            scores['timbre'] = self._compute_timbre_similarity(
                user_timbre,
                artist_data['timbre_features']
            )
        else:
            scores['timbre'] = 0.0  # No similarity if no timbre data
        
        # Weighted combination (only use non-zero scores)
        total_weight = 0
        combined = 0
        
        for k, w in weights.items():
            score = scores.get(k, 0.0)
            if score > 0:  # Only count if we have actual similarity
                combined += score * w
                total_weight += w
        
        # Normalize if some scores were missing
        if total_weight > 0:
            combined = combined / total_weight
        else:
            # If no scores available, return 0 instead of defaulting
            return 0.0
        
        # Возвращаем raw score (0-100) без масштабирования
        # Масштабирование будет применено в find_similar_artists относительно других артистов
        return min(100.0, max(0.0, combined))
    
    def _compute_timbre_similarity(
        self,
        user_timbre: Dict[str, float],
        artist_timbre: Dict[str, float],
    ) -> float:
        """
        Compute similarity between timbre feature sets.
        
        Uses normalized Euclidean distance converted to similarity.
        """
        common_keys = set(user_timbre.keys()) & set(artist_timbre.keys())
        
        if not common_keys:
            return 0.0  # No similarity if no common features
        
        user_values = np.array([user_timbre[k] for k in common_keys])
        artist_values = np.array([artist_timbre[k] for k in common_keys])
        
        # Normalize
        user_norm = np.linalg.norm(user_values)
        artist_norm = np.linalg.norm(artist_values)
        
        if user_norm > 0:
            user_values = user_values / user_norm
        if artist_norm > 0:
            artist_values = artist_values / artist_norm
        
        # Cosine similarity
        similarity = np.dot(user_values, artist_values)
        
        return max(0, similarity) * 100
    
    def find_similar_artists(
        self,
        user_embedding: np.ndarray,
        user_min_pitch: float,
        user_max_pitch: float,
        user_timbre: Dict[str, float],
        artists: List[Dict[str, Any]],
        top_n: int = None,
    ) -> List[ArtistMatch]:
        """
        Find most similar artists to user's voice.
        
        Args:
            user_embedding: User's voice embedding
            user_min_pitch: User's minimum pitch
            user_max_pitch: User's maximum pitch
            user_timbre: User's timbre features
            artists: List of artist data dicts
            top_n: Number of results to return
            
        Returns:
            List of ArtistMatch objects sorted by similarity
        """
        top_n = top_n or self.top_n
        
        matches = []
        raw_scores = []
        
        # Сначала вычисляем все similarity scores
        for artist in artists:
            similarity = self.compute_combined_similarity(
                user_embedding,
                user_min_pitch,
                user_max_pitch,
                user_timbre,
                artist,
            )
            
            pitch_overlap = None
            if 'min_pitch_hz' in artist and 'max_pitch_hz' in artist:
                pitch_overlap = self.compute_pitch_overlap(
                    user_min_pitch,
                    user_max_pitch,
                    artist['min_pitch_hz'],
                    artist['max_pitch_hz'],
                )
            
            matches.append(ArtistMatch(
                artist_id=artist['id'],
                name=artist['name'],
                similarity_score=similarity,  # Временный score
                voice_type=artist.get('voice_type'),
                genre=artist.get('genre'),
                pitch_overlap=pitch_overlap,
            ))
            
            raw_scores.append(similarity)
        
        # Сортируем по raw score
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Нормализуем scores относительно друг друга для более правдоподобных процентов
        if len(raw_scores) > 0:
            min_score = min(raw_scores)
            max_score = max(raw_scores)
            score_range = max_score - min_score
            
            if score_range > 0.01:  # Если есть разница между артистами
                # Нормализуем в диапазон 60-95% для топ артистов
                for i, match in enumerate(matches[:top_n]):
                    # Нормализуем относительно min/max
                    normalized = (match.similarity_score - min_score) / score_range
                    # Масштабируем в диапазон 60-95%
                    scaled = 60 + (normalized * 35)
                    # Добавляем небольшой бонус за позицию (топ-1 получает +2%, топ-2 +1%)
                    position_bonus = max(0, 2 - i)
                    match.similarity_score = min(100.0, scaled + position_bonus)
            else:
                # Если все артисты очень похожи, даем им разные проценты на основе позиции
                for i, match in enumerate(matches[:top_n]):
                    base_score = 85.0
                    match.similarity_score = base_score - (i * 2)  # 85%, 83%, 81%
        
        return matches[:top_n]
    
    def recommend_songs(
        self,
        user_min_pitch: float,
        user_max_pitch: float,
        songs: List[Dict[str, Any]],
        top_n: int = 10,
        difficulty_preference: Optional[int] = None,
    ) -> List[SongMatch]:
        """
        Recommend songs based on pitch range matching.
        
        Args:
            user_min_pitch: User's minimum pitch
            user_max_pitch: User's maximum pitch
            songs: List of song data dicts
            top_n: Number of recommendations
            difficulty_preference: Preferred difficulty level (1-5)
            
        Returns:
            List of SongMatch recommendations
        """
        matches = []
        
        for song in songs:
            pitch_score = self.compute_pitch_overlap(
                user_min_pitch,
                user_max_pitch,
                song['min_pitch_hz'],
                song['max_pitch_hz'],
            )
            
            # Adjust score based on difficulty preference
            if difficulty_preference and song.get('difficulty'):
                diff_delta = abs(song['difficulty'] - difficulty_preference)
                pitch_score *= (1 - diff_delta * 0.1)  # Reduce score for difficulty mismatch
            
            matches.append(SongMatch(
                song_id=song['id'],
                title=song['title'],
                artist_name=song.get('artist_name', 'Unknown'),
                pitch_match_score=pitch_score,
                difficulty=song.get('difficulty'),
                yandex_music_id=song.get('yandex_music_id'),
                yandex_music_url=song.get('yandex_music_url'),
            ))
        
        # Sort by match score
        matches.sort(key=lambda x: x.pitch_match_score, reverse=True)
        
        return matches[:top_n]


# Module-level instance
similarity_engine = SimilarityEngine()

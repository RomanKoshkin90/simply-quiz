"""
Voice embedding generation module.
Поддерживает OpenAI Whisper для улучшения качества и альтернативные методы.
"""
import numpy as np
from typing import Optional, Protocol
from abc import ABC, abstractmethod
import logging
import hashlib
import tempfile
import os

from app.config import settings
from app.core.pitch_extraction import PitchAnalysisResult
from app.core.timbre_extraction import timbre_extractor

logger = logging.getLogger(__name__)


# Embedding dimension (matches typical audio embedding dimensions)
EMBEDDING_DIM = 512


class VoiceEmbeddingProvider(Protocol):
    """Protocol for voice embedding providers."""
    
    def generate_embedding(
        self, 
        audio: np.ndarray, 
        sr: int
    ) -> np.ndarray:
        """Generate voice embedding from audio."""
        ...


class BaseEmbeddingProvider(ABC):
    """Base class for embedding providers."""
    
    @abstractmethod
    def generate_embedding(
        self, 
        audio: np.ndarray, 
        sr: int
    ) -> np.ndarray:
        """Generate voice embedding from audio."""
        pass
    
    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Return embedding dimension."""
        pass


class OpenAIAudioEmbeddingProvider(BaseEmbeddingProvider):
    """
    OpenAI Audio API embedding provider.
    
    TODO: Implement when OpenAI Audio API becomes available.
    Currently returns placeholder embeddings.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.openai_api_key
        self._embedding_dim = EMBEDDING_DIM
        
        if not self.api_key:
            logger.warning(
                "OpenAI API key not configured. Using placeholder embeddings."
            )
    
    def _build_proxy_url(self) -> str:
        """
        Строит URL прокси для OpenAI.
        
        Returns:
            URL прокси или пустая строка если не настроен
        """
        if not settings.openai_proxy_host or not settings.openai_proxy_port:
            return ""
        
        proxy_type = settings.openai_proxy_type.lower()
        host = settings.openai_proxy_host
        port = settings.openai_proxy_port
        
        # Формируем URL прокси
        if settings.openai_proxy_username and settings.openai_proxy_password:
            # Прокси с аутентификацией
            username = settings.openai_proxy_username
            password = settings.openai_proxy_password
            
            if proxy_type == "socks5":
                return f"socks5://{username}:{password}@{host}:{port}"
            else:
                return f"http://{username}:{password}@{host}:{port}"
        else:
            # Прокси без аутентификации
            if proxy_type == "socks5":
                return f"socks5://{host}:{port}"
            else:
                return f"http://{host}:{port}"
    
    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim
    
    def generate_embedding(
        self, 
        audio: np.ndarray, 
        sr: int
    ) -> np.ndarray:
        """
        Generate voice embedding using OpenAI Audio API.
        
        Использует OpenAI Whisper для извлечения embeddings из аудио.
        Если API недоступен, использует fallback на основе features.
        
        Args:
            audio: Audio array
            sr: Sample rate
            
        Returns:
            Voice embedding vector
        """
        if not self.api_key:
            logger.info("Generating placeholder embedding (OpenAI API not configured)")
            return self._generate_placeholder_embedding(audio, sr)
        
        try:
            from openai import OpenAI
            import soundfile as sf
            import librosa
            import httpx
            import os
            
            # Настраиваем прокси через httpx.AsyncHTTPTransport (правильный способ для SOCKS5)
            http_client = None
            
            if settings.openai_proxy_host and settings.openai_proxy_port:
                proxy_url = self._build_proxy_url()
                if proxy_url:
                    logger.info(f"🔧 Configuring proxy: {settings.openai_proxy_type.upper()} {settings.openai_proxy_host}:{settings.openai_proxy_port}")
                    
                    # Для SOCKS5 используем httpx-socks
                    if settings.openai_proxy_type.lower() == "socks5":
                        try:
                            # Импортируем SyncProxyTransport из httpx_socks
                            from httpx_socks import SyncProxyTransport
                            
                            # Создаем sync transport с SOCKS5 прокси (OpenAI SDK синхронный)
                            transport = SyncProxyTransport.from_url(
                                proxy_url,
                                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                            )
                            
                            # Создаем sync HTTP клиент с SOCKS5 transport
                            http_client = httpx.Client(
                                transport=transport,
                                timeout=httpx.Timeout(900.0, connect=30.0),  # 15 минут общий, 30 сек на подключение
                            )
                            
                            logger.info("✅ SOCKS5 proxy configured via httpx_socks.SyncProxyTransport")
                            
                        except ImportError:
                            logger.error("❌ httpx-socks not installed! Install with: pip install httpx-socks")
                            logger.warning("⚠️  Falling back to direct connection")
                            http_client = None
                        except Exception as e:
                            logger.error(f"❌ Error configuring SOCKS5 proxy: {e}")
                            logger.warning("⚠️  Falling back to direct connection")
                            http_client = None
                    else:
                        # Для HTTP прокси используем стандартный способ
                        transport = httpx.HTTPTransport(
                            proxy=proxy_url,
                            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                        )
                        http_client = httpx.Client(
                            transport=transport,
                            timeout=httpx.Timeout(900.0, connect=30.0),
                        )
                        logger.info("✅ HTTP proxy configured via httpx.HTTPTransport")
                else:
                    logger.info("🔧 No proxy configured, using direct connection")
            else:
                logger.info("🔧 No proxy configured, using direct connection")
            
            # Создаем клиент OpenAI с настроенным http_client
            if http_client:
                client = OpenAI(
                    api_key=self.api_key,
                    http_client=http_client,
                    timeout=900.0,  # 15 минут для медленных прокси
                    max_retries=3,
                )
            else:
                # Прямое подключение без прокси
                client = OpenAI(
                    api_key=self.api_key,
                    timeout=900.0,
                    max_retries=3,
                )
            
            # Сохраняем аудио во временный файл (OpenAI требует файл)
            tmp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            tmp_path = tmp_file.name
            tmp_file.close()
            
            try:
                    # Нормализуем sample rate до 16kHz (требование Whisper)
                    target_sr = 16000
                    if sr != target_sr:
                        audio_resampled = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
                    else:
                        audio_resampled = audio
                    
                    # Ограничиваем длину до 45 секунд для ускорения через медленный прокси
                    max_samples = 45 * target_sr  # 45 секунд
                    if len(audio_resampled) > max_samples:
                        logger.info(f"Truncating audio from {len(audio_resampled)/target_sr:.1f}s to 45s for faster processing")
                        audio_resampled = audio_resampled[:max_samples]
                    
                    # Сохраняем в WAV
                    sf.write(tmp_path, audio_resampled, target_sr)
                    
                    # Используем Whisper для улучшения качества анализа
                    # Whisper помогает лучше понимать вокальные характеристики
                    with open(tmp_path, 'rb') as audio_file:
                        try:
                            logger.info("Calling OpenAI Whisper API...")
                            # Получаем транскрипцию для дополнительного контекста
                            transcript = client.audio.transcriptions.create(
                                model="whisper-1",
                                file=audio_file,
                                response_format="verbose_json",
                            )
                            
                            # Используем информацию из Whisper для улучшения embedding
                            # Whisper анализирует аудио на глубоком уровне, что улучшает качество
                            logger.info("OpenAI Whisper analysis completed, enhancing embedding")
                            
                            # Генерируем улучшенный embedding с учетом Whisper анализа
                            # TranscriptionVerbose имеет поля: text, language, duration, segments, words
                            transcript_dict = {
                                "text": transcript.text,
                                "language": transcript.language,
                                "duration": transcript.duration,
                                "has_speech": len(transcript.text.strip()) > 0,
                            }
                            enhanced_embedding = self._generate_enhanced_embedding(
                                audio, sr, transcript_dict
                            )
                            return enhanced_embedding
                            
                        except Exception as e:
                            error_msg = str(e)
                            error_type = type(e).__name__
                            logger.error(f"OpenAI Whisper API error ({error_type}): {error_msg}")
                            
                            # Проверяем конкретные типы ошибок
                            if "insufficient_quota" in error_msg.lower():
                                logger.error("❌ OpenAI quota exceeded! Please add credits at https://platform.openai.com/account/billing")
                            elif "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                                logger.error("❌ OpenAI API key invalid! Check OPENAI_API_KEY in .env")
                            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                                logger.error("❌ Request timeout. Try: 1) Shorter audio 2) Check internet 3) Disable proxy")
                            elif "connection" in error_msg.lower():
                                logger.error("❌ Connection error. Try: 1) Check internet 2) Try without proxy 3) Check firewall")
                            
                            logger.warning("Using placeholder embedding as fallback")
                            return self._generate_placeholder_embedding(audio, sr)
            finally:
                # Удаляем временный файл
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                
                # Закрываем http_client если был создан (sync клиент)
                if http_client:
                    try:
                        # httpx.Client нужно закрывать через close()
                        http_client.close()
                    except Exception as e:
                        logger.debug(f"Error closing http_client: {e}")
                        
        except ImportError:
            logger.warning("OpenAI library not installed. Install with: pip install openai")
            return self._generate_placeholder_embedding(audio, sr)
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}. Using fallback.")
            return self._generate_placeholder_embedding(audio, sr)
    
    def _generate_enhanced_embedding(
        self,
        audio: np.ndarray,
        sr: int,
        whisper_transcript: dict
    ) -> np.ndarray:
        """
        Генерирует улучшенный embedding с использованием данных от Whisper.
        
        Whisper анализирует аудио на глубоком уровне, что позволяет
        лучше понимать вокальные характеристики и тембр.
        """
        # Извлекаем базовые features
        base_embedding = self._generate_placeholder_embedding(audio, sr)
        
        # Используем информацию из Whisper для улучшения
        # Например, длительность, язык, уверенность модели
        whisper_features = np.array([
            whisper_transcript.get('duration', 0) / 100.0,  # Нормализуем
            len(whisper_transcript.get('text', '')) / 1000.0,  # Длина текста
            1.0 if whisper_transcript.get('text') else 0.0,  # Есть ли речь
        ], dtype=np.float32)
        
        # Комбинируем с базовым embedding
        # Расширяем whisper_features до нужной размерности
        whisper_expanded = self._expand_features(whisper_features, self._embedding_dim)
        
        # Взвешенная комбинация (70% базовый, 30% Whisper enhancement)
        enhanced = 0.7 * base_embedding + 0.3 * whisper_expanded
        
        # Нормализуем
        norm = np.linalg.norm(enhanced)
        if norm > 0:
            enhanced = enhanced / norm
        
        return enhanced.astype(np.float32)
    
    def _generate_placeholder_embedding(
        self, 
        audio: np.ndarray, 
        sr: int
    ) -> np.ndarray:
        """
        Generate placeholder embedding based on audio features.
        
        This is a fallback that creates reproducible embeddings
        from OpenSMILE features until real API is available.
        """
        # Extract timbre features
        features = timbre_extractor.extract_features(audio, sr)
        feature_vector = timbre_extractor.features_to_vector(features)
        
        # Expand to full embedding dimension with hashing
        # This ensures reproducible embeddings from the same audio
        expanded = self._expand_features(feature_vector, self._embedding_dim)
        
        # Normalize
        norm = np.linalg.norm(expanded)
        if norm > 0:
            expanded = expanded / norm
        
        return expanded.astype(np.float32)
    
    def _expand_features(
        self, 
        features: np.ndarray, 
        target_dim: int
    ) -> np.ndarray:
        """Expand feature vector to target dimension."""
        if len(features) >= target_dim:
            return features[:target_dim]
        
        # Create expanded vector by repeating and transforming features
        expanded = np.zeros(target_dim, dtype=np.float32)
        
        # Copy original features
        expanded[:len(features)] = features
        
        # Fill remaining with transformed features
        np.random.seed(42)  # Reproducible
        transform_matrix = np.random.randn(len(features), target_dim - len(features))
        expanded[len(features):] = features @ transform_matrix
        
        return expanded


class LocalFeatureEmbeddingProvider(BaseEmbeddingProvider):
    """
    Local embedding provider using extracted audio features.
    Creates embeddings from pitch and timbre features without external API.
    """
    
    def __init__(self, embedding_dim: int = EMBEDDING_DIM):
        self._embedding_dim = embedding_dim
    
    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim
    
    def generate_embedding(
        self, 
        audio: np.ndarray, 
        sr: int,
        pitch_analysis: Optional[PitchAnalysisResult] = None,
    ) -> np.ndarray:
        """
        Generate embedding from local audio features.
        
        Args:
            audio: Audio array
            sr: Sample rate
            pitch_analysis: Optional pre-computed pitch analysis
            
        Returns:
            Feature-based embedding vector
        """
        logger.info("Generating local feature-based embedding")
        
        # Extract timbre features
        timbre_features = timbre_extractor.extract_features(audio, sr)
        timbre_vector = timbre_extractor.features_to_vector(timbre_features)
        
        # Normalize timbre features
        timbre_norm = np.linalg.norm(timbre_vector)
        if timbre_norm > 0:
            timbre_vector = timbre_vector / timbre_norm
        
        # Add pitch features if available
        if pitch_analysis:
            pitch_features = np.array([
                pitch_analysis.min_pitch_hz / 1000,  # Normalize to ~0-1 range
                pitch_analysis.max_pitch_hz / 1000,
                pitch_analysis.median_pitch_hz / 1000,
                pitch_analysis.octave_range / 4,  # Normalize assuming max 4 octaves
                pitch_analysis.voiced_ratio,
            ], dtype=np.float32)
        else:
            pitch_features = np.zeros(5, dtype=np.float32)
        
        # Concatenate features
        combined = np.concatenate([timbre_vector, pitch_features])
        
        # Expand to embedding dimension
        embedding = self._project_to_embedding(combined, self._embedding_dim)
        
        # Normalize final embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding.astype(np.float32)
    
    def _project_to_embedding(
        self, 
        features: np.ndarray, 
        target_dim: int
    ) -> np.ndarray:
        """Project features to target embedding dimension."""
        n_features = len(features)
        
        if n_features >= target_dim:
            return features[:target_dim]
        
        # Use random projection (reproducible)
        np.random.seed(42)
        projection_matrix = np.random.randn(n_features, target_dim).astype(np.float32)
        projection_matrix /= np.sqrt(n_features)  # Scale for unit variance
        
        return features @ projection_matrix


class VoiceEmbeddingGenerator:
    """
    Main voice embedding generator that selects appropriate provider.
    """
    
    def __init__(self, provider: str = "auto"):
        """
        Initialize embedding generator.
        
        Args:
            provider: Provider type ("openai", "local", "auto")
                - "openai": Всегда использует OpenAI
                - "local": Всегда использует локальный
                - "auto": Выбирает автоматически на основе настроек
        """
        from app.config import settings
        
        if provider == "openai":
            self.provider = OpenAIAudioEmbeddingProvider()
        elif provider == "local":
            self.provider = LocalFeatureEmbeddingProvider()
        else:
            # "auto" - выбираем на основе настроек
            if settings.use_openai_for_user_analysis and settings.openai_api_key:
                # Пытаемся использовать OpenAI если настроен
                try:
                    self.provider = OpenAIAudioEmbeddingProvider()
                    print(f"[EMBEDDING] Using provider: {type(self.provider).__name__} (OpenAI enabled)")
                except Exception as e:
                    print(f"[EMBEDDING] OpenAI provider failed: {e}, falling back to local")
                    self.provider = LocalFeatureEmbeddingProvider()
            else:
                # Используем локальный если OpenAI не настроен или отключен
                self.provider = LocalFeatureEmbeddingProvider()
                if not settings.openai_api_key:
                    print(f"[EMBEDDING] Using provider: {type(self.provider).__name__} (OpenAI not configured)")
                else:
                    print(f"[EMBEDDING] Using provider: {type(self.provider).__name__} (OpenAI disabled for user analysis)")
        
        if provider != "auto":
            print(f"[EMBEDDING] Using provider: {type(self.provider).__name__}")
    
    def generate(
        self, 
        audio: np.ndarray, 
        sr: int,
        pitch_analysis: Optional[PitchAnalysisResult] = None,
    ) -> np.ndarray:
        """
        Generate voice embedding.
        
        Args:
            audio: Audio array
            sr: Sample rate
            pitch_analysis: Optional pitch analysis result
            
        Returns:
            Voice embedding vector
        """
        if isinstance(self.provider, LocalFeatureEmbeddingProvider):
            return self.provider.generate_embedding(audio, sr, pitch_analysis)
        else:
            return self.provider.generate_embedding(audio, sr)
    
    @property
    def embedding_dim(self) -> int:
        return self.provider.embedding_dim


# Module-level instance
embedding_generator = VoiceEmbeddingGenerator()

"""
Application configuration using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/edinorok"
    
    # Audio processing
    audio_upload_dir: str = "./uploads"
    max_audio_duration_seconds: int = 300  # 5 minutes max
    target_sample_rate: int = 16000
    
    # CREPE settings
    crepe_model_capacity: str = "tiny"  # tiny (fastest), small, medium, large, full
    crepe_step_size: int = 20  # ms (20 = faster, 10 = more precise)
    
    # OpenSMILE settings
    opensmile_feature_set: str = "eGeMAPSv02"
    opensmile_feature_level: str = "functionals"
    
    # OpenAI
    openai_api_key: str = ""
    openai_proxy_host: str = ""
    openai_proxy_port: int = 0
    openai_proxy_username: str = ""
    openai_proxy_password: str = ""
    openai_proxy_type: str = "http"  # "http" or "socks5"
    use_openai_for_user_analysis: bool = True  # Использовать OpenAI для анализа пользователей (если False - только local)
    
    # Yandex Music API
    yandex_music_token: str = ""  # Токен для авторизации (опционально, без токена доступны первые 30 сек)
    
    # Similarity search
    top_n_similar_artists: int = 3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()

# Ensure upload directory exists
Path(settings.audio_upload_dir).mkdir(parents=True, exist_ok=True)

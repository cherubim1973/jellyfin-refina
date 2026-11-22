from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(20), index=True, nullable=False)  # 'movie', 'series', 'show'
    title = Column(String(255), index=True, nullable=False)    # Título limpo
    original_filename = Column(String(255), nullable=False)
    file_path = Column(Text, unique=True, index=True, nullable=False)
    file_size_bytes = Column(BigInteger, default=0)
    resolution = Column(String(20), default="SD")              # 4K, 1080p, 720p, SD
    year = Column(Integer, index=True, nullable=True)
    season = Column(Integer, nullable=True)                    # Para séries
    episode = Column(Integer, nullable=True)                   # Para séries
    episode_title = Column(String(255), nullable=True)
    has_subtitles = Column(Boolean, default=False, index=True)
    subtitle_paths = Column(Text, nullable=True)               # Lista em JSON de caminhos das legendas
    metadata_json = Column(Text, nullable=True)                # Cache JSON de metadados ricos (TMDB/Gemini)
    metadata_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

from pydantic import BaseModel, Field
from typing import Optional, List

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

class DirectorySettings(BaseModel):
    movie_dir: Optional[str] = ""
    series_dir: Optional[str] = ""
    shows_dir: Optional[str] = ""

class ApiSettings(BaseModel):
    gemini_api_key: Optional[str] = ""
    tmdb_api_key: Optional[str] = ""

class MediaItemOut(BaseModel):
    id: int
    category: str
    title: str
    resolution: str
    year: Optional[int] = None
    has_subtitles: bool
    file_size_bytes: int

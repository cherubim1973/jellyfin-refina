from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import MediaItem
from app.auth import require_auth
from app.templating import render_template

router = APIRouter()

def format_storage_size(bytes_val: int) -> str:
    """Formata bytes em unidade legível (MB, GB, TB)."""
    if not bytes_val or bytes_val <= 0:
        return "0 GB"
    tb = bytes_val / (1024 ** 4)
    if tb >= 1.0:
        return f"{tb:.2f} TB"
    gb = bytes_val / (1024 ** 3)
    if gb >= 1.0:
        return f"{gb:.2f} GB"
    mb = bytes_val / (1024 ** 2)
    return f"{mb:.1f} MB"

@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, user=Depends(require_auth), db: Session = Depends(get_db)):
    # Contagens por categoria
    total_movies = db.query(MediaItem).filter(MediaItem.category == "movie").count()
    total_series_episodes = db.query(MediaItem).filter(MediaItem.category == "series").count()
    total_series_shows = db.query(func.count(func.distinct(MediaItem.title))).filter(MediaItem.category == "series").scalar() or 0
    total_shows = db.query(MediaItem).filter(MediaItem.category == "show").count()
    total_items = total_movies + total_series_episodes + total_shows

    # Espaço em disco consumido
    total_bytes = db.query(func.sum(MediaItem.file_size_bytes)).scalar() or 0
    storage_formatted = format_storage_size(total_bytes)

    # AUDITOR DE ACERVO (Saúde da Biblioteca):
    no_subs_count = db.query(MediaItem).filter(MediaItem.has_subtitles == False).count()
    low_res_count = db.query(MediaItem).filter(MediaItem.resolution.in_(["SD", "480p", "576p"])).count()

    duplicate_titles_query = (
        db.query(MediaItem.title, MediaItem.year, func.count(MediaItem.id).label("count"))
        .group_by(MediaItem.title, MediaItem.year)
        .having(func.count(MediaItem.id) > 1)
        .all()
    )
    duplicates_count = sum(row.count for row in duplicate_titles_query)

    # Itens recentes para carrossel/destaque
    recent_items = (
        db.query(MediaItem)
        .order_by(MediaItem.created_at.desc())
        .limit(8)
        .all()
    )

    return render_template(request, "dashboard.html", {
        "user": user,
        "total_movies": total_movies,
        "total_series": total_series_shows,
        "total_series_episodes": total_series_episodes,
        "total_shows": total_shows,
        "total_items": total_items,
        "storage_formatted": storage_formatted,
        "no_subs_count": no_subs_count,
        "low_res_count": low_res_count,
        "duplicates_count": duplicates_count,
        "recent_items": recent_items
    })

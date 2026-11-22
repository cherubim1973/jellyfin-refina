import json
from fastapi import APIRouter, Depends, Request, Query, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from app.database import get_db
from app.models import MediaItem
from app.auth import require_auth
from app.metadata_service import get_or_update_metadata
from app.templating import render_template

router = APIRouter()

def filter_and_sort_media(
    query,
    q: str = "",
    res: str = "",
    subs: str = "",
    sort: str = "title_asc"
):
    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                MediaItem.title.ilike(search_pattern),
                MediaItem.original_filename.ilike(search_pattern)
            )
        )

    if res:
        query = query.filter(MediaItem.resolution == res)

    if subs == "with":
        query = query.filter(MediaItem.has_subtitles == True)
    elif subs == "without":
        query = query.filter(MediaItem.has_subtitles == False)

    if sort == "title_asc":
        query = query.order_by(asc(MediaItem.title))
    elif sort == "title_desc":
        query = query.order_by(desc(MediaItem.title))
    elif sort == "year_desc":
        query = query.order_by(desc(MediaItem.year).nullslast(), asc(MediaItem.title))
    elif sort == "year_asc":
        query = query.order_by(asc(MediaItem.year).nullslast(), asc(MediaItem.title))
    elif sort == "recent":
        query = query.order_by(desc(MediaItem.created_at))

    return query

@router.get("/movies", response_class=HTMLResponse)
async def list_movies(
    request: Request,
    q: str = Query("", description="Busca por título"),
    res: str = Query("", description="Filtro de resolução"),
    subs: str = Query("", description="Filtro de legendas (with/without)"),
    sort: str = Query("title_asc", description="Ordenação"),
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    base_query = db.query(MediaItem).filter(MediaItem.category == "movie")
    total_count = base_query.count()
    items = filter_and_sort_media(base_query, q, res, subs, sort).all()

    return render_template(request, "media_list.html", {
        "user": user,
        "category_title": "Filmes",
        "category": "movie",
        "items": items,
        "total_count": total_count,
        "filtered_count": len(items),
        "q": q,
        "res": res,
        "subs": subs,
        "sort": sort
    })

@router.get("/series", response_class=HTMLResponse)
async def list_series(
    request: Request,
    q: str = Query("", description="Busca por título"),
    res: str = Query("", description="Filtro de resolução"),
    subs: str = Query("", description="Filtro de legendas"),
    sort: str = Query("title_asc", description="Ordenação"),
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    base_query = db.query(MediaItem).filter(MediaItem.category == "series")
    total_count = base_query.count()
    items = filter_and_sort_media(base_query, q, res, subs, sort).all()

    return render_template(request, "media_list.html", {
        "user": user,
        "category_title": "Séries",
        "category": "series",
        "items": items,
        "total_count": total_count,
        "filtered_count": len(items),
        "q": q,
        "res": res,
        "subs": subs,
        "sort": sort
    })

@router.get("/shows", response_class=HTMLResponse)
async def list_shows(
    request: Request,
    q: str = Query("", description="Busca por título"),
    res: str = Query("", description="Filtro de resolução"),
    subs: str = Query("", description="Filtro de legendas"),
    sort: str = Query("title_asc", description="Ordenação"),
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    base_query = db.query(MediaItem).filter(MediaItem.category == "show")
    total_count = base_query.count()
    items = filter_and_sort_media(base_query, q, res, subs, sort).all()

    return render_template(request, "media_list.html", {
        "user": user,
        "category_title": "Shows & Concertos",
        "category": "show",
        "items": items,
        "total_count": total_count,
        "filtered_count": len(items),
        "q": q,
        "res": res,
        "subs": subs,
        "sort": sort
    })

@router.get("/media/{item_id}", response_class=HTMLResponse)
async def media_detail(
    item_id: int,
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item multimídia não encontrado.")

    metadata = await get_or_update_metadata(item, db)

    subtitles_list = []
    if item.subtitle_paths:
        try:
            subtitles_list = json.loads(item.subtitle_paths)
        except Exception:
            subtitles_list = []

    size_mb = round(item.file_size_bytes / (1024 * 1024), 1) if item.file_size_bytes else 0
    size_gb = round(item.file_size_bytes / (1024 * 1024 * 1024), 2) if item.file_size_bytes else 0
    formatted_size = f"{size_gb} GB ({size_mb} MB)" if size_gb >= 1.0 else f"{size_mb} MB"

    return render_template(request, "media_detail.html", {
        "user": user,
        "item": item,
        "meta": metadata,
        "subtitles_list": subtitles_list,
        "formatted_size": formatted_size
    })

@router.post("/media/{item_id}/refresh")
async def refresh_media_metadata(
    item_id: int,
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado.")

    await get_or_update_metadata(item, db, force_refresh=True)
    return RedirectResponse(url=f"/media/{item_id}", status_code=status.HTTP_303_SEE_OTHER)

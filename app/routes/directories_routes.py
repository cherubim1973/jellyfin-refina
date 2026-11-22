import os
from pathlib import Path
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Setting
from app.auth import require_auth
from app.scanner import scan_directory
from app.templating import render_template

router = APIRouter()

def get_setting_value(db: Session, key: str, default: str = "") -> str:
    s = db.query(Setting).filter(Setting.key == key).first()
    return s.value if s and s.value else default

def set_setting_value(db: Session, key: str, value: str):
    s = db.query(Setting).filter(Setting.key == key).first()
    if not s:
        s = Setting(key=key, value=value)
        db.add(s)
    else:
        s.value = value
    db.commit()

@router.get("/directories", response_class=HTMLResponse)
async def directories_page(request: Request, user=Depends(require_auth), db: Session = Depends(get_db)):
    movie_dir = get_setting_value(db, "movie_dir", "")
    series_dir = get_setting_value(db, "series_dir", "")
    shows_dir = get_setting_value(db, "shows_dir", "")

    return render_template(request, "directories.html", {
        "user": user,
        "movie_dir": movie_dir,
        "series_dir": series_dir,
        "shows_dir": shows_dir,
        "message": None,
        "scan_results": None
    })

@router.post("/directories")
async def save_directories(
    request: Request,
    movie_dir: str = Form(""),
    series_dir: str = Form(""),
    shows_dir: str = Form(""),
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    set_setting_value(db, "movie_dir", movie_dir.strip())
    set_setting_value(db, "series_dir", series_dir.strip())
    set_setting_value(db, "shows_dir", shows_dir.strip())

    return render_template(request, "directories.html", {
        "user": user,
        "movie_dir": movie_dir.strip(),
        "series_dir": series_dir.strip(),
        "shows_dir": shows_dir.strip(),
        "message": "Diretórios salvos com sucesso!",
        "scan_results": None
    })

@router.post("/directories/scan")
async def trigger_scan(
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    movie_dir = get_setting_value(db, "movie_dir", "")
    series_dir = get_setting_value(db, "series_dir", "")
    shows_dir = get_setting_value(db, "shows_dir", "")

    results = []
    if movie_dir:
        res = scan_directory("movie", movie_dir, db)
        results.append(res)
    if series_dir:
        res = scan_directory("series", series_dir, db)
        results.append(res)
    if shows_dir:
        res = scan_directory("show", shows_dir, db)
        results.append(res)

    return render_template(request, "directories.html", {
        "user": user,
        "movie_dir": movie_dir,
        "series_dir": series_dir,
        "shows_dir": shows_dir,
        "message": "Varredura concluída com sucesso!",
        "scan_results": results
    })

@router.get("/api/fs/browse")
async def browse_filesystem(
    path: str = Query("/media"),
    user=Depends(require_auth)
):
    """
    API segura para o modal do explorador visual de pastas do servidor.
    Inicia por padrão em /media onde o volume de mídia do servidor é montado.
    """
    clean_path = path.strip()
    if not clean_path:
        clean_path = "/media"

    if "\0" in clean_path:
        raise HTTPException(status_code=400, detail="Caminho inválido detectado.")

    try:
        target_path = Path(clean_path).resolve()
        # Se o caminho alvo não existir, tenta /media; se /media também não existir, cai para /
        if not target_path.exists() or not target_path.is_dir():
            media_fallback = Path("/media").resolve()
            target_path = media_fallback if media_fallback.exists() and media_fallback.is_dir() else Path("/").resolve()

        ignored_names = {".git", ".cache", "proc", "sys", "dev", ".gemini"}

        folders = []
        try:
            with os.scandir(target_path) as entries:
                for entry in entries:
                    if entry.name.startswith(".") and entry.name != ".":
                        continue
                    if entry.name in ignored_names:
                        continue
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            folders.append({
                                "name": entry.name,
                                "path": str(Path(entry.path).resolve())
                            })
                    except (PermissionError, OSError):
                        continue
        except PermissionError:
            pass

        folders.sort(key=lambda x: x["name"].lower())
        parent_path = str(target_path.parent) if target_path != target_path.parent else None

        shortcuts = []
        for candidate in ["/media", "/mnt", "/home", "/app/data", "/data", "/"]:
            p = Path(candidate)
            if p.exists() and p.is_dir():
                shortcuts.append({"name": candidate, "path": str(p.resolve())})

        return JSONResponse({
            "current_path": str(target_path),
            "parent_path": parent_path,
            "folders": folders,
            "shortcuts": shortcuts
        })
    except Exception as e:
        return JSONResponse({
            "current_path": "/",
            "parent_path": None,
            "folders": [],
            "shortcuts": [],
            "error": str(e)
        }, status_code=500)

import httpx
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Setting
from app.auth import require_auth
from app.config import GEMINI_API_KEY as ENV_GEMINI_API, TMDB_API_KEY as ENV_TMDB_API
from app.routes.directories_routes import get_setting_value, set_setting_value
from app.templating import render_template

router = APIRouter()

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    gemini_key = get_setting_value(db, "gemini_api_key", ENV_GEMINI_API)
    tmdb_key = get_setting_value(db, "tmdb_api_key", ENV_TMDB_API)

    return render_template(request, "settings.html", {
        "user": user,
        "gemini_api_key": gemini_key,
        "tmdb_api_key": tmdb_key,
        "message": None,
        "error": None
    })

@router.post("/settings")
async def save_settings(
    request: Request,
    gemini_api_key: str = Form(""),
    tmdb_api_key: str = Form(""),
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    set_setting_value(db, "gemini_api_key", gemini_api_key.strip())
    set_setting_value(db, "tmdb_api_key", tmdb_api_key.strip())

    return render_template(request, "settings.html", {
        "user": user,
        "gemini_api_key": gemini_api_key.strip(),
        "tmdb_api_key": tmdb_api_key.strip(),
        "message": "Chaves de API atualizadas com sucesso no banco de dados!",
        "error": None
    })

@router.post("/api/settings/test-tmdb")
async def test_tmdb_key(
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    key = get_setting_value(db, "tmdb_api_key", ENV_TMDB_API)
    if not key:
        return JSONResponse({"success": False, "message": "Nenhuma chave TMDB configurada."})

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(f"https://api.themoviedb.org/3/configuration?api_key={key}")
            if resp.status_code == 200:
                return JSONResponse({"success": True, "message": "Conexão com TMDB API bem-sucedida!"})
            else:
                return JSONResponse({"success": False, "message": f"TMDB retornou erro: HTTP {resp.status_code}"})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Erro de conexão com TMDB: {str(e)}"})

@router.post("/api/settings/test-gemini")
async def test_gemini_key(
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    key = get_setting_value(db, "gemini_api_key", ENV_GEMINI_API)
    if not key:
        return JSONResponse({"success": False, "message": "Nenhuma chave Gemini configurada."})

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return JSONResponse({"success": True, "message": "Conexão com Google Gemini API bem-sucedida!"})
            else:
                return JSONResponse({"success": False, "message": f"Gemini retornou erro: HTTP {resp.status_code}"})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Erro de conexão com Gemini: {str(e)}"})

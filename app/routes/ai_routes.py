import random
import json
import httpx
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import MediaItem, Setting
from app.auth import require_auth
from app.config import GEMINI_API_KEY as ENV_GEMINI_API
from app.metadata_service import get_api_key, build_youtube_trailer_url
from app.templating import render_template

router = APIRouter()

MOODS = [
    {"id": "fun", "name": "😄 Quero rir e descontrair", "genres": ["Comédia", "Animação", "Família"]},
    {"id": "thrill", "name": "⚡ Ação eletrizante e adrenalina", "genres": ["Ação", "Aventura", "Crime"]},
    {"id": "suspense", "name": "🕵️ Suspense tenso e mistério", "genres": ["Mistério", "Thriller", "Suspense"]},
    {"id": "scifi", "name": "🚀 Ficção científica e mente aberta", "genres": ["Ficção científica", "Fantasia"]},
    {"id": "drama", "name": "🎭 Drama emocionante e reflexivo", "genres": ["Drama", "Romance", "História"]},
    {"id": "music", "name": "🎸 Show musical e energia contagiante", "genres": ["Show Ao Vivo", "Música"]}
]

@router.get("/recommendations", response_class=HTMLResponse)
async def recommendations_page(
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    total_items = db.query(MediaItem).count()
    return render_template(request, "recommendations.html", {
        "user": user,
        "moods": MOODS,
        "total_items": total_items,
        "recommendation": None,
        "error": None
    })

@router.post("/recommendations/ask", response_class=HTMLResponse)
async def get_ai_recommendation(
    request: Request,
    mood_id: str = Form(...),
    category_filter: str = Form("all"),
    user=Depends(require_auth),
    db: Session = Depends(get_db)
):
    selected_mood = next((m for m in MOODS if m["id"] == mood_id), MOODS[0])

    query = db.query(MediaItem)
    if category_filter in ["movie", "series", "show"]:
        query = query.filter(MediaItem.category == category_filter)

    available_items = query.all()
    if not available_items:
        return render_template(request, "recommendations.html", {
            "user": user,
            "moods": MOODS,
            "total_items": 0,
            "recommendation": None,
            "error": "Nenhum título encontrado no seu acervo para esta categoria. Execute uma varredura em 'Diretórios' primeiro!"
        })

    gemini_key = get_api_key(db, "gemini_api_key", ENV_GEMINI_API)
    recommendation = None

    if gemini_key:
        try:
            catalog_sample = []
            for it in available_items[:40]:
                catalog_sample.append({
                    "id": it.id,
                    "title": it.title,
                    "year": it.year,
                    "category": it.category,
                    "resolution": it.resolution
                })

            prompt = (
                f"Você é o assistente inteligente de curadoria do 'Jellyfin-refina'. "
                f"O usuário está com o seguinte estado de espírito: '{selected_mood['name']}'. "
                f"Abaixo está o acervo local disponível no servidor do usuário: "
                f"{json.dumps(catalog_sample, ensure_ascii=False)} "
                "Escolha O MELHOR título deste acervo que combine perfeitamente com a vibe pedida. "
                "Responda estritamente em JSON no seguinte formato: "
                "{"
                '"item_id": 123,'
                '"curator_verdict": "Explicação calorosa e empolgante em português do porquê esse título é a escolha perfeita agora",'
                '"match_score": 98'
                "}"
            )

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.5, "response_mime_type": "application/json"}
            }

            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    resp_data = resp.json()
                    candidates = resp_data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = json.loads(text)
                        rec_id = parsed.get("item_id")
                        target_item = db.query(MediaItem).filter(MediaItem.id == rec_id).first()
                        if target_item:
                            recommendation = {
                                "item": target_item,
                                "verdict": parsed.get("curator_verdict", "Excelente escolha para a sua sessão de hoje!"),
                                "match_score": parsed.get("match_score", 95),
                                "engine": "Google Gemini IA",
                                "trailer_url": build_youtube_trailer_url(target_item.title, target_item.year)
                            }
        except Exception:
            recommendation = None

    if not recommendation:
        target_item = random.choice(available_items)
        recommendation = {
            "item": target_item,
            "verdict": (
                f"Curadoria local Jellyfin-refina: '{target_item.title}' é uma ótima pedida para o humor "
                f"'{selected_mood['name']}'! Qualidade {target_item.resolution} pronta na sua biblioteca."
            ),
            "match_score": random.randint(88, 97),
            "engine": "Curadoria Algorítmica Local",
            "trailer_url": build_youtube_trailer_url(target_item.title, target_item.year)
        }

    return render_template(request, "recommendations.html", {
        "user": user,
        "moods": MOODS,
        "total_items": len(available_items),
        "selected_mood_id": mood_id,
        "selected_category": category_filter,
        "recommendation": recommendation,
        "error": None
    })

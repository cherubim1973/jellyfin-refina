import json
import urllib.parse
from datetime import datetime
import httpx
from sqlalchemy.orm import Session
from app.config import GEMINI_API_KEY as ENV_GEMINI_API, TMDB_API_KEY as ENV_TMDB_API
from app.models import Setting, MediaItem

def get_api_key(db: Session, key_name: str, env_fallback: str) -> str:
    """Busca chave de API no banco de dados primeiro, com fallback para variável de ambiente."""
    setting = db.query(Setting).filter(Setting.key == key_name).first()
    if setting and setting.value and setting.value.strip():
        return setting.value.strip()
    return env_fallback.strip()

def build_youtube_trailer_url(title: str, year: int | None = None, trailer_key: str | None = None) -> str:
    """Retorna URL direta do trailer no YouTube ou URL de busca precisa do trailer oficial."""
    if trailer_key:
        return f"https://www.youtube.com/watch?v={trailer_key}"
    query = f"{title} {year or ''} trailer oficial official trailer".strip()
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"

async def fetch_tmdb_metadata(title: str, year: int | None, category: str, api_key: str) -> dict | None:
    """Busca metadados na API oficial do TMDB (The Movie Database)."""
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # Seleciona endpoint de busca conforme categoria
            search_endpoint = "tv" if category == "series" else "movie"
            params = {
                "api_key": api_key,
                "query": title,
                "language": "pt-BR",
                "include_adult": "false"
            }
            if year:
                if category == "series":
                    params["first_air_date_year"] = str(year)
                else:
                    params["year"] = str(year)

            url = f"https://api.themoviedb.org/3/search/{search_endpoint}"
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return None

            data = resp.json()
            results = data.get("results", [])
            if not results:
                # Tenta sem o ano se não encontrar
                if year:
                    params.pop("year", None)
                    params.pop("first_air_date_year", None)
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        results = resp.json().get("results", [])

            if not results:
                return None

            best_match = results[0]
            tmdb_id = best_match.get("id")

            # Busca detalhes completos com vídeos e créditos
            detail_url = f"https://api.themoviedb.org/3/{search_endpoint}/{tmdb_id}"
            detail_resp = await client.get(
                detail_url,
                params={"api_key": api_key, "language": "pt-BR", "append_to_response": "videos,credits"}
            )
            detail_data = detail_resp.json() if detail_resp.status_code == 200 else best_match

            # Se a sinopse em PT-BR estiver vazia, tenta em inglês
            overview = detail_data.get("overview")
            if not overview:
                en_resp = await client.get(
                    detail_url,
                    params={"api_key": api_key, "language": "en-US"}
                )
                if en_resp.status_code == 200:
                    overview = en_resp.json().get("overview", "")

            # Extração de trailer do YouTube
            trailer_key = None
            videos = detail_data.get("videos", {}).get("results", [])
            for v in videos:
                if v.get("site") == "YouTube" and v.get("type") in ["Trailer", "Teaser"]:
                    trailer_key = v.get("key")
                    break

            # Extração de elenco
            cast = []
            credits = detail_data.get("credits", {}).get("cast", [])
            for actor in credits[:8]:
                cast.append({
                    "name": actor.get("name"),
                    "character": actor.get("character"),
                    "profile_path": f"https://image.tmdb.org/t/p/w185{actor.get('profile_path')}" if actor.get("profile_path") else None
                })

            poster_path = detail_data.get("poster_path")
            backdrop_path = detail_data.get("backdrop_path")
            genres = [g.get("name") for g in detail_data.get("genres", []) if g.get("name")]

            release_date = detail_data.get("release_date") or detail_data.get("first_air_date") or ""

            return {
                "source": "tmdb",
                "tmdb_id": tmdb_id,
                "title": detail_data.get("title") or detail_data.get("name") or title,
                "original_title": detail_data.get("original_title") or detail_data.get("original_name") or "",
                "overview": overview or "Sinopse não disponível.",
                "rating": round(float(detail_data.get("vote_average", 0)), 1),
                "vote_count": detail_data.get("vote_count", 0),
                "poster_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None,
                "backdrop_url": f"https://image.tmdb.org/t/p/w1280{backdrop_path}" if backdrop_path else None,
                "genres": genres,
                "cast": cast,
                "release_date": release_date,
                "trailer_key": trailer_key,
                "trailer_url": build_youtube_trailer_url(title, year, trailer_key)
            }
    except Exception:
        return None

async def fetch_gemini_metadata(title: str, year: int | None, category: str, api_key: str) -> dict | None:
    """Utiliza a API do Google Gemini para enriquecer sinopse, curiosidades e recomendações."""
    if not api_key:
        return None

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        prompt = (
            f"Você é um curador cinematográfico sênior do sistema 'Jellyfin-refina'. "
            f"Analise a seguinte obra: '{title}' ({year or 'ano não especificado'}), categoria: {category}. "
            "Forneça uma resposta estritamente em JSON no seguinte formato: "
            "{"
            '"ai_synopsis": "Sinopse envolvente e cativante em português do Brasil",'
            '"trivia": ["Curiosidade de bastidores 1", "Curiosidade 2", "Curiosidade 3"],'
            '"why_watch": "Por que vale a pena assistir essa obra?",'
            '"similar_titles": ["Título 1", "Título 2", "Título 3"]'
            "}"
        )

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "response_mime_type": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                result = resp.json()
                candidates = result.get("candidates", [])
                if candidates:
                    content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    return json.loads(content_text)
    except Exception:
        pass
    return None

def generate_local_fallback_metadata(item: MediaItem) -> dict:
    """Gera metadados locais elegantes caso nenhuma API externa esteja disponível."""
    size_mb = round(item.file_size_bytes / (1024 * 1024), 1) if item.file_size_bytes else 0
    category_labels = {
        "movie": "Filme",
        "series": "Série",
        "show": "Show / Concerto Musical"
    }
    cat_label = category_labels.get(item.category, "Vídeo")

    default_genres = {
        "movie": ["Cinema", "Acervo Local"],
        "series": ["Série de TV", "Episódios"],
        "show": ["Show Ao Vivo", "Música"]
    }.get(item.category, ["Geral"])

    return {
        "source": "local",
        "title": item.title,
        "overview": (
            f"{cat_label} catalogado localmente na biblioteca Jellyfin-refina. "
            f"Arquivo de vídeo com resolução {item.resolution}, tamanho de {size_mb} MB "
            f"e {'com legenda SRT detectada' if item.has_subtitles else 'sem legenda SRT encontrada'}."
        ),
        "rating": 7.5,
        "vote_count": 1,
        "poster_url": None,
        "backdrop_url": None,
        "genres": default_genres,
        "cast": [],
        "release_date": str(item.year) if item.year else "Ano desconhecido",
        "trailer_key": None,
        "trailer_url": build_youtube_trailer_url(item.title, item.year),
        "trivia": [
            f"Armazenado em: {item.file_path}",
            f"Formato detectado: {item.resolution} ({item.original_filename})",
            "Indexado automaticamente pelo scanner Jellyfin-refina."
        ],
        "why_watch": "Excelente título presente na sua coleção multimídia privada pronta para streaming."
    }

async def get_or_update_metadata(item: MediaItem, db: Session, force_refresh: bool = False) -> dict:
    """Obtém os metadados do cache do banco ou busca nas APIs externas com fallback inteligente."""
    if not force_refresh and item.metadata_json:
        try:
            return json.loads(item.metadata_json)
        except Exception:
            pass

    tmdb_key = get_api_key(db, "tmdb_api_key", ENV_TMDB_API)
    gemini_key = get_api_key(db, "gemini_api_key", ENV_GEMINI_API)

    # 1. Tenta TMDB
    metadata = None
    if tmdb_key:
        metadata = await fetch_tmdb_metadata(item.title, item.year, item.category, tmdb_key)

    # 2. Se TMDB não retornou ou não está configurado, usa fallback local base
    if not metadata:
        metadata = generate_local_fallback_metadata(item)
    else:
        # Garante URL de trailer
        if not metadata.get("trailer_url"):
            metadata["trailer_url"] = build_youtube_trailer_url(item.title, item.year, metadata.get("trailer_key"))

    # 3. Enriquece com Google Gemini se configurado
    if gemini_key:
        ai_data = await fetch_gemini_metadata(item.title, item.year, item.category, gemini_key)
        if ai_data:
            metadata["gemini_enhanced"] = True
            if ai_data.get("ai_synopsis"):
                metadata["gemini_synopsis"] = ai_data["ai_synopsis"]
            if ai_data.get("trivia"):
                metadata["trivia"] = ai_data["trivia"]
            if ai_data.get("why_watch"):
                metadata["why_watch"] = ai_data["why_watch"]
            if ai_data.get("similar_titles"):
                metadata["similar_titles"] = ai_data["similar_titles"]

    # Salva em cache no SQLite
    try:
        item.metadata_json = json.dumps(metadata)
        item.metadata_updated_at = datetime.utcnow()
        db.commit()
    except Exception:
        db.rollback()

    return metadata

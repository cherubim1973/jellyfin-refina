import os
import re
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.config import VIDEO_EXTENSIONS, SUBTITLE_EXTENSIONS
from app.models import MediaItem

# Regex refinado para extrair tags indesejadas e limpar o título
# Remove qualidade, codecs, rips, grupos de release, áudios, etc.
RELEASE_TAGS = [
    r"\b(2160p|1080p|1080i|720p|576p|480p|4k|uhd)\b",
    r"\b(bluray|blu-ray|bdrip|brrip|web-dl|webrip|web|hdtv|dvdrip|dvdr|remux)\b",
    r"\b(hdr10\+|hdr10|hdr|dolby[\s\.-]?vision|dovi|dv)\b",
    r"\b(x264|x265|hevc|avc|h264|h265|xvid|divx|10bit|8bit)\b",
    r"\b(truehd|atmos|dts-hd[\s\.-]?ma|dts-hd|dts|ddp5\.1|dd5\.1|ac3|aac|eac3|mp3|flac|lpcm|2\.0|5\.1|7\.1)\b",
    r"\b(extended|remastered|unrated|directors[\s\.-]?cut|theatrical|criterion|proper|repack|dual|multi|dublado|legendado)\b",
    r"\b(yify|rarbg|yts|flux|sparks|amiable|fgt|ettv|galaxyrg|cinefile|ntb|geckos)\b",
    r"\[.*?\]",  # Conteúdo entre colchetes [exemplo]
]
COMPILED_RELEASE_REGEX = re.compile("|".join(RELEASE_TAGS), re.IGNORECASE)

# Regex para extração de ano (1900 a 2099)
YEAR_REGEX = re.compile(r"\b(19\d{2}|20\d{2})\b")

# Regex para temporada e episódio em séries: S01E02, s1e2, 1x02, etc.
SERIES_EPISODE_REGEX = re.compile(r"(?:[sS](\d{1,2})[\s\.-]?[eE](\d{1,2})|(\d{1,2})[xX](\d{1,2}))")

def detect_resolution(filename: str) -> str:
    """Identifica a resolução a partir do nome do arquivo."""
    name_lower = filename.lower()
    if any(q in name_lower for q in ["2160p", "4k", "uhd"]):
        return "4K"
    if "1080p" in name_lower or "1080i" in name_lower:
        return "1080p"
    if "720p" in name_lower:
        return "720p"
    if "480p" in name_lower or "576p" in name_lower or "dvd" in name_lower:
        return "SD"
    return "1080p"  # Resolução padrão se não identificada explicitamente

def clean_media_title(filename_without_ext: str) -> tuple[str, int | None, int | None, int | None]:
    """
    Higieniza o nome do arquivo, removendo tags de qualidade/release.
    Retorna (título_limpo, ano, temporada, episódio).
    """
    original = filename_without_ext

    # Substitui pontos, underscores e traços por espaços
    clean = re.sub(r"[\._\+]", " ", original)

    # Identificar temporada e episódio (se for série)
    season, episode = None, None
    series_match = SERIES_EPISODE_REGEX.search(clean)
    if series_match:
        if series_match.group(1) and series_match.group(2):
            season = int(series_match.group(1))
            episode = int(series_match.group(2))
        elif series_match.group(3) and series_match.group(4):
            season = int(series_match.group(3))
            episode = int(series_match.group(4))
        # Corta o título antes do marcador SxxExx
        clean = clean[:series_match.start()]

    # Identificar ano
    year = None
    year_match = YEAR_REGEX.search(clean)
    if year_match:
        year = int(year_match.group(1))
        # Se encontrou o ano, o título geralmente fica antes dele
        clean_before_year = clean[:year_match.start()].strip()
        if len(clean_before_year) > 2:
            clean = clean_before_year

    # Remove tags de release
    clean = COMPILED_RELEASE_REGEX.sub(" ", clean)

    # Remove parênteses vazios ou com lixo
    clean = re.sub(r"\(\s*\)", "", clean)
    clean = re.sub(r"\[\s*\]", "", clean)

    # Remove múltiplos espaços e hífens isolados
    clean = re.sub(r"[\-\s]+", " ", clean).strip()

    # Se ficou muito curto ou vazio, volta ao original higienizado
    if not clean or len(clean) < 2:
        clean = re.sub(r"[\._]", " ", filename_without_ext).strip()

    # Formata em Title Case suave
    return clean, year, season, episode

def find_subtitles(video_file_path: Path) -> tuple[bool, list[str]]:
    """
    Verifica se existem legendas .srt associadas na mesma pasta.
    Retorna (has_subtitles, lista_de_caminhos).
    """
    has_subtitles = False
    subtitle_paths = []

    try:
        parent_dir = video_file_path.parent
        stem = video_file_path.stem.lower()

        # 1. Checa se há arquivo com mesmo prefixo do vídeo
        for ext in SUBTITLE_EXTENSIONS:
            direct_srt = parent_dir / f"{video_file_path.stem}{ext}"
            if direct_srt.exists() and direct_srt.is_file():
                has_subtitles = True
                subtitle_paths.append(str(direct_srt))

        # 2. Varre a pasta do arquivo buscando legendas .srt que possam corresponder
        if parent_dir.exists():
            for item in parent_dir.iterdir():
                if item.is_file() and item.suffix.lower() in SUBTITLE_EXTENSIONS:
                    if str(item) not in subtitle_paths:
                        # Se tem nome parecido ou se é pasta exclusiva do filme
                        if stem in item.stem.lower() or "subs" in item.stem.lower() or "por" in item.stem.lower() or "pob" in item.stem.lower() or "eng" in item.stem.lower() or len(subtitle_paths) == 0:
                            has_subtitles = True
                            subtitle_paths.append(str(item))

            # 3. Checa subpasta comum "Subs" ou "Subtitles"
            subs_folder = parent_dir / "Subs"
            if subs_folder.exists() and subs_folder.is_dir():
                for sub_item in subs_folder.iterdir():
                    if sub_item.is_file() and sub_item.suffix.lower() in SUBTITLE_EXTENSIONS:
                        has_subtitles = True
                        subtitle_paths.append(str(sub_item))
    except Exception:
        pass

    return has_subtitles, subtitle_paths

def scan_directory(category: str, base_path_str: str, db: Session) -> dict:
    """
    Varre recursivamente um diretório de mídia e atualiza o banco de dados SQLite.
    """
    result = {
        "category": category,
        "path": base_path_str,
        "scanned_files": 0,
        "added_items": 0,
        "updated_items": 0,
        "errors": []
    }

    if not base_path_str or not os.path.exists(base_path_str):
        result["errors"].append(f"Diretório não encontrado: {base_path_str}")
        return result

    base_path = Path(base_path_str)

    try:
        for root, _, files in os.walk(base_path):
            for file_name in files:
                file_path = Path(root) / file_name
                file_ext = file_path.suffix.lower()

                if file_ext in VIDEO_EXTENSIONS:
                    result["scanned_files"] += 1
                    try:
                        file_size = file_path.stat().st_size
                        stem = file_path.stem
                        clean_title, year, season, episode = clean_media_title(stem)
                        resolution = detect_resolution(file_name)
                        has_subtitles, subtitle_paths = find_subtitles(file_path)

                        # Verifica se item já existe no banco
                        existing = db.query(MediaItem).filter(MediaItem.file_path == str(file_path)).first()

                        if existing:
                            existing.category = category
                            existing.title = clean_title
                            existing.original_filename = file_name
                            existing.file_size_bytes = file_size
                            existing.resolution = resolution
                            existing.year = year or existing.year
                            existing.season = season
                            existing.episode = episode
                            existing.has_subtitles = has_subtitles
                            existing.subtitle_paths = json.dumps(subtitle_paths)
                            result["updated_items"] += 1
                        else:
                            new_item = MediaItem(
                                category=category,
                                title=clean_title,
                                original_filename=file_name,
                                file_path=str(file_path),
                                file_size_bytes=file_size,
                                resolution=resolution,
                                year=year,
                                season=season,
                                episode=episode,
                                has_subtitles=has_subtitles,
                                subtitle_paths=json.dumps(subtitle_paths),
                                metadata_json=None
                            )
                            db.add(new_item)
                            result["added_items"] += 1
                    except Exception as e:
                        result["errors"].append(f"Erro ao processar {file_name}: {str(e)}")

        db.commit()
    except Exception as e:
        db.rollback()
        result["errors"].append(f"Erro geral durante varredura: {str(e)}")

    return result

import os
import secrets
from pathlib import Path

# Portas críticas que NÃO devem ser usadas
FORBIDDEN_PORTS = {80, 81, 443, 3000, 5055, 6767, 7878, 8096, 8191, 8989, 9000, 9091, 9696, 51413}

# Diretório base
BASE_DIR = Path(__file__).resolve().parent.parent

# Configurações de ambiente
PORT = int(os.getenv("PORT", "8585"))

# Verificação de segurança da porta
if PORT in FORBIDDEN_PORTS:
    raise ValueError(f"CRÍTICO: A porta {PORT} faz parte da lista de portas proibidas do ecossistema multimídia existente! Altere para uma porta permitida (ex: 8585).")

# Caminho do banco de dados persistente
# No container Docker será /app/data/jellyfin_refina.db
# No ambiente local de desenvolvimento, utiliza ./data/jellyfin_refina.db
DEFAULT_DATA_DIR = Path("/app/data") if Path("/app").exists() else BASE_DIR / "data"
DATABASE_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR)))
DATABASE_PATH = DATABASE_DIR / "jellyfin_refina.db"

# Chave secreta de sessão
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

# Chaves de API externas (opcionais via .env, também configuráveis via UI)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

# Extensões de vídeo suportadas
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".webm"}
SUBTITLE_EXTENSIONS = {".srt"}

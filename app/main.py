from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import PORT, FORBIDDEN_PORTS, BASE_DIR
from app.database import init_db
from app.templating import templates, templates_dir
from app.routes import (
    auth_routes,
    dashboard_routes,
    directories_routes,
    media_routes,
    ai_routes,
    settings_routes
)

def check_port_safety(port: int):
    """Verifica se a porta não está na lista de portas proibidas e alerta sobre conflitos."""
    if port in FORBIDDEN_PORTS:
        raise SystemExit(
            f"ERRO CRÍTICO DE CONFIGURAÇÃO: A porta {port} é utilizada pelo ecossistema multimídia do host. "
            f"Use PORT=8585 ou outra porta segura não conflitante."
        )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa banco de dados SQLite
    init_db()
    check_port_safety(PORT)
    yield

app = FastAPI(
    title="Jellyfin-refina",
    description="Sistema inteligente de catalogação, auditoria e curadoria de acervo multimídia",
    version="1.0.0",
    lifespan=lifespan
)

# Montagem de arquivos estáticos
static_dir = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Registra rotas
app.include_router(auth_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(directories_routes.router)
app.include_router(media_routes.router)
app.include_router(ai_routes.router)
app.include_router(settings_routes.router)

@app.get("/health")
async def health_check():
    """Endpoint de verificação de integridade para Docker e monitoramento."""
    return {"status": "healthy", "service": "jellyfin-refina", "port": PORT}

if __name__ == "__main__":
    import uvicorn
    check_port_safety(PORT)
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=False)

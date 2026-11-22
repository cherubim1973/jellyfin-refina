from fastapi import Request
from fastapi.templating import Jinja2Templates
from app.config import BASE_DIR

templates_dir = BASE_DIR / "app" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

def render_template(request: Request, name: str, context: dict | None = None, status_code: int = 200):
    """
    Renderiza um template Jinja2 garantindo compatibilidade estrita
    com todas as versões do Starlette/FastAPI.
    """
    ctx = context.copy() if context else {}
    return templates.TemplateResponse(
        request=request,
        name=name,
        context=ctx,
        status_code=status_code
    )

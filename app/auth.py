import bcrypt
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Response, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.config import SECRET_KEY
from app.database import get_db
from app.models import User

SESSION_COOKIE_NAME = "jellyfin_refina_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 dias em segundos

serializer = URLSafeTimedSerializer(SECRET_KEY, salt="jellyfin-refina-salt")

def hash_password(password: str) -> str:
    """Gera hash seguro de senha usando bcrypt com salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto puro confere com o hash bcrypt."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_session_token(username: str) -> str:
    """Cria um token assinado e seguro para o cookie de sessão."""
    return serializer.dumps({"sub": username, "ts": datetime.utcnow().isoformat()})

def decode_session_token(token: str) -> str | None:
    """Decodifica e valida o token de sessão."""
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("sub")
    except (BadSignature, SignatureExpired, Exception):
        return None

def set_auth_cookie(response: Response, username: str):
    """Configura o cookie de sessão seguro (HttpOnly, SameSite=Lax)."""
    token = create_session_token(username)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False  # Permitir em HTTP local (se HTTPS estiver configurado por proxy reverso, Lax ainda protege)
    )

def clear_auth_cookie(response: Response):
    """Remove o cookie de sessão ao fazer logout."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax"
    )

def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Retorna o usuário logado se houver cookie válido, ou None."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    username = decode_session_token(token)
    if not username:
        return None
    return db.query(User).filter(User.username == username).first()

def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependência para proteger rotas: exige usuário logado."""
    user_count = db.query(User).count()
    if user_count == 0:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/setup"}
        )
    user = get_current_user_optional(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return user

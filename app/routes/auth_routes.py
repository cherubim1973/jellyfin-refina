from fastapi import APIRouter, Depends, Request, Response, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import hash_password, verify_password, set_auth_cookie, clear_auth_cookie, get_current_user_optional
from app.templating import render_template

router = APIRouter()

@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request, db: Session = Depends(get_db)):
    # Se já existir qualquer usuário, bloqueia setup e manda para login
    if db.query(User).count() > 0:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    return render_template(request, "setup.html", {"error": None})

@router.post("/setup")
async def process_setup(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Se já existir usuário, proíbe registro
    if db.query(User).count() > 0:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    username = username.strip()
    if len(username) < 3:
        return render_template(request, "setup.html", {
            "error": "O nome de usuário deve ter pelo menos 3 caracteres."
        }, status_code=400)

    if len(password) < 6:
        return render_template(request, "setup.html", {
            "error": "A senha deve conter no mínimo 6 caracteres."
        }, status_code=400)

    if password != confirm_password:
        return render_template(request, "setup.html", {
            "error": "As senhas não coincidem. Digite novamente."
        }, status_code=400)

    hashed = hash_password(password)
    admin_user = User(username=username, hashed_password=hashed)
    db.add(admin_user)
    db.commit()

    # Redireciona para /directories após criar o admin
    redirect_resp = RedirectResponse(url="/directories", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookie(redirect_resp, username)
    return redirect_resp

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    # Se não houver usuários cadastrados, força primeiro acesso via setup
    if db.query(User).count() == 0:
        return RedirectResponse(url="/setup", status_code=status.HTTP_303_SEE_OTHER)

    # Se já estiver logado, vai direto para o dashboard
    current_user = get_current_user_optional(request, db)
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    return render_template(request, "login.html", {"error": None})

@router.post("/login")
async def process_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(User).count() == 0:
        return RedirectResponse(url="/setup", status_code=status.HTTP_303_SEE_OTHER)

    user = db.query(User).filter(User.username == username.strip()).first()

    if not user or not verify_password(password, user.hashed_password):
        return render_template(request, "login.html", {
            "error": "Usuário ou senha inválidos. Tente novamente."
        }, status_code=400)

    redirect_resp = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookie(redirect_resp, user.username)
    return redirect_resp

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_auth_cookie(response)
    return response

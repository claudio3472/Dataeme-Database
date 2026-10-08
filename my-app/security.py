"""
Variáveis de ambiente:
    SECRET_KEY              obrigatória em produção (ex.: python -c "import secrets; print(secrets.token_hex(32))")
    FLASK_DEBUG=1           só em desenvolvimento local (desliga cookie "Secure" e ativa o debugger)
    RATELIMIT_STORAGE_URI   ex.: redis://localhost:6379  (por omissão memory://, só serve para 1 processo)
    TRUST_PROXY=1           se a app estiver atrás de um proxy/reverse proxy (Nginx, Render, Railway...),
                            para o rate limiting ver o IP real do cliente
"""

import os
import secrets
from datetime import timedelta
from functools import wraps

from flask import abort, redirect, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFError, CSRFProtect

from config import supabase

DEBUG = os.environ.get("FLASK_DEBUG") == "1"

PASSWORD_MAX = 128
USERNAME_MAX = 100

csrf = CSRFProtect()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)


# ------------------------------------------------------------
# Chaves de rate limiting por conta (além do limite por IP)
# ------------------------------------------------------------

def chave_username():
    return "user:" + request.form.get("username", "").strip().lower()[:USERNAME_MAX]


def chave_email():
    return "email:" + request.form.get("email", "").strip().lower()[:254]


def chave_nif():
    return "nif:" + request.form.get("nif", "").strip()[:20]


# ------------------------------------------------------------
# Decorator para rotas de administrador
# ------------------------------------------------------------

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "id_utilizador" not in session or not session.get("is_admin", False):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ------------------------------------------------------------
# Inicialização
# ------------------------------------------------------------

def configurar_seguranca(app):
    # --- SECRET_KEY: nunca hardcoded ---
    chave = os.environ.get("SECRET_KEY")

    if not chave:
        if DEBUG:
            # Só em desenvolvimento: chave aleatória (as sessões perdem-se ao reiniciar)
            chave = secrets.token_hex(32)
            print("AVISO: SECRET_KEY não definida; a usar chave temporária (apenas dev).")
        else:
            raise RuntimeError(
                "SECRET_KEY não definida. Defina a variável de ambiente SECRET_KEY."
            )

    app.secret_key = chave

    # --- Cookie de sessão ---
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=not DEBUG,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
        WTF_CSRF_TIME_LIMIT=None,  # o token vale enquanto a sessão valer
    )

    if os.environ.get("TRUST_PROXY") == "1":
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    csrf.init_app(app)
    limiter.init_app(app)

    # --- Pedidos em excesso ---
    @app.errorhandler(429)
    def demasiados_pedidos(e):
        return (
            "Demasiados pedidos. Aguarde alguns minutos e tente novamente.",
            429,
        )

    # --- Logout forjado: um pedido de logout sem token CSRF válido ---
    # --- não termina a sessão (só volta à página inicial) ---
    @app.errorhandler(CSRFError)
    def erro_csrf(e):
        if request.endpoint == "logout":
            return redirect(url_for("home"))
        return e.description, 400

    # --- Revalidar a sessão na base de dados em cada pedido ---
    # 1) session_version: ao mudar a password, as sessões antigas (outros
    #    dispositivos) deixam de valer no pedido seguinte.
    # 2) is_admin: se um admin for despromovido ou apagado, perde o acesso
    #    logo, e não só quando a sessão expira.
    @app.before_request
    def revalidar_sessao():
        if request.endpoint in (None, "static"):
            return

        id_utilizador = session.get("id_utilizador")

        if not id_utilizador:
            return

        try:
            resposta = (
                supabase
                .table("utilizador")
                .select("is_admin, session_version")
                .eq("id_utilizador", id_utilizador)
                .limit(1)
                .execute()
            )
        except Exception:
            app.logger.exception("Falha ao revalidar a sessão")
            abort(503)

        if not resposta.data:
            session.clear()
            return

        utilizador = resposta.data[0]

        # Sessões criadas antes desta alteração não têm "sv": voltam a
        # fazer login uma vez.
        if session.get("sv") != utilizador.get("session_version"):
            session.clear()
            return

        session["is_admin"] = bool(utilizador.get("is_admin"))

    # --- Cabeçalhos de segurança básicos ---
    @app.after_request
    def cabecalhos(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        resposta.headers.setdefault("Referrer-Policy", "same-origin")

        # Páginas com formulários/sessão não devem ficar em cache
        if request.endpoint in (
            "login", "registar", "recuperar_password",
            "confirmar_codigo", "definir_password",
        ):
            resposta.headers["Cache-Control"] = "no-store"

        return resposta

    return limiter
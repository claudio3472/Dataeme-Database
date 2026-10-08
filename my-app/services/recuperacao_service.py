"""
Códigos de recuperação de password guardados NO SERVIDOR (tabela recuperacao_codigo).

Porquê: a sessão do Flask é apenas assinada, não encriptada. Guardar o código
na sessão permitia ao atacante lê-lo no próprio cookie. Agora o cookie só
contém um token aleatório sem significado; o código existe apenas como
hash na base de dados e na caixa de email do dono da conta.
"""

import hashlib
import hmac
import secrets
import time

from flask import current_app, session

from config import supabase
from services.email_service import enviar_codigo_recuperacao

TABELA = "recuperacao_codigo"

VALIDADE_SEGUNDOS = 300      # o código vale 5 minutos
MAX_TENTATIVAS = 5           # tentativas erradas antes de o código ser destruído
COOLDOWN_SEGUNDOS = 60       # intervalo mínimo entre envios para a mesma conta

# Mensagem única para qualquer falha (não revela se o token/conta existe)
MSG_CODIGO_INVALIDO = "Código inválido ou expirado."
MSG_DEMASIADAS_TENTATIVAS = "Demasiadas tentativas. Peça um novo código."


class RecuperacaoErro(ValueError):
    """Erro de validação do código, com mensagem segura para mostrar ao utilizador."""


def _hash_codigo(token, codigo):
    chave = current_app.secret_key
    if isinstance(chave, str):
        chave = chave.encode()

    return hmac.new(
        chave,
        f"{token}:{codigo}".encode(),
        hashlib.sha256
    ).hexdigest()


def _gerar_codigo():
    return f"{secrets.randbelow(1_000_000):06d}"


def _token_falso():
    """
    Para emails/NIFs inexistentes: o fluxo tem o mesmo aspeto, mas o token
    não existe na base de dados, logo nunca valida.
    """
    if "recuperacao_token" not in session:
        session["recuperacao_token"] = secrets.token_urlsafe(32)


def iniciar_recuperacao_falsa():
    _token_falso()


def iniciar_recuperacao(id_utilizador, email):
    """
    Cria um código, guarda o hash no servidor e envia-o por email.
    Devolve "enviado" ou "cooldown" (já foi enviado um código há pouco).
    Se o envio falhar, levanta a exceção (o código é apagado).
    """
    agora = int(time.time())

    # Limpeza de códigos expirados
    supabase.table(TABELA).delete().lt("expira_em", agora).execute()

    recente = (
        supabase
        .table(TABELA)
        .select("criado_em")
        .eq("id_utilizador", id_utilizador)
        .order("criado_em", desc=True)
        .limit(1)
        .execute()
    )

    if recente.data and agora - recente.data[0]["criado_em"] < COOLDOWN_SEGUNDOS:
        _token_falso()
        return "cooldown"

    # Só um código ativo por conta
    supabase.table(TABELA).delete().eq("id_utilizador", id_utilizador).execute()

    token = secrets.token_urlsafe(32)
    codigo = _gerar_codigo()

    supabase.table(TABELA).insert({
        "token": token,
        "id_utilizador": id_utilizador,
        "codigo_hash": _hash_codigo(token, codigo),
        "tentativas": 0,
        "expira_em": agora + VALIDADE_SEGUNDOS,
        "criado_em": agora,
    }).execute()

    try:
        enviar_codigo_recuperacao(email, codigo)
    except Exception:
        supabase.table(TABELA).delete().eq("token", token).execute()
        raise

    session["recuperacao_token"] = token

    return "enviado"


def _tentativas_apos_incremento(token):
    """Incremento atómico no Postgres (função SQL), imune a pedidos paralelos."""
    resposta = supabase.rpc(
        "incrementar_tentativas_recuperacao",
        {"p_token": token}
    ).execute()

    valor = resposta.data

    if isinstance(valor, list):
        valor = valor[0] if valor else None

    if isinstance(valor, dict):
        valor = next(iter(valor.values()), None)

    return valor


def validar_codigo(token, codigo):
    """
    Valida o código. Devolve o id_utilizador e destrói o código (uso único).
    Levanta RecuperacaoErro com mensagem segura em qualquer falha.
    """
    if not token or not codigo:
        raise RecuperacaoErro(MSG_CODIGO_INVALIDO)

    resposta = (
        supabase
        .table(TABELA)
        .select("*")
        .eq("token", token)
        .limit(1)
        .execute()
    )

    if not resposta.data:
        raise RecuperacaoErro(MSG_CODIGO_INVALIDO)

    registo = resposta.data[0]

    if time.time() > registo["expira_em"]:
        apagar_token(token)
        raise RecuperacaoErro(MSG_CODIGO_INVALIDO)

    tentativas = _tentativas_apos_incremento(token)

    if tentativas is None or tentativas > MAX_TENTATIVAS:
        apagar_token(token)
        raise RecuperacaoErro(MSG_DEMASIADAS_TENTATIVAS)

    esperado = registo["codigo_hash"]
    recebido = _hash_codigo(token, codigo.strip())

    if not hmac.compare_digest(esperado, recebido):
        if tentativas >= MAX_TENTATIVAS:
            apagar_token(token)
            raise RecuperacaoErro(MSG_DEMASIADAS_TENTATIVAS)

        raise RecuperacaoErro(MSG_CODIGO_INVALIDO)

    # Sucesso: uso único
    apagar_token(token)

    return registo["id_utilizador"]


def apagar_token(token):
    if token:
        supabase.table(TABELA).delete().eq("token", token).execute()
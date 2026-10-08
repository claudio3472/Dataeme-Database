from datetime import datetime, timedelta, timezone

from config import supabase, ph

# Colunas necessárias (não puxar o hash para sítios que não precisam dele)
COLUNAS_LOGIN = (
    "id_utilizador, username, password, is_admin, "
    "deve_alterar_password, prov_enviada_em, session_version"
)

# Quanto tempo uma password provisória é válida desde que foi enviada.
# Depois disto o cliente tem de usar "Esqueci-me da password".
VALIDADE_PASSWORD_PROVISORIA = timedelta(days=7)

# Hash falso: quando o utilizador não existe fazemos na mesma uma verificação
# Argon2, para que o tempo de resposta não revele se o username existe.
_HASH_FALSO = ph.hash("password-falsa-para-igualar-tempos")


def autenticar(username, password):
    """
    Verifica username + password.
    Devolve o utilizador (SEM o hash da password) ou None.
    Não distingue "utilizador não existe" de "password errada".
    """

    response = (
        supabase
        .table("utilizador")
        .select(COLUNAS_LOGIN)
        .eq("username", username)
        .limit(1)
        .execute()
    )

    if not response.data:
        try:
            ph.verify(_HASH_FALSO, password)
        except Exception:
            pass

        return None

    utilizador = response.data[0]
    hash_guardado = utilizador["password"]

    try:
        ph.verify(hash_guardado, password)

    except Exception:
        return None

    # Atualizar o hash se os parâmetros do Argon2 mudaram desde que foi criado
    try:
        if ph.check_needs_rehash(hash_guardado):
            (
                supabase
                .table("utilizador")
                .update({"password": ph.hash(password)})
                .eq("id_utilizador", utilizador["id_utilizador"])
                .execute()
            )
    except Exception:
        pass

    utilizador.pop("password", None)

    return utilizador


def provisoria_expirada(utilizador):
    """
    True se o utilizador tem uma password provisória cuja validade passou.
    Se prov_enviada_em não existir ou não for legível, não bloqueia.
    """

    if not utilizador.get("deve_alterar_password"):
        return False

    enviada_em = utilizador.get("prov_enviada_em")

    if not enviada_em:
        return False

    try:
        momento = datetime.fromisoformat(str(enviada_em).replace("Z", "+00:00"))
    except ValueError:
        return False

    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) - momento > VALIDADE_PASSWORD_PROVISORIA


def invalidar_sessoes(id_utilizador):
    """
    Incrementa a session_version do utilizador (função SQL atómica).
    Todas as sessões já abertas com a versão antiga deixam de ser aceites
    no pedido seguinte (ver revalidar_sessao em security.py).
    Devolve a nova versão, para a sessão atual a poder guardar.
    """

    resposta = supabase.rpc(
        "invalidar_sessoes",
        {"p_id_utilizador": id_utilizador}
    ).execute()

    valor = resposta.data

    if isinstance(valor, list):
        valor = valor[0] if valor else None

    if isinstance(valor, dict):
        valor = next(iter(valor.values()), None)

    if valor is None:
        raise RuntimeError("Não foi possível invalidar as sessões do utilizador.")

    return valor
import re
from datetime import datetime, timedelta, timezone

from config import supabase, ph
from load_utilizadores import gerar_password_provisoria
from services.email_service import (enviar_password_provisoria, enviar_codigo_recuperacao)
import secrets
import time

from flask import session


import secrets 

""" MUDAR PARA USAR O PRIMEIRO DIGITO DO NIF PARA ESCOLHER SE É EMPRESA OU NÃO
E AJUSTAR O NOME CONSOANTE. 
SE FOR EMPRESA TEM DE TER PESSOA DE CONTACTO """

def validar_nome(nome):
    nome = nome.strip()

    if len(nome.split()) < 2:
        raise ValueError(
            "O nome deve conter pelo menos nome e apelido."
        )

    if any(char.isdigit() for char in nome):
        raise ValueError(
            "O nome não pode conter números."
        )

    if not re.match(
        r"^[A-Za-zÀ-ÿ\s\-]+$",
        nome
    ):
        raise ValueError(
            "O nome contém caracteres inválidos."
        )
    

def validar_nif(nif):
    if not nif.isdigit() or len(nif) != 9:
        raise ValueError(
            "O NIF deve conter exatamente 9 dígitos."
        )


def validar_indicativo(indicativo):
    if not re.match(
        r"^\+\d{1,4}$",
        indicativo
    ):
        raise ValueError(
            "Indicativo internacional inválido."
        )

def validar_telefone(telefone, indicativo):
    if not telefone.isdigit():
        raise ValueError(
            "O telefone só pode conter dígitos."
        )

    if indicativo == "+351":
        if len(telefone) != 9:
            raise ValueError(
                "O telefone português deve conter exatamente 9 dígitos."
            )

        prefixos_validos = (
            "91", "92", "93", "96",
            "21", "22",
            "231", "232", "233", "234", "235", "236", "238", "239",
            "241", "242", "243", "244", "245", "249",
            "251", "252", "253", "254", "255", "256", "258", "259",
            "261", "262", "263", "265", "266", "268", "269",
            "271", "272", "273", "274", "275", "276", "277", "278",
            "281", "282", "283", "284", "285", "286", "289",
            "291", "292", "295", "296"
        )

        if not telefone.startswith(prefixos_validos):
            raise ValueError(
                "O telefone deve ser um número português válido."
            )

    else:
        if len(telefone) < 6 or len(telefone) > 15:
            raise ValueError(
                "Número de telefone internacional inválido."
            )

    
def validar_email(email):
    if not re.match(
        r"^[^@]+@[^@]+\.[^@]+$",
        email
    ):
        raise ValueError(
            "Email inválido."
        )


def validar_codigo_postal(codigo_postal):
    if not re.match(
        r"^\d{4}-\d{3}$",
        codigo_postal
    ):
        raise ValueError(
            "Código postal inválido. Exemplo: 0000-000."
        )

"""FUTURAMENTE USAR WEB SCRAPPER PARA ATRAVES DO CODIGO POSTAL PREENCHER A LOCALIZACAO"""
def validar_localizacao(localizacao):
    localizacao = localizacao.strip()

    if len(localizacao) < 3:
        raise ValueError(
            "A localização deve conter pelo menos 3 caracteres."
        )

    if any(char.isdigit() for char in localizacao):
        raise ValueError(
            "A localização não pode conter números."
        )


"""Meter campo à parte para o numero/andar"""
def validar_morada(morada):
    morada = morada.strip()

    prefixos_validos = [
        "Alameda", "AL",
        "Avenida", "AV",
        "Azinhaga", "AZ",
        "Bairro", "BR",
        "Beco", "BC",
        "Calçada", "CC",
        "Calçadinha", "CCNH",
        "Caminho", "CAM",
        "Casa", "CS",
        "Conjunto", "CJ",
        "Escadas", "ESC",
        "Escadinhas", "ESCNH",
        "Estrada", "ESTR",
        "Jardim", "JD",
        "Largo", "LG",
        "Loteamento", "LOT",
        "Lugar", "LUG",
        "Parque", "PQ",
        "Pátio", "PAT",
        "Praça", "PC",
        "Praceta", "PCT",
        "Prolongamento", "PRL",
        "Quadra", "QD",
        "Quinta", "QTA",
        "Rotunda", "ROT",
        "Rua", "R",
        "Transversal", "TRANSV",
        "Travessa", "TV",
        "Urbanização", "URB",
        "Vila", "VL",
        "Vale", "V",
        "Zona", "ZN"
    ]

    prefixo_encontrado = None

    for prefixo in prefixos_validos:
        if morada.startswith(prefixo + " "):
            prefixo_encontrado = prefixo
            break

    if prefixo_encontrado is None:
        raise ValueError(
            "A morada deve começar por Rua, Avenida, Travessa, Praceta, Largo, Alameda, etc."
        )

    resto = morada[len(prefixo_encontrado):].strip()

    if not resto:
        raise ValueError(
            "A morada deve conter um nome após o tipo de via."
        )


def validar_password(password):
    if len(password) < 8:
        raise ValueError(
            "A password deve ter pelo menos 8 caracteres."
        )

    if not any(c.isupper() for c in password):
        raise ValueError(
            "A password deve conter pelo menos uma letra maiúscula."
        )

    if not any(c.islower() for c in password):
        raise ValueError(
            "A password deve conter pelo menos uma letra minúscula."
        )

    if not any(c.isdigit() for c in password):
        raise ValueError(
            "A password deve conter pelo menos um número."
        )


def validar_numero_cliente(numero):
    if not numero.isdigit() or int(numero) <= 0:
        raise ValueError(
            "O número de cliente deve ser um número inteiro positivo."
        )


def verificar_duplicados(nif, email, numero_cliente=None):
    if numero_cliente is not None:
        numero_existe = (
            supabase
            .table("cliente")
            .select("numero_cliente")
            .eq("numero_cliente", numero_cliente)
            .execute()
        )

        if numero_existe.data:
            raise ValueError(
                "Já existe um cliente com esse número de cliente."
            )

    nif_existe = (
        supabase
        .table("cliente")
        .select("nif")
        .eq("nif", nif)
        .execute()
    )

    if nif_existe.data:
        raise ValueError(
            "Já existe um cliente com esse NIF."
        )

    email_existe = (
        supabase
        .table("cliente")
        .select("email")
        .eq("email", email)
        .execute()
    )

    if email_existe.data:
        raise ValueError(
            "Já existe um cliente com esse email."
        )

    utilizador_existe = (
        supabase
        .table("utilizador")
        .select("username")
        .eq("username", nif)
        .execute()
    )

    if utilizador_existe.data:
        raise ValueError(
            "Já existe um utilizador com esse NIF."
        )


def verificar_username_disponivel(username):
    utilizador_existe = (
        supabase
        .table("utilizador")
        .select("username")
        .eq("username", username)
        .execute()
    )

    if utilizador_existe.data:
        raise ValueError(
            "Já existe um utilizador com esse nome de utilizador."
        )


def registar_cliente_web(form, admin=False, permitir_numero_manual=False):
    nome = form["nome"].strip()
    password = form["password"]

    if admin == False:

        confirmar_password = form["confirmar_password"]

        nif = form["nif"].strip()
        morada = form["morada"].strip()
        email = form["email"].strip().lower()
        indicativo = form["ind"].strip()
        telefone = form["tel"].strip()
        codigo_postal = form["postal"].strip()
        localizacao = form["local"].strip()
        predio = form["predio"]
        andar = form["andar"].strip()

        # Número de cliente: automático, a não ser que um admin o defina.
        numero_cliente = None

        if permitir_numero_manual:
            numero_cliente = (form.get("numero_cliente") or "").strip() or None

        if numero_cliente is not None:
            validar_numero_cliente(numero_cliente)
            numero_cliente = int(numero_cliente)

        validar_nif(nif)
        validar_indicativo(indicativo)
        validar_telefone(
            telefone,
            indicativo
        )
        validar_email(email)
        validar_codigo_postal(codigo_postal)
        validar_localizacao(localizacao)
        validar_morada(morada)
        verificar_duplicados(
                nif,
                email,
                numero_cliente
            )

    else:
        verificar_username_disponivel(nome)

    validar_nome(nome)

    validar_password(password)

    if admin == False and password != confirmar_password:

        raise ValueError(
            "A nova password não corresponde com a confirmação da password."
        )

    password_hash = ph.hash(password)

    if admin == False:

        utilizador = {
            "username": nif,
            "password": password_hash,
            "is_admin": admin
        }

    else:
        utilizador = {
            "username": nome,
            "password": password_hash,
            "is_admin": admin
        }

    response = (
        supabase
        .table("utilizador")
        .insert(utilizador)
        .execute()
    )
   

    id_utilizador = response.data[0]["id_utilizador"]

    if admin == False:
        if not predio:
            morada_completa = morada
        elif not andar:
            morada_completa = f"{morada}, {predio}"
        else:
            morada_completa = f"{morada}, {predio}, {andar}"

        cliente = {
            "nif": nif,
            "nome": nome,
            "morada": morada_completa,
            "email": email,
            "telefone": int(telefone),
            "codigo_postal": codigo_postal,
            "localizacao": localizacao,
            "indicativo": indicativo,
            "id_utilizador": id_utilizador
        }

        # Se não for enviado, a base de dados gera o número automaticamente
        if numero_cliente is not None:
            cliente["numero_cliente"] = numero_cliente

        (
            supabase
            .table("cliente")
            .insert(cliente)
            .execute()
        )

    return True

def obter_cliente(id_utilizador):
    response = (
        supabase
        .table("cliente")
        .select("*")
        .eq(
            "id_utilizador",
            id_utilizador
        )
        .execute()
    )

    if not response.data:
        return None

    cliente = response.data[0]

    morada_completa = cliente["morada"].split(", ")

    tamanho = len(morada_completa)

    morada = morada_completa[0] if tamanho > 0 else ''
    predio = morada_completa[1] if tamanho > 1 else ''
    andar = morada_completa[2] if tamanho > 2  else ''

    return {
        "id_cliente": cliente["id_cliente"],
        "numero_cliente": cliente["numero_cliente"],
        "nif": cliente["nif"],
        "nome": cliente["nome"],
        "morada": morada,
        "predio": predio,
        "andar": andar,
        "email": cliente["email"],
        "tel": cliente["telefone"],
        "postal": cliente["codigo_postal"],
        "local": cliente["localizacao"],
        "indicativo": cliente["indicativo"]
    }

def obter_cliente_por_email(email):

    response = (
        supabase
        .table("cliente")
        .select("*")
        .eq(
            "email",
            email
        )
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


# ============================================================
# CONTAS CRIADAS PELO ADMIN (password provisória)
# ============================================================

COOLDOWN_PASSWORD_PROVISORIA = timedelta(minutes=10)
DOMINIO_EMAIL_FALSO = "@dataeme.invalid"


def _mascarar_email(email):
    nome, _, dominio = email.partition("@")
    return f"{nome[:1]}***@{dominio}"


def tratar_registo_conta_pre_criada(nif):
    """
    Chamar no registo. Se o NIF pertencer a uma conta criada pelo admin
    que ainda não foi ativada, envia um código de recuperação para o email
    guardado na ficha do cliente (nunca para um email escrito no formulário).

    O código usa a sessão e a rota existente /confirmar-codigo para o cliente
    definir uma password nova. A password existente nunca é desencriptada
    nem enviada por email.

    Devolve (estado, email_mascarado):
        (None, None)       -> não é uma conta pré-criada; seguir o registo normal
        ("enviado", email) -> código enviado para a conta pré-criada
        ("sem_email", None)-> a conta não tem um email válido
    """

    resposta_utilizador = (
        supabase
        .table("utilizador")
        .select("id_utilizador, deve_alterar_password")
        .eq("username", nif)
        .limit(1)
        .execute()
    )

    if not resposta_utilizador.data:
        return None, None

    utilizador = resposta_utilizador.data[0]

    if not utilizador.get("deve_alterar_password"):
        return None, None

    resposta_cliente = (
        supabase
        .table("cliente")
        .select("nome, email")
        .eq("id_utilizador", utilizador["id_utilizador"])
        .limit(1)
        .execute()
    )

    if not resposta_cliente.data:
        return None, None

    cliente = resposta_cliente.data[0]
    email = (cliente.get("email") or "").strip()

    if not email or email.endswith(DOMINIO_EMAIL_FALSO):
        return "sem_email", None

    email_mascarado = _mascarar_email(email)
    codigo = str(secrets.randbelow(900000) + 100000)

    # A página confirmar_codigo() existente usa estas chaves para validar
    # o código e guardar a password escolhida pelo cliente.
    session["recuperacao_codigo"] = codigo
    session["recuperacao_id_utilizador"] = utilizador["id_utilizador"]
    session["recuperacao_email"] = email
    session["recuperacao_expira"] = time.time() + 300

    try:
        enviar_codigo_recuperacao(email, codigo)
    except Exception:
        session.pop("recuperacao_codigo", None)
        session.pop("recuperacao_id_utilizador", None)
        session.pop("recuperacao_email", None)
        session.pop("recuperacao_expira", None)
        raise

    return "enviado", email_mascarado

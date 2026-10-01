import csv
import os
import secrets
import string
from datetime import datetime

import pandas as pd
from config import supabase, ph


# ============================================================
# PASSWORD PROVISÓRIA
# ============================================================
# A parte aleatória tem sempre pelo menos 1 maiúscula, 1 minúscula
# e 1 número (cumpre as regras de validar_password), e não usa
# caracteres que se confundem (O/0, I/l/1) para ser fácil de ditar.

PREFIXO_PASSWORD = "ProvDE-"     # <- parte fixa
TAMANHO_ALEATORIO = 8             # <- quantos caracteres aleatórios

MAIUSCULAS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
MINUSCULAS = "abcdefghijkmnopqrstuvwxyz"
NUMEROS = "23456789"


def gerar_password_provisoria():

    # Garante pelo menos um de cada tipo
    caracteres = [
        secrets.choice(MAIUSCULAS),
        secrets.choice(MINUSCULAS),
        secrets.choice(NUMEROS)
    ]

    # Preenche o resto com uma mistura dos três
    todos = MAIUSCULAS + MINUSCULAS + NUMEROS

    caracteres += [
        secrets.choice(todos)
        for _ in range(TAMANHO_ALEATORIO - len(caracteres))
    ]

    # Baralha para o tipo de cada posição ser imprevisível
    secrets.SystemRandom().shuffle(caracteres)

    return PREFIXO_PASSWORD + "".join(caracteres)


def guardar_passwords_provisorias(linhas):
    """Guarda (NIF, nome, email, password) num CSV para o admin poder
    entregar as passwords aos clientes. Devolve o caminho do ficheiro."""

    if not linhas:
        return None

    pasta = "passwords_provisorias"

    os.makedirs(pasta, exist_ok=True)

    caminho = os.path.join(
        pasta,
        f"passwords_{datetime.now():%Y%m%d_%H%M%S}.csv"
    )

    # utf-8-sig + ";" para abrir bem no Excel português
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:

        escritor = csv.writer(f, delimiter=";")

        escritor.writerow([
            "NIF (username)",
            "Nome",
            "Email",
            "Password provisória"
        ])

        escritor.writerows(linhas)

    return caminho


# ============================================================
# AUXILIARES
# ============================================================

def _texto(valor):
    """Converte uma célula do Excel em texto limpo (ou None se estiver vazia).
    Números inteiros vindos como 123.0 passam a '123'."""

    if pd.isna(valor):
        return None

    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)

    valor = str(valor).strip()

    return valor or None


def _inteiro(valor):
    texto = _texto(valor)

    if texto is None:
        return None

    try:
        return int(texto)
    except ValueError:
        return None


def _e_admin(valor):
    if pd.isna(valor):
        return False

    return str(valor).strip().lower() in ("true", "1", "sim", "s", "yes", "verdadeiro")


# ============================================================
# VERIFICAÇÕES
# ============================================================

def username_existe(username):
    response = (
        supabase
        .table("utilizador")
        .select("username")
        .eq("username", username)
        .execute()
    )

    return bool(response.data)


def numero_cliente_existe(numero_cliente):
    response = (
        supabase
        .table("cliente")
        .select("numero_cliente")
        .eq("numero_cliente", numero_cliente)
        .execute()
    )

    return bool(response.data)


# ============================================================
# IMPORTAÇÃO
# ============================================================

def importar_utilizadores(ficheiro):
    extensoes_aceites = (".xlsx", ".xls")

    if ficheiro.filename.lower().endswith(extensoes_aceites):

        df = pd.read_excel(
            ficheiro,
            sheet_name=0,
            usecols=range(10)
        )

    else:

        df = pd.read_csv(
            ficheiro,
            sep=","
        )

    # (NIF, nome, email, password) de cada cliente criado
    passwords_criadas = []

    for _, row in df.iterrows():

        nome = _texto(row["Nome / Empresa"])
        nif = _texto(row["NIF"])

        if not nome or not nif:
            continue

        print(f"\nProcessando utilizador: {nome}")

        if _e_admin(row["Admin?"]):
            print(
                f"{nome} é admin. Ignorado "
                f"(criar em Configurações)."
            )
            continue

        if username_existe(nif):
            print(
                f"Utilizador {nome} (NIF {nif}) "
                f"já existe. Ignorado."
            )
            continue

        id_utilizador = None

        try:

            morada = _texto(row["Morada"])
            indicativo = _texto(row["Indicativo"])
            telefone = _inteiro(row["Telefone"])
            postal = _texto(row["Código Postal"])
            local = _texto(row["Localização"])

            if not all([
                morada,
                indicativo,
                telefone,
                postal,
                local
            ]):
                print(
                    f"Dados obrigatórios em falta "
                    f"para {nome}. Ignorado."
                )
                continue

            if not indicativo.startswith("+"):
                indicativo = f"+{indicativo}"

            numero_cliente = _inteiro(
                row["Número Cliente"]
            )

            if (
                numero_cliente is not None
                and numero_cliente_existe(numero_cliente)
            ):
                print(
                    f"Número de cliente "
                    f"{numero_cliente} já existe. "
                    f"{nome} ignorado."
                )
                continue

            email = _texto(row["E-mail"])

            if email:
                email = email.lower()
            else:
                email = (
                    f"sem-email-{nif}"
                    f"@dataeme.invalid"
                )

            # Password provisória (fica guardada só como hash na base
            # de dados; o texto simples vai para o CSV no fim)
            password_provisoria = gerar_password_provisoria()

            password_hash = ph.hash(password_provisoria)

            resposta_utilizador = (
                supabase
                .table("utilizador")
                .insert({
                    "username": nif,
                    "password": password_hash,
                    "is_admin": False
                })
                .execute()
            )

            id_utilizador = (
                resposta_utilizador
                .data[0]["id_utilizador"]
            )

            cliente = {
                "nif": nif,
                "nome": nome,
                "morada": morada,
                "email": email,
                "telefone": telefone,
                "codigo_postal": postal,
                "localizacao": local,
                "indicativo": indicativo,
                "id_utilizador": id_utilizador
            }

            if numero_cliente is not None:
                cliente["numero_cliente"] = numero_cliente

            (
                supabase
                .table("cliente")
                .insert(cliente)
                .execute()
            )

            passwords_criadas.append(
                (nif, nome, email, password_provisoria)
            )

            print(
                f"Utilizador {nome} "
                f"inserido com sucesso."
            )

        except Exception as erro:

            print(
                f"ERRO no utilizador "
                f"{nome}: {erro}"
            )

            if id_utilizador is not None:

                try:

                    (
                        supabase
                        .table("utilizador")
                        .delete()
                        .eq(
                            "id_utilizador",
                            id_utilizador
                        )
                        .execute()
                    )

                except Exception as erro_rollback:

                    print(
                        "Não foi possível desfazer "
                        f"o utilizador: {erro_rollback}"
                    )

    # --------------------------------------------------------
    # GUARDAR AS PASSWORDS PROVISÓRIAS NUM CSV
    # --------------------------------------------------------

    caminho = guardar_passwords_provisorias(passwords_criadas)

    if caminho:
        print(
            f"\n{len(passwords_criadas)} passwords provisórias "
            f"guardadas em: {caminho}"
        )

    return caminho
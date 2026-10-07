import os
import secrets
import string
from datetime import datetime

import pandas as pd

from config import supabase, ph


PASTA_RELATORIOS = os.path.join("static", "data")


def _texto(valor):
    if pd.isna(valor):
        return ""

    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))

    return str(valor).strip()


def gerar_password_provisoria(tamanho=12):
    caracteres = string.ascii_letters + string.digits
    return "".join(secrets.choice(caracteres) for _ in range(tamanho))


def _ler_ficheiro(ficheiro):
    nome = getattr(ficheiro, "filename", "") or ""
    extensao = os.path.splitext(nome.lower())[1]

    if extensao in (".xlsx", ".xls"):
        return pd.read_excel(ficheiro, sheet_name=0)

    if extensao == ".csv":
        try:
            return pd.read_csv(ficheiro)
        except UnicodeDecodeError:
            ficheiro.seek(0)
            return pd.read_csv(ficheiro, encoding="latin-1")

    raise ValueError("Formato não suportado. Envia um ficheiro .xlsx, .xls ou .csv.")


def _normalizar_email(email):
    email = _texto(email).lower()

    if not email:
        return ""

    return email


def _guardar_utilizadores_sem_email(utilizadores_sem_email):
    if not utilizadores_sem_email:
        return None

    os.makedirs(PASTA_RELATORIOS, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_ficheiro = f"utilizadores_sem_email_{timestamp}.xlsx"
    caminho = os.path.join(PASTA_RELATORIOS, nome_ficheiro)

    colunas = [
        "Nome / Empresa",
        "NIF",
        "Morada",
        "Indicativo",
        "Telefone",
        "Código Postal",
        "Localização",
        "E-mail",
        "Motivo"
    ]

    df = pd.DataFrame(utilizadores_sem_email, columns=colunas)
    df.to_excel(caminho, index=False)

    return nome_ficheiro


def importar_utilizadores(ficheiro):
    df = _ler_ficheiro(ficheiro)

    campos_obrigatorios = [
        "Nome / Empresa",
        "NIF",
        "Morada",
        "Indicativo",
        "Telefone",
        "Código Postal",
        "Localização"
    ]

    campos_em_falta = [
        campo for campo in campos_obrigatorios
        if campo not in df.columns
    ]

    if campos_em_falta:
        raise ValueError(
            "Faltam colunas obrigatórias no ficheiro: "
            + ", ".join(campos_em_falta)
        )

    if "E-mail" not in df.columns:
        df["E-mail"] = ""

    passwords_criadas = []
    utilizadores_sem_email = []
    utilizadores_importados = 0
    utilizadores_ignorados = 0

    for _, row in df.iterrows():
        nome = _texto(row["Nome / Empresa"])
        nif = _texto(row["NIF"])
        morada = _texto(row["Morada"])
        indicativo = _texto(row["Indicativo"])
        telefone = _texto(row["Telefone"])
        codigo_postal = _texto(row["Código Postal"])
        localizacao = _texto(row["Localização"])
        email = _normalizar_email(row["E-mail"])

        if not email:
            utilizadores_sem_email.append({
                "Nome / Empresa": nome,
                "NIF": nif,
                "Morada": morada,
                "Indicativo": indicativo,
                "Telefone": telefone,
                "Código Postal": codigo_postal,
                "Localização": localizacao,
                "E-mail": "",
                "Motivo": "Sem email"
            })
            utilizadores_ignorados += 1
            continue

        password_provisoria = gerar_password_provisoria()
        password_hash = ph.hash(password_provisoria)

        resposta_utilizador = (
            supabase
            .table("utilizador")
            .insert({
                "username": nif,
                "password": password_hash,
                "is_admin": False,
                "deve_alterar_password": True
            })
            .execute()
        )

        if not resposta_utilizador.data:
            raise ValueError(
                f"Não foi possível criar o utilizador com NIF {nif}."
            )

        utilizador_criado = resposta_utilizador.data[0]
        id_utilizador = utilizador_criado["id_utilizador"]

        try:
            resposta_cliente = (
                supabase
                .table("cliente")
                .insert({
                    "id_utilizador": id_utilizador,
                    "nif": nif,
                    "nome": nome,
                    "morada": morada,
                    "email": email,
                    "telefone": telefone,
                    "indicativo": indicativo,
                    "codigo_postal": codigo_postal,
                    "localizacao": localizacao
                })
                .execute()
            )

            if not resposta_cliente.data:
                raise ValueError(
                    f"Não foi possível criar o cliente com NIF {nif}."
                )

        except Exception:
            supabase.table("utilizador").delete().eq(
                "id_utilizador", id_utilizador
            ).execute()
            raise

        passwords_criadas.append({
            "NIF": nif,
            "Nome / Empresa": nome,
            "E-mail": email,
            "Password provisória": password_provisoria
        })

        utilizadores_importados += 1

    nome_ficheiro_sem_email = _guardar_utilizadores_sem_email(
        utilizadores_sem_email
    )

    if passwords_criadas:
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho_passwords = os.path.join(
            PASTA_RELATORIOS,
            f"passwords_criadas_{timestamp}.csv"
        )

        pd.DataFrame(passwords_criadas).to_csv(
            caminho_passwords,
            index=False,
            encoding="utf-8-sig"
        )

    return {
        "importados": utilizadores_importados,
        "sem_email": utilizadores_ignorados,
        "ficheiro_sem_email": nome_ficheiro_sem_email
    }

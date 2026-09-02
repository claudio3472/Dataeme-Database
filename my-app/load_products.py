import pandas as pd
from config import supabase


# ============================================================
# SUBFAMÍLIA
# ============================================================

def obter_id_subfamilia(nome):

    response = (
        supabase
        .table("subfamilia")
        .select("id_subfamilia")
        .eq("nome", nome.strip())
        .execute()
    )

    if response.data:
        return response.data[0]["id_subfamilia"]

    return None


# ============================================================
# COR
# ============================================================

def obter_id_cor(nome_cor):

    response = (
        supabase
        .table("cores_produto")
        .select("id_cor")
        .eq("nome_cor", nome_cor.strip())
        .execute()
    )

    if response.data:
        return response.data[0]["id_cor"]

    return None


def criar_cor(nome_cor, codigo_cor):

    response = (
        supabase
        .table("cores_produto")
        .insert({
            "nome_cor": nome_cor.strip(),
            "codigo_cor": codigo_cor,
            "imagem_url": None
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Erro ao criar a cor: {nome_cor}"
        )

    return response.data[0]["id_cor"]


def obter_ou_criar_cor(nome_cor, codigo_cor):

    id_cor = obter_id_cor(nome_cor)

    if id_cor is not None:
        return id_cor

    return criar_cor(
        nome_cor,
        codigo_cor
    )


# ============================================================
# MODELO DO PRODUTO
# ============================================================

def obter_id_modelo(nome):

    response = (
        supabase
        .table("produtos_modelo")
        .select("id_modelo")
        .eq("nome_catalogo", nome.strip())
        .execute()
    )

    if response.data:
        return response.data[0]["id_modelo"]

    return None


def criar_modelo(
    nome,
    descricao_catalogo,
    descricao_detalhada,
    id_subfamilia
):

    response = (
        supabase
        .table("produtos_modelo")
        .insert({
            "nome_catalogo": nome.strip(),
            "descricao_catalogo": descricao_catalogo,
            "descricao_detalhada": descricao_detalhada,
            "id_subfamilia": id_subfamilia
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Erro ao criar modelo: {nome}"
        )

    return response.data[0]["id_modelo"]


def obter_ou_criar_modelo(
    nome,
    descricao_catalogo,
    descricao_detalhada,
    id_subfamilia
):

    id_modelo = obter_id_modelo(nome)

    if id_modelo is not None:
        return id_modelo

    return criar_modelo(
        nome,
        descricao_catalogo,
        descricao_detalhada,
        id_subfamilia
    )


# ============================================================
# IVA
# ============================================================

def obter_id_iva(percentagem):

    percentagem = float(percentagem)

    response = (
        supabase
        .table("iva")
        .select("id_iva")
        .eq("percentagem", percentagem)
        .execute()
    )

    if response.data:
        return response.data[0]["id_iva"]

    return None


def criar_iva(percentagem):

    percentagem = float(percentagem)

    response = (
        supabase
        .table("iva")
        .insert({
            "percentagem": percentagem,
            "descricao": f"IVA {percentagem:g}%"
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            f"Erro ao criar IVA: {percentagem}%"
        )

    return response.data[0]["id_iva"]


def obter_ou_criar_iva(percentagem):

    id_iva = obter_id_iva(percentagem)

    if id_iva is not None:
        return id_iva

    return criar_iva(percentagem)


# ============================================================
# PRODUTO
# ============================================================

def produto_existe(referencia):

    response = (
        supabase
        .table("produtos")
        .select("referencia")
        .eq("referencia", int(referencia))
        .execute()
    )

    return bool(response.data)


# ============================================================
# IMPORTAÇÃO
# ============================================================

def importar_produtos():

    df = pd.read_csv(
        "data/produtos.csv",
        sep=","
    )

    for _, row in df.iterrows():

        referencia = int(
            row["referencia"]
        )

        print(
            f"\nProcessando produto: {referencia}"
        )

        try:

            # ------------------------------------------------
            # SUBFAMÍLIA
            # ------------------------------------------------

            id_subfamilia = obter_id_subfamilia(
                row["subfamilia"]
            )

            if id_subfamilia is None:

                print(
                    f"ERRO: Subfamília "
                    f"'{row['subfamilia']}' não existe."
                )

                continue

            # ------------------------------------------------
            # COR
            # ------------------------------------------------

            id_cor = obter_ou_criar_cor(
                row["cor"],
                row["codigo_cor"]
            )

            print(
                f"Cor: {row['cor']} "
                f"-> ID {id_cor}"
            )

            # ------------------------------------------------
            # MODELO
            # ------------------------------------------------

            id_modelo = obter_ou_criar_modelo(
                row["nome"],
                row["descrição no catalogo"],
                row["descricao"],
                id_subfamilia
            )

            print(
                f"Modelo: {row['nome']} "
                f"-> ID {id_modelo}"
            )

            # ------------------------------------------------
            # IVA
            # ------------------------------------------------

            percentagem_iva = float(
                row["iva"]
            )

            id_iva = obter_ou_criar_iva(
                percentagem_iva
            )

            print(
                f"IVA: {percentagem_iva}% "
                f"-> ID {id_iva}"
            )

            # ------------------------------------------------
            # PREÇO
            # ------------------------------------------------

            preco_com_iva = float(
                row["preco com iva"]
            )

            preco_base = round(
                preco_com_iva /
                (1 + percentagem_iva / 100),
                2
            )

            print(
                f"Preço CSV: "
                f"{preco_com_iva:.2f}€"
            )

            print(
                f"Preço sem IVA: "
                f"{preco_base:.2f}€"
            )

            # ------------------------------------------------
            # VERIFICAR PRODUTO
            # ------------------------------------------------

            if produto_existe(referencia):

                print(
                    f"Produto {referencia} "
                    f"já existe. Ignorado."
                )

                continue

            # ------------------------------------------------
            # INSERIR PRODUTO
            # ------------------------------------------------

            supabase \
                .table("produtos") \
                .insert({
                    "referencia": referencia,
                    "id_modelo": id_modelo,
                    "id_cor": id_cor,
                    "preco_base": preco_base,
                    "id_iva": id_iva,
                    "quantidade_stock": int(
                        row["Stock"]
                    ),
                    "codigo_barras_produto": str(
                        row["código de barras"]
                    ).strip(),
                    "descontinuado": bool(
                        row["descontinuado"]
                    )
                }) \
                .execute()

            print(
                f"Produto {referencia} "
                f"inserido com sucesso."
            )

        except Exception as erro:

            print(
                f"ERRO no produto "
                f"{referencia}: {erro}"
            )

importar_produtos()